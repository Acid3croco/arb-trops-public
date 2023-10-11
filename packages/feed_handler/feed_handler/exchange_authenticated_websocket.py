import math
import threading
import uuid
import os.path
import pathlib

from abc import abstractmethod
from datetime import datetime, timezone

from cryptofeed.defines import *
from cryptofeed.feed import Feed
from cryptofeed.symbols import Symbol
from cryptofeed.feedhandler import FeedHandler
from cryptofeed.defines import ORDER_INFO, FILLS, BALANCES, POSITIONS

from arb_defines.defines import *
from arb_defines.status import StatusEnum
from feed_handler.exchange_base import ExchangeBase
from feed_handler.feed_handler import PRIVATE_CHANNELS
from redis_manager.redis_wrappers import InstrumentRedis
from redis_manager.redis_events import BalanceEvent, PositionEvent, TradeExecEvent
from arb_defines.arb_dataclasses import Balance, Instrument, Order, Position, Trade


class ExchangeAuthenticatedWebsocket(ExchangeBase):
    has_orders = True

    def __init__(self,
                 feed: Feed,
                 instruments: list[Instrument],
                 channels: list[str],
                 subaccount=None):
        # force to listen to all priave channels
        self.channels = PRIVATE_CHANNELS
        super().__init__(feed, instruments, channels)
        self.subaccount = subaccount
        self.callbacks = self._get_callbacks()

    def disconnect(self):
        self.logger.info(f'Closing funding websocket {self.exchange}')
        # for exchange in self.redis_manager.exchanges.values():
        self.exchange.set_status(private=StatusEnum.UNAVAILABLE)
        for instrument in self.redis_manager.instruments.values():
            instrument.set_status(private=StatusEnum.UNAVAILABLE)
        self.logger.info(f'Closed funding websocket {self.exchange}')

    def _subscribe(self):
        self.redis_manager.subscribe_event(BalanceEvent(self.exchange))
        self.redis_manager.subscribe_event(PositionEvent(self.instruments))

    def _run_redis_manager(self):
        self._subscribe()
        th = threading.Thread(target=self.redis_manager.run)
        self.redis_manager_thread = th
        self.logger.info(f'Starting redis manager thread {th}')
        th.start()

    def run(self):
        if not self.feed_codes:
            self.logger.warning(
                f"No symbol found for {self.exchange} - run aborted")
            return

        self._run_redis_manager()
        f = FeedHandler(config=self._get_handler_config())

        channels = self.callbacks.keys()
        # TODO: use _get_exchange_credentials from ExchangeBase
        dirname = os.environ.get("ARB_TROPS_CONFIG_KEYS")
        config = pathlib.Path(dirname, "config_exchanges.yaml")
        feed: Feed = self.feed(config=config.as_posix(),
                               symbols=self.feed_codes,
                               subaccount=self.subaccount,
                               channels=channels,
                               timeout=-1,
                               callbacks=self.callbacks)
        feed.ignore_invalid_instruments = True
        f.add_feed(feed)

        symbols_rep = self.feed_codes
        if isinstance(symbols_rep[0], Symbol):
            symbols_rep = [s.normalized for s in symbols_rep]

        self.logger.info(
            f'run authenticated websocket {self.exchange} - {channels} - {len(self.instruments)} instruments: {self.instruments}'
        )

        for instr in self.redis_manager.instruments.values():
            instr.set_status(private=StatusEnum.UP)
        self.exchange.set_status(private=StatusEnum.UP)

        f.run()

    async def on_balances_cb(self, balance, receipt_timestamp):
        """
        exchange: BINANCE_FUTURES currency: USDT balance: 34.32624789 reserved: None
        """
        self.logger.info(f'BALANCES - {balance}')

    async def on_fills_cb(self, trade_info, receipt_timestamp):
        self.logger.info(f'FILLS - {trade_info}')

        trade = self._extract_trade_info(trade_info, receipt_timestamp)

        balance_consumption = self._update_position_from_trade(trade)
        self._update_balance_from_trade(trade, balance_consumption)

        self.redis.publish_event(TradeExecEvent, trade)

    async def on_order_info_cb(self, order_info, receipt_timestamp):
        self.logger.info(f'ORDER_INFO - {order_info}')

        if not order_info.status:
            self.logger.error(f'NO STATUS IN ORDER_INFO')
        order = self._extract_order_info(order_info, receipt_timestamp)
        self.logger.debug(f'ORDER_INFO extract - {order}')
        self.redis_manager.orders_manager.received_order(order)

    async def on_positions_cb(self, position, receipt_timestamp):
        """
        exchange: BINANCE_FUTURES   symbol: ALGO-USDT-PERP  position: -2.7  entry_price: 1.86480    side: both  unrealised_pnl: -0.00108000     timestamp: 1637515936.05
        """
        # * BINANCE_FUTURES side is both all the time but qty not abs apparently?

        self.logger.info(f'POSITIONS - {position}')

    def _extract_order_info(self, order_info, receipt_timestamp) -> Order:
        instr = self.get_instr_from_code(order_info.symbol)

        time_ack = (datetime.fromtimestamp(receipt_timestamp, tz=timezone.utc)
                    if receipt_timestamp else None)

        order_id = self._get_order_id(order_info)
        order = Order(id=order_id,
                      instr=instr,
                      price=self._get_price(order_info),
                      qty=self._get_qty(order_info),
                      order_type=self._get_order_type(order_info),
                      order_status=self._get_order_status(order_info),
                      exchange_order_id=order_info.id,
                      total_filled=self._get_total_filled(order_info))

        # if order.order_status in [PARTIAL, FILLED]:
        #     self.on_fills_cb(order_info, receipt_timestamp)

        if order.order_status == OPEN:
            order.time_ack_mkt = time_ack
        elif order.order_status in [PARTIAL, FILLED]:
            order.time_filled_mkt = time_ack
        elif order.order_status == CANCELED:
            order.time_canceled_mkt = time_ack
        elif order.order_status == REJECTED:
            order.time_rejected_mkt = time_ack

        return order

    def _extract_trade_info(self, trade_info, receipt_timestamp) -> Trade:
        instr = self.get_instr_from_code(trade_info.symbol)

        time_ack = (datetime.fromtimestamp(receipt_timestamp, tz=timezone.utc)
                    if receipt_timestamp else None)
        qty = float(self._get_trade_qty(trade_info))
        qty = -abs(qty) if trade_info.side == SELL else qty

        #! temporary for test where orders are sent from exchange not by arb
        trade_id = self._get_order_id(trade_info) or uuid.uuid4()
        trade = Trade(
            id=trade_id,
            time=time_ack,
            instr=instr,
            price=self._get_price(trade_info),
            qty=qty,
            fee=self._get_fee(trade_info),
            order_type=self._get_trade_type(trade_info),
            exchange_order_id=self._get_exchange_order_id(trade_info))

        return trade

    def _update_position_from_trade(self, trade: Trade):
        if trade.instr.instr_type == SPOT:
            # there is no position for spot instruments
            return

        instr: InstrumentRedis = trade.instr
        instr_pos = instr.position or Position(instr_id=instr.id)
        trade_pos = Position.from_trade(trade)

        #! Fees?
        balance_consumption = Position.calc_balance_consumption(
            instr_pos, trade_pos)  # + trade.fee
        self.logger.info(f'BALANCE CONSUMPTION - {balance_consumption}')
        new_position = instr_pos + trade_pos
        instr.set_position(new_position)
        self.logger.info(
            f'POSITION - {instr.instr_code} {instr.position.qty}@{instr.position.price}'
        )
        return balance_consumption

    def _update_balance_from_trade(self, trade: Trade,
                                   balance_consumption: float):
        balance: Balance = self.exchange.get_balance(trade.instr.quote)
        if not balance:
            balance = Balance(exchange_id=self.exchange.id,
                              currency=trade.instr.quote)

        if trade.instr.instr_type == SPOT:
            base_balance: Balance = self.exchange.get_balance(trade.instr.base)
            if not base_balance:
                base_balance = Balance(exchange_id=self.exchange.id,
                                       currency=trade.instr.base)
            self.logger.info(base_balance)

            #! Fees?
            # balance_consumption = math.copysign(
            #     abs(trade.amount) + trade.fee, trade.amount)
            balance_consumption = trade.amount
            base_balance.qty += trade.qty
            self.logger.info(
                f'BALANCE - {self.exchange.feed_name} {base_balance.currency} {base_balance.qty}'
            )
            self.logger.info(base_balance)
            self.exchange.set_balance(base_balance)

        balance.qty -= balance_consumption
        self.logger.info(
            f'BALANCE - {self.exchange} {balance.currency} {balance.qty}')
        self.exchange.set_balance(balance)

        self.logger.info(trade.instr.instr_type)

    @abstractmethod
    def _get_order_id(self, order_info):
        self.logger.info(order_info.raw)
        raise NotImplementedError

    @staticmethod
    def _get_exchange_order_id(trade_info):
        return trade_info.order_id

    @staticmethod
    def _get_order_type(order_info):
        """MAKER TAKER"""
        if order_info.type is None:
            return
        order_type = order_info.type.lower()
        if order_type in [LIMIT, MAKER]:
            return MAKER
        if order_type in [MARKET, TAKER]:
            return TAKER
        return order_type

    @staticmethod
    def _get_order_status(order_info):
        """OPEN PARTIAL FILLED CANCELLED REJECTED CLOSED"""
        status = order_info.status.lower()
        if status in [NEW, SUBMITTING, SUBMIT, SUBMITED, SUBMITTED, OPEN]:
            return OPEN
        if status in [FILL]:
            return FILLED
        if status in [CANCEL, CANCELED, CANCELLED]:
            return CANCELED
        if status in [REJECT, REJECTED]:
            return REJECTED
        if status in [CLOSE, CLOSED]:
            return CLOSED
        if status in [EXPIRED, EXPIRE]:
            return EXPIRED
        return status

    @staticmethod
    def _get_trade_type(trade_info):
        """MAKER TAKER"""
        trade_type = trade_info.liquidity.lower()
        if trade_type in [LIMIT, MAKER]:
            return MAKER
        if trade_type in [MARKET, TAKER]:
            return TAKER
        return trade_type

    @staticmethod
    def _get_trade_qty(trade_info):
        return trade_info.amount or 0

    @staticmethod
    def _get_price(order_info):
        return float(order_info.price or 0)

    @staticmethod
    def _get_qty(order_info):
        qty = float(order_info.amount or 0) + float(order_info.remaining or 0)
        return -abs(qty) if order_info.side == SELL else qty

    @staticmethod
    def _get_fee(trade_info):
        fee = float(trade_info.fee or 0)
        return fee

    @staticmethod
    def _get_total_filled(order_info):
        filled = order_info.amount
        return -abs(filled) if order_info.side == SELL else filled

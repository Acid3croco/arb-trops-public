import time
import uuid

from datetime import datetime, timezone
from dataclasses import dataclass
from collections import defaultdict

from cryptofeed.defines import FTX, SPOT, PERPETUAL, MARKET, BUY

from arb_defines.defines import *
from arb_logger.logger import get_logger
from arb_defines.event_types import EventTypes
from redis_manager.redis_handler import RedisHandler
from redis_manager.redis_wrappers import ExchangeRedis, InstrumentRedis
from arb_defines.arb_dataclasses import AggrBook, AggrFundingRate, Balance, ExchangeStatus, FundingRate, InstrStatus, Instrument, Order, OrderBook, Position, StrategyInfo, Trade
from redis_manager.redis_events import BalanceEvent, ExchangeStatusEvent, FundingRateEvent, InstrStatusEvent, OrderBookEvent, OrderEvent, OrderExchangeEvent, PositionEvent, StrategyInfoDBEvent, TradeExecEvent


@dataclass
class Config:
    last_order_threshold: float = 30
    min_spread = 0.0019
    # self.config = AttrDict(config) # where config is dict


class SeekerSpreadFunding:

    def __init__(self, instruments: list[Instrument],
                 currencies: list[Instrument]):
        self.base = instruments[0].base

        self.logger = get_logger(f'{self}_{self.base}')
        self.logger.info(f'{self.base} {self} initialization')

        self.timeout = 0
        self.last_order_time = 0
        self.config = Config

        self.redis = RedisHandler(logger=self.logger)

        self.exchanges: defaultdict[int, ExchangeRedis] = {
            e.id: ExchangeRedis.from_exchange(e)
            for e in [i.exchange for i in instruments + currencies]
        }
        self.instruments: defaultdict[int, InstrumentRedis] = {
            i.id: InstrumentRedis.from_instrument(i)
            for i in instruments
        }
        self.currencies: defaultdict[int, InstrumentRedis] = {
            c.id: InstrumentRedis.from_instrument(c)
            for c in currencies
        }

        self.all_instrs: list[Instrument] = (list(self.instruments.values()) +
                                             list(self.currencies.values()))

        self.load_exchanges_from_redis()
        self.load_instruments_from_redis()
        self.load_currencies_from_redis()

        funding_rates: dict[Instrument, FundingRate] = {
            i: i.funding_rate
            for i in self.instruments.values()
        }
        self.aggrfundingrate = AggrFundingRate(funding_rates=funding_rates)

        self.aggrbook = AggrBook(currencies=self.currencies.values())

        self.excl_buys = []
        self.excl_sells = []
        self.update_excl()

    def __str__(self) -> str:
        return self.__class__.__name__

    def load_exchanges_from_redis(self):
        for exchange in self.exchanges.values():
            while exchange.exchange_status != EXCHANGE_STATUS_UP:
                exchange: ExchangeRedis = self.redis.get_exchange(exchange)
                self.exchanges[exchange.id] = exchange

                if exchange.exchange_status == EXCHANGE_STATUS_UNAVAILABLE:
                    self.logger.error(
                        f'{exchange.feed_name} is unavailable, disabling')
                    break

                self.logger.info(f'Waiting for exchange {exchange} to be up')
                time.sleep(1)
            self.logger.info(f'Exchange {exchange} is up')
        self.logger.info(f'Exchanges loaded from redis')

    def load_instruments_from_redis(self):
        for instr in self.instruments.values():
            while instr.instr_status != INSTRUMENT_STATUS_UP:
                instr_redis: InstrumentRedis = self.redis.get_instrument(instr)
                self.instruments[instr.id] = instr_redis

                if self.exchanges[instr.exchange.
                                  id].exchange_status != EXCHANGE_STATUS_UP:
                    self.logger.error(
                        f'{instr.exchange.feed_name} is unavailable, disabling'
                    )
                    instr_redis.instr_status = INSTRUMENT_STATUS_UNAVAILABLE
                    break

                time.sleep(1)

        if len(self.instruments) < 2:
            self.logger.error(
                f'{self.base} {len(self.instruments)} instruments - not enought for me - leaving here'
            )
            exit(0)

        self.logger.info(
            f'{len(self.instruments)} instruments loaded from redis')

    def load_currencies_from_redis(self):
        for instr in self.currencies.values():
            while instr.instr_status != INSTRUMENT_STATUS_UP:
                instr_redis: InstrumentRedis = self.redis.get_instrument(instr)
                self.currencies[instr.id] = instr_redis

                if self.exchanges[instr.exchange.
                                  id].exchange_status != EXCHANGE_STATUS_UP:
                    self.logger.error(
                        f'{instr.exchange.feed_name} is unavailable, disabling'
                    )
                    instr_redis.instr_status = INSTRUMENT_STATUS_UNAVAILABLE
                    break

                time.sleep(1)

        self.logger.info(
            f'{len(self.currencies)} currencies loaded from redis')

    def run(self):
        self.redis.subscribe_event(
            ExchangeStatusEvent(self.exchanges.values()),
            self.on_exchange_status_event)

        self.redis.subscribe_event(BalanceEvent(self.all_instrs),
                                   self.on_balance_event)
        self.redis.subscribe_event(PositionEvent(self.all_instrs),
                                   self.on_position_event)
        self.redis.subscribe_event(OrderBookEvent(self.all_instrs),
                                   self.on_order_book_event)
        self.redis.subscribe_event(TradeExecEvent(self.all_instrs),
                                   self.on_trade_exec_event)
        self.redis.subscribe_event(FundingRateEvent(self.all_instrs),
                                   self.on_funding_rate_event)
        self.redis.subscribe_event(InstrStatusEvent(self.all_instrs),
                                   self.on_instr_status_event)

        self.logger.info(f'{self.base} {self} started')

        self.redis.run()

    def on_exchange_status_event(self, es: ExchangeStatus):
        self.exchanges[es.id].exchange_status = es.exchange_status

    def on_balance_event(self, balance: Balance):
        ex: ExchangeRedis = self.exchanges.get(balance.exchange_id)
        if not ex:
            self.logger.error(f'No exchange found for balance: {balance}')
        ex.balances[balance.currency] = balance
        self.logger.info(f"on_balance_event {ex}")

    def on_position_event(self, position: Position):
        instr: InstrumentRedis = self.instruments.get(position.instr_id)
        if not instr:
            self.logger.error(f'No instrument found for position: {position}')

        instr.position = position

        self.update_excl()

    def on_order_book_event(self, orderbook: OrderBook):
        instr = (self.instruments.get(orderbook.instr_id)
                 or self.currencies.get(orderbook.instr_id))

        if not instr:
            self.logger.error(
                f'No instrument found for orderbook, instr_id: {orderbook.instr_id}'
            )
            return

        if instr.instr_status != INSTRUMENT_STATUS_UP:
            self.logger.warning(f'Instrument {instr} is not up, skipping')
            return

        instr.orderbook = orderbook
        self.aggrbook.update_aggrbook_taker(instr, orderbook)

        if self.pre_routine_checks(instr):
            self.strat_routine(instr)

    def on_funding_rate_event(self, funding_rate: FundingRate):
        instr = (self.instruments.get(funding_rate.instr_id)
                 or self.currencies.get(funding_rate.instr_id))

        if not instr:
            self.logger.error(
                f'No instrument found for funding_rate, instr_id: {funding_rate.instr_id}'
            )

        instr.funding_rate = funding_rate
        self.aggrfundingrate.upadte_funding_rate(instr, funding_rate)

        if self.pre_routine_checks(instr):
            self.strat_routine(instr)

    def on_trade_exec_event(self, trade: Trade):
        """
        When receiving BTC EXEC, FIRE BTCSRN + SRNPERP
        """
        instr: InstrumentRedis = (self.instruments.get(trade.instr_id)
                                  or self.currencies.get(trade.instr_id))
        self.logger.info(
            f'TRADE received in {self.__class__.__name__}: {trade}')

        if instr.id in self.currencies:
            order_instr = self.excl_sells[0]
            if trade.side == BUY:
                price, _ = order_instr.orderbook.ask()
            else:
                price, _ = order_instr.orderbook.bid()
            qty = 2200
            order = Order(instr=order_instr,
                          price=price,
                          qty=qty,
                          order_type=MARKET,
                          event_type=EventTypes.HIT_HIT_FUNDING)
            self.fire_orders([order])

    def on_instr_status_event(self, i_s: InstrStatus):
        instr: InstrumentRedis = (self.instruments.get(i_s.instr_id)
                                  or self.currencies.get(i_s.instr_id))
        instr.instr_status = i_s.instr_status

    def entry_spread(self):
        spread = self.aggrbook.hit_hit_spread(excl_buys=self.excl_buys,
                                              excl_sells=self.excl_sells)
        return spread

    def exit_spread(self):
        spread = self.aggrbook.hit_hit_spread(excl_buys=self.excl_sells,
                                              excl_sells=self.excl_buys)
        return spread

    def _compute_spread(self, spread, excl_buy, excl_sell, secret_word=''):
        buy, buy_size, buy_instr = self.aggrbook.taker_buy(
            excl_instrs=excl_buy)
        sell, sell_size, sell_instr = self.aggrbook.taker_sell(
            excl_instrs=excl_sell)

        fr_spread, _, _ = self.aggrfundingrate.spread(incl_buys=[buy_instr],
                                                      incl_sells=[sell_instr])

        buy = buy * self.aggrbook.get_currency_rate(buy_instr)
        sell = sell * self.aggrbook.get_currency_rate(sell_instr)
        if buy_instr != sell_instr:
            self.logger.info(
                f"  \t{secret_word} SPREAD {spread * 100:.3f}% ({fr_spread * 100:.5f}%) - {buy_instr} - {buy_size:.5f} - {buy:.5f} - {sell:.5f} - {sell_size:.5f} - {sell_instr}",
            )
            return buy_instr, sell_instr
        return None, None

    def pre_routine_checks(self, instr):
        # check orderbook.timestamp, balances(risk), delay btw,
        # wake up seeker_spread routine
        if time.time() < self.timeout:
            self.logger.debug(
                f'Timeout until: {datetime.fromtimestamp(self.timeout)}')
            return False

        if time.time() < (self.last_order_time +
                          self.config.last_order_threshold):
            self.logger.debug(
                f'New order sent too soon - last_order_time: {datetime.fromtimestamp(self.last_order_time)}'
            )
            return False

        return True

    def strat_routine(self, instr):
        entry_spread = self.entry_spread()
        exit_spread = self.exit_spread()

        orders = None
        if exit_spread and exit_spread > 0.015:
            buy_instr, sell_instr = self._compute_spread(
                exit_spread, self.excl_sells, self.excl_buys, 'EXIT')
            fr_spread, _, _ = self.aggrfundingrate.spread(
                incl_buys=[buy_instr], incl_sells=[sell_instr])

            if fr_spread < 0:
                pass

        elif entry_spread and entry_spread > 0.005:
            buy_instr, sell_instr = self._compute_spread(
                entry_spread, self.excl_buys, self.excl_sells, 'ENTRY')
            if buy_instr and sell_instr:
                instr_curr = list(self.currencies.values())[0]
                price, _ = instr_curr.orderbook.ask()
                qty = 2200 / price
                order_curr = Order(instr=instr_curr,
                                   price=price,
                                   qty=qty,
                                   order_type=MARKET,
                                   event_type=EventTypes.HIT_HIT_FUNDING)
                price, _ = sell_instr.orderbook.bid()
                qty = 2200
                order_perp = Order(instr=sell_instr,
                                   price=price,
                                   qty=qty,
                                   order_type=MARKET,
                                   event_type=EventTypes.HIT_HIT_FUNDING)
                orders = [order_curr, order_perp]

        if orders:
            self.fire_orders(orders)

    def update_excl(self):
        self._update_excl_buys()
        self._update_excl_sells()

    def _update_excl_buys(self):
        instruments: list[InstrumentRedis] = self.instruments.values()
        self.excl_buys: list[Instrument] = [
            i for i in instruments if i.instr_type != SPOT
        ]

    def _update_excl_sells(self):
        instruments: list[InstrumentRedis] = self.instruments.values()
        self.excl_sells: list[Instrument] = [
            i for i in instruments if i.instr_type == SPOT
        ]

    def _check_order_size(self, orders: list[Order]) -> bool:
        check = True

        for order in orders:
            balance: Balance = self.exchanges.get(
                order.exchange_id).balances.get(order.instr.quote)
            order_amount = abs(order.qty * order.price)

            instr = (self.instruments.get(order.instr.id)
                     or self.currencies.get(order.instr.id))
            if instr is None:
                self.logger.critical(f'Instrument not found {instr}')
                check = False
                continue
            if instr.instr_type == SPOT:
                incr_pos = order.qty > 0
            else:
                if instr.position is None:
                    self.logger.info(f'No position for {instr}')
                pos = instr.position
                incr_pos = order.qty * pos.qty > 0

            if incr_pos and balance.qty / balance.total_qty < 0.3:
                self.logger.error(f'Order size too big {order}, {balance}')
                check = False
        return check

    def fire_orders(self, orders: list[Order], bypass_timeout=False):
        if not self._check_order_size(orders):
            return

        event_key = uuid.uuid4()
        for order in orders:
            order.event_key = event_key
            self.logger.info(order)
            if order.instr_id in self.currencies:
                #! TEMPORARY
                trade = Trade(id=order.id,
                              time=datetime.now(tz=timezone.utc),
                              exchange_order_id=uuid.uuid4(),
                              instr=order.instr,
                              qty=order.qty,
                              price=order.price,
                              fee=0,
                              order_type=MARKET)
                self.redis.publish_event(TradeExecEvent, trade)
            # self.redis.publish_event(OrderExchangeEvent, order)

        if not bypass_timeout:
            self.last_order_time = time.time()

        for order in orders:
            self._snap_strategy_info(order)

    def _snap_strategy_info(self, order):
        orderbook = self.redis.get_orderbook(order.instr.id)
        strategy_info = StrategyInfo(order_id=order.id,
                                     event_key=order.event_key,
                                     payload=orderbook)
        self.redis.publish_event(StrategyInfoDBEvent, strategy_info)

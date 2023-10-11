import time
import uuid

from datetime import datetime, timezone
from dataclasses import dataclass
from collections import defaultdict

from cryptofeed.defines import SPOT, MARKET, BUY, SELL

from arb_defines.defines import *
from arb_logger.logger import get_logger
from arb_defines.event_types import EventTypes
from process_manager.process_manager import ProcessManager
from redis_manager.redis_manager import RedisManager
from redis_manager.redis_wrappers import ExchangeRedis, InstrumentRedis
from arb_defines.arb_dataclasses import AggrBook, Balance, ExchangeStatus, FundingRate, InstrStatus, Instrument, Order, OrderBook, Position, StrategyInfo, Trade
from redis_manager.redis_events import BalanceEvent, ExchangeStatusEvent, FundingRateEvent, InstrStatusEvent, OrderBookEvent, OrderEvent, OrderExchangeEvent, PositionEvent, StrategyInfoDBEvent, TradeExecEvent


@dataclass
class Config:
    last_order_threshold = 30

    spot_order_qty = 1600
    _min_spread = 0.01
    min_spread_entry = 0.05
    min_spread_exit = 0.01
    # self.config = AttrDict(config) # where config is dict


#! NEED TO CONTROL POSITIONS AND BALANCES TO NOT REVERSE THE PERP WHILE NOT BEING ABLE TO SHORT SPOT
class TriangularArbSpotPerpFundingSeeker:

    def __init__(self, instr_spot: Instrument, instr_perp: Instrument,
                 currency: Instrument):
        self.base = instr_perp.base
        self.config = Config

        self.logger = get_logger(f'{self}_{self.base}')
        self.logger.info(f'{self.base} {self} initialization')
        self.redis_last_load = 0

        self.state = SEEKER_STATUS_RUNNING
        self.last_order_time = time.time()

        self.redis = RedisManager(logger=self.logger)

        self.instr_spot_id = instr_spot.id
        self.instr_perp_id = instr_perp.id
        self.currency_id = currency.id

        # self.instruments = {
        #     i.id: InstrumentRedis.from_instrument(i)
        #     for i in [instr_spot, instr_perp, currency]
        # }

        # self.exchanges: defaultdict[int, ExchangeRedis] = {
        #     e.id: ExchangeRedis.from_exchange(e)
        #     for e in [i.exchange for i in self.instruments.values()]
        # }

        # self.load_exchanges_from_redis()
        # self.load_instruments_from_redis()

        self.aggrbook = AggrBook({self.currency.base: self.currency})

        # get recent orderbooks
        self.aggrbook.set_orderbooks([
            i for i in self.instruments.values()
            if i.orderbook and i.orderbook.timestamp > time.time() - 15
        ])

    def __str__(self) -> str:
        return self.__class__.__name__

    @property
    def instr_perp(self):
        return self.redis.instruments.get(self.instr_perp_id)

    @property
    def instr_spot(self):
        return self.redis.instruments.get(self.instr_spot_id)

    @property
    def currency(self):
        return self.redis.instruments.get(self.currency_id)

    # region new loader redis
    # def load_exchanges_from_redis(self):
    #     for exchange in self.exchanges.values():
    #         while exchange.exchange_status != EXCHANGE_STATUS_UP:
    #             exchange: ExchangeRedis = self.redis.get_exchange(exchange)
    #             self.exchanges[exchange.id] = exchange

    #             if exchange.exchange_status == EXCHANGE_STATUS_UNAVAILABLE:
    #                 self.logger.error(
    #                     f'{exchange.feed_name} is unavailable, disabling')
    #                 break

    #             self.logger.info(f'Waiting for exchange {exchange} to be up')
    #             time.sleep(1)
    #         self.logger.info(f'Exchange {exchange} is up')
    #     self.logger.info(f'Exchanges loaded from redis')

    # def load_instruments_from_redis(self):
    #     for instr in self.instruments.values():
    #         while instr.instr_status != INSTRUMENT_STATUS_UP:
    #             instr_redis: InstrumentRedis = self.redis.get_instrument(instr)
    #             self.instruments[instr.id] = instr_redis

    #             if self.exchanges[instr.exchange.
    #                               id].exchange_status != EXCHANGE_STATUS_UP:
    #                 self.logger.error(
    #                     f'{instr.exchange.feed_name} is unavailable, disabling'
    #                 )
    #                 instr_redis.instr_status = INSTRUMENT_STATUS_UNAVAILABLE
    #                 break

    #             time.sleep(1)

    #     if len(self.instruments) < 3:
    #         self.logger.error(
    #             f'{self.base} {len(self.instruments)} instruments - not enought for me, i need a spot a perp and a currency - leaving here'
    #         )
    #         exit(0)

    #     self.logger.info(
    #         f'{len(self.instruments)} instruments loaded from redis')

    # def load_exchanges_from_redis(self):
    #     if time.time() < self.redis_last_load + 5:
    #         return
    #     self.logger.info(f'Loading exchanges from redis')

    #     for exchange in self.exchanges.values():
    #         exchange: ExchangeRedis = self.redis.get_exchange(exchange)
    #         self.exchanges[exchange.id] = exchange

    #         self.logger.info(
    #             f'Exchange {exchange} is {exchange.exchange_status}')
    #         if exchange.exchange_status == EXCHANGE_STATUS_UNAVAILABLE:
    #             continue

    #     self.logger.info(f'Exchanges loaded from redis')
    #     self.redis_last_load = time.time()

    # def load_instruments_from_redis(self):
    #     if time.time() < self.redis_last_load + 5:
    #         return
    #     self.logger.info(f'Loading instruments from redis')

    #     for instr in self.instruments.values():
    #         instr_redis: InstrumentRedis = self.redis.get_instrument(instr)
    #         self.instruments[instr.id] = instr_redis

    #         self.logger.info(
    #             f'Instrument {instr_redis} is {instr_redis.instr_status}')
    #         if self.exchanges[
    #                 instr.exchange.id].exchange_status != EXCHANGE_STATUS_UP:
    #             instr_redis.instr_status = INSTRUMENT_STATUS_UNAVAILABLE
    #             continue

    #     self.logger.info(f'{self.instruments.values()} loaded from redis')
    #     self.redis_last_load = time.time()

    #endregion

    def run(self):
        self.redis.subscribe_event(
            ExchangeStatusEvent(self.exchanges.values()),
            self.on_exchange_status_event)
        self.redis.subscribe_event(BalanceEvent(self.exchanges.values()),
                                   self.on_balance_event)

        instruments = self.instruments.values()
        self.redis.subscribe_event(PositionEvent(instruments),
                                   self.on_position_event)
        self.redis.subscribe_event(OrderBookEvent(instruments),
                                   self.on_order_book_event)
        self.redis.subscribe_event(TradeExecEvent(instruments),
                                   self.on_trade_exec_event)
        self.redis.subscribe_event(FundingRateEvent(instruments),
                                   self.on_funding_rate_event)
        self.redis.subscribe_event(InstrStatusEvent(instruments),
                                   self.on_instr_status_event)

        self.logger.info(f'{self.base} {self} started')

        self.last_order_time = time.time()
        self.redis.run()

    def on_exchange_status_event(self, es: ExchangeStatus):
        self.exchanges[es.id].exchange_status = es.exchange_status
        self.logger.info(
            f'Exchange {es.exchange} status changed to {es.exchange_status}')

    def on_instr_status_event(self, i_s: InstrStatus):
        instr: InstrumentRedis = self.instruments.get(i_s.instr_id)
        instr.instr_status = i_s.instr_status
        self.logger.info(
            f'Instrument {instr} status changed to {i_s.instr_status}')

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

    def on_order_book_event(self, orderbook: OrderBook):
        instr = self.instruments.get(orderbook.instr_id)

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
        instr = self.instruments.get(funding_rate.instr_id)

        if not instr:
            self.logger.error(
                f'No instrument found for funding_rate, instr_id: {funding_rate.instr_id}'
            )

        instr.funding_rate = funding_rate

        if self.pre_routine_checks(instr):
            self.strat_routine(instr)

    def on_trade_exec_event(self, trade: Trade):
        """
        When receiving BTC EXEC, FIRE BTCSRN
        """
        instr: InstrumentRedis = self.instruments.get(trade.instr_id)
        trade.instr = instr

        self.logger.info(
            f'TRADE received in {self.__class__.__name__}: {trade}')

        o_instr = None
        price = 0
        qty = 0
        curr_crurr_qty = self.exchanges[self.currency.exchange.id].balances[
            self.currency.base].qty
        if instr == self.currency and trade.side == BUY:
            o_instr = self.instr_spot
            price, _ = o_instr.orderbook.ask()
            qty = self.config.spot_order_qty
            # qty = min(
            #     qty, curr_crurr_qty
            #     if curr_crurr_qty and curr_crurr_qty != 0 else qty)

        elif instr == self.instr_spot and trade.side == SELL:
            o_instr = self.currency
            price, _ = self.instr_spot.orderbook.bid()
            qty = trade.qty * price
            # qty = max(
            #     qty, curr_crurr_qty
            #     if curr_crurr_qty and curr_crurr_qty != 0 else qty)

        if o_instr:
            order = Order(instr=o_instr,
                          price=price,
                          qty=qty,
                          order_type=MARKET,
                          event_type=EventTypes.TRI_ARB_SPOT_PERP_FUNDING)
            self.fire_orders([order])
            self.last_order_time = time.time()

    def entry_spread(self):
        spread = self.aggrbook.hit_hit_spread(excl_buys=[self.instr_perp],
                                              excl_sells=[self.instr_spot])
        return spread

    def exit_spread(self):
        spread = self.aggrbook.hit_hit_spread(excl_buys=[self.instr_spot],
                                              excl_sells=[self.instr_perp])
        return spread

    def _show_spread(self, spread, buy_instr, sell_instr, secret_word=''):
        rate = self.instr_perp.funding_rate.predicted_rate

        buy, buy_size = buy_instr.orderbook.ask()
        sell, sell_size = sell_instr.orderbook.bid()
        buy = buy * self.aggrbook.get_currency_rate(buy_instr)
        sell = sell * self.aggrbook.get_currency_rate(sell_instr)
        if buy_instr != sell_instr:
            self.logger.info(
                f"  \t{secret_word} SPREAD {spread * 100:.3f}% ({rate * 100:.5f}%) - {buy_instr} - {buy_size:.5f} - {buy:.5f} - {sell:.5f} - {sell_size:.5f} - {sell_instr}",
            )
            return buy_instr, sell_instr
        return None, None

    def _exchanges_status_check(self):
        check = True

        for ex in self.exchanges.values():
            if ex.exchange_status != EXCHANGE_STATUS_UP:
                self.logger.debug(
                    f'{self} exchange {ex} not up, state: {ex.exchange_status}'
                )
                check = False

        if not check:
            self.load_exchanges_from_redis()

        return check

    def _instruments_status_check(self):
        check = True

        for instr in self.instruments.values():
            if instr.instr_status != INSTRUMENT_STATUS_UP:
                self.logger.debug(
                    f'{self} instrument {instr} not up, state: {instr.instr_status}'
                )
                check = False

        if not check:
            self.load_instruments_from_redis()

        return check

    def pre_routine_checks(self, instr):
        if self.state != SEEKER_STATUS_RUNNING:
            self.logger.debug(f'{self} not running, state: {self.state}')
            return False

        if not self._exchanges_status_check():
            return False
        if not self._instruments_status_check():
            return False

        timeout = self.last_order_time + self.config.last_order_threshold
        if time.time() < timeout:
            self.logger.debug(
                f'Timeout until: {datetime.fromtimestamp(timeout)}')
            return False

        return True

    def entry_spread_orders(self):
        qty = self.config.spot_order_qty

        price_perp = self.instr_perp.orderbook.bid()[0]
        qty_perp = qty * -1

        price_curr = self.currency.orderbook.ask()[0]
        price_spot = self.instr_spot.orderbook.ask()[0]
        # take into account fees when going in for the btc because we will need them to take srn
        qty_curr = (qty * price_spot *
                    (1 + self.currency.taker_fee.percent_value * 1.5))

        order_perp = Order(instr=self.instr_perp,
                           qty=qty_perp,
                           price=price_perp,
                           order_type=MARKET,
                           event_type=EventTypes.TRI_ARB_SPOT_PERP_FUNDING)
        order_curr = Order(instr=self.currency,
                           qty=qty_curr,
                           price=price_curr,
                           order_type=MARKET,
                           event_type=EventTypes.TRI_ARB_SPOT_PERP_FUNDING)

        return [order_perp, order_curr]

    def exit_spread_orders(self):
        qty = self.config.spot_order_qty

        price_perp = self.instr_perp.orderbook.ask()[0]
        qty_perp = qty

        price_spot = self.instr_spot.orderbook.bid()[0]
        qty_spot = qty * -1

        order_perp = Order(instr=self.instr_perp,
                           qty=qty_perp,
                           price=price_perp,
                           order_type=MARKET,
                           event_type=EventTypes.TRI_ARB_SPOT_PERP_FUNDING)
        order_spot = Order(instr=self.instr_spot,
                           qty=qty_spot,
                           price=price_spot,
                           order_type=MARKET,
                           event_type=EventTypes.TRI_ARB_SPOT_PERP_FUNDING)

        return [order_perp, order_spot]

    def strat_routine(self, instr):
        entry_spread = self.entry_spread()
        exit_spread = self.exit_spread()
        fr_spread = self.instr_perp.funding_rate.predicted_rate
        orders = None

        if fr_spread < 0 and exit_spread and exit_spread > self.config.min_spread_exit:
            exch = self.exchanges.get(self.instr_spot.exchange.id)
            bal: Balance = exch.get_balance(self.instr_spot.base)
            # 1 SRN being very small its fine + we cant have 0 SRN because of min size/min qty/rounding errors etc
            # care with too small (e.g sub 1000 SRN when converted to BTC these BTC cant be converted to USD )
            if bal.qty >= self.config.spot_order_qty:
                self._show_spread(exit_spread, self.instr_perp,
                                  self.instr_spot, 'EXIT')
                orders = self.exit_spread_orders()

        elif fr_spread > 0 and entry_spread and entry_spread > self.config.min_spread_entry:
            self._show_spread(entry_spread, self.instr_spot, self.instr_perp,
                              'ENTRY')
            orders = self.entry_spread_orders()

        if orders:
            self.last_order_time = time.time()
            self.fire_orders(orders)

    def _check_order_size(self, orders: list[Order]) -> bool:
        check = True

        for order in orders:
            balance: Balance = self.exchanges.get(
                order.exchange_id).balances.get(order.instr.quote)

            instr = self.instruments.get(order.instr.id)
            if instr is None:
                self.logger.error(f'Instrument not found {instr}')
                check = False
                continue
            if instr.instr_type == SPOT:
                incr_pos = order.qty > 0
            else:
                if instr.position is None:
                    self.logger.error(f'No position for {instr}')
                    check = False
                    continue
                pos = instr.position
                incr_pos = order.qty * pos.qty > 0

            if incr_pos and balance.qty / balance.total_qty < 0.2:
                self.logger.error(f'Order size too big {order}, {balance}')
                check = False
        return check

    def fire_orders(self, orders: list[Order]):
        if not self._check_order_size(orders):
            self.logger.error(
                f'{orders} did not pass check_order_size, not sending')
            return

        event_key = uuid.uuid4()
        for order in orders:
            order.event_key = event_key
            self.logger.info(order)

            # #! TEMPORARY
            # trade = Trade(id=order.id,
            #               time=datetime.now(tz=timezone.utc),
            #               exchange_order_id=uuid.uuid4(),
            #               instr=order.instr,
            #               qty=order.qty,
            #               price=order.price,
            #               fee=0,
            #               order_type=MARKET)

            # self.redis.publish_event(TradeExecEvent, trade)
            # self.redis.publish_event(OrderExchangeEvent, order)

        for order in orders:
            self._snap_strategy_info(order)

    def _snap_strategy_info(self, order):
        orderbook = self.redis.get_orderbook(order.instr.id)
        strategy_info = StrategyInfo(order_id=order.id,
                                     event_key=order.event_key,
                                     payload=orderbook)
        self.redis.publish_event(StrategyInfoDBEvent, strategy_info)


def triangular_arb_spot_perp_funding_run(instr_spot, instr_perp, currency):
    seeker = TriangularArbSpotPerpFundingSeeker(instr_spot, instr_perp,
                                                currency)
    seeker.run()


def triangular_arb_spot_perp_funding_run_all(process_manager: ProcessManager,
                                             instr_spot, instr_perp,
                                             currency) -> ProcessManager:
    process_manager.spawn_process([
        triangular_arb_spot_perp_funding_run,
        (instr_spot, instr_perp, currency)
    ])

    return process_manager

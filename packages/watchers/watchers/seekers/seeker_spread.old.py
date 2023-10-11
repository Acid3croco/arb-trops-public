import math
import time
import uuid
import asyncio

from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict

from unsync.unsync import unsync
from cryptofeed.defines import LIMIT, MARKET

from arb_defines.defines import *
from arb_logger.logger import get_logger
from arb_defines.event_types import EventTypes
from redis_manager.redis_handler import RedisHandler
from redis_manager.redis_wrappers import ExchangeRedis, InstrumentRedis
from arb_defines.arb_dataclasses import AggrBook, Balance, ExchangeStatus, InstrStatus, Instrument, Order, OrderBook, Position, StrategyInfo
from redis_manager.redis_events import BalanceEvent, ExchangeStatusEvent, InstrStatusEvent, OrderBookEvent, OrderExchangeEvent, PositionEvent, StrategyInfoDBEvent


@dataclass
class Config:
    last_order_threshold: float = 30
    min_spread = 0.0019
    # self.config = AttrDict(config) # where config is dict


class SeekerSpread:

    def __init__(self, instruments: list[Instrument]):
        self.timeout = 0
        self.last_order_time = 0
        self.base = instruments[0].base
        self.logger = get_logger(f'{self}_{self.base}')
        self.config = Config

        self.logger.info(f'{self.base} {self} initialization')

        self.exchanges: defaultdict[int, ExchangeRedis] = {
            e.id: ExchangeRedis.from_exchange(e)
            for e in [i.exchange for i in instruments]
        }
        self.instruments: defaultdict[int, InstrumentRedis] = {
            i.id: InstrumentRedis.from_instrument(i)
            for i in instruments
        }

        self.aggrbook = AggrBook()
        self.redis = RedisHandler(logger=self.logger)

        self.load_exchanges_from_redis()
        self.load_instruments_from_redis()

    def __str__(self) -> str:
        return self.__class__.__name__

    def load_exchanges_from_redis(self):
        """
        blocking loop on status before starting
        load exchanges balances, and positions and yadaya from database/redis?
        """
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
        """
        blocking loop on status before starting
        load insturments status, balances and positions and yadaya from database/redis?
        """
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
            exit(1)

        self.logger.info(
            f'{len(self.instruments)} instruments loaded from redis')

    def run(self):
        self.redis.subscribe_event(
            ExchangeStatusEvent(self.exchanges.values()),
            self.on_exchange_status_event)
        self.redis.subscribe_event(BalanceEvent(self.exchanges.values()),
                                   self.on_balance_event)

        self.redis.subscribe_event(InstrStatusEvent(self.instruments.values()),
                                   self.on_instr_status_event)
        self.redis.subscribe_event(PositionEvent(self.instruments.values()),
                                   self.on_position_event)
        self.redis.subscribe_event(OrderBookEvent(self.instruments.values()),
                                   self.on_order_book_event)

        self.logger.info(f'{self.base} {self.__class__.__name__} started')

        self.redis.run()

    def on_exchange_status_event(self, es: ExchangeStatus):
        self.exchanges[es.id].exchange_status = es.exchange_status

    def on_instr_status_event(self, i_s: InstrStatus):
        self.instruments[i_s.instr_id].instr_status = i_s.instr_status

    def on_order_book_event(self, orderbook: OrderBook):
        instr: InstrumentRedis = self.instruments.get(orderbook.instr_id)
        if not instr:
            self.logger.error(
                f'No instrument found for orderbook, instr_id: {orderbook.instr_id}'
            )

        if instr.instr_status != INSTRUMENT_STATUS_UP:
            self.logger.warning(f'Instrument {instr} is not up, skipping')
            return

        instr.orderbook = orderbook
        self.aggrbook.update_aggrbook_taker(instr, orderbook)

        if self.pre_routine_checks(instr):
            self.strat_routine(instr)

    def on_position_event(self, position: Position):
        instr: InstrumentRedis = self.instruments.get(position.instr_id)
        if not instr:
            self.logger.error(f'No instrument found for position: {position}')

        instr.position = position

    def on_balance_event(self, balance: Balance):
        ex: ExchangeRedis = self.exchanges.get(balance.exchange_id)
        if not ex:
            self.logger.error(f'No exchange found for balance: {balance}')
        ex.balances[balance.currency] = balance
        self.logger.info(f"on_balance_event {ex}")

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
        spread = self.aggrbook.hit_hit_spread()

        if spread and spread > self.config.min_spread:
            buy, buy_size, buy_instr = self.aggrbook.taker_buy()
            sell, sell_size, sell_instr = self.aggrbook.taker_sell()
            if buy_instr == sell_instr:
                self.timeout = time.time() + 5
                self.logger.warning(
                    f'Buy and sell instruments are the same: {buy_instr}, not going further, timeout 5s'
                )
                return

            self.logger.info(
                f"  \tSPREAD {spread * 100:.3f}% - {buy_instr} - {buy:.5f} - {sell:.5f} - {sell_instr}",
            )

            order1 = Order(instr=buy_instr,
                           price=buy,
                           qty=1,
                           order_type=MARKET,
                           event_type=EventTypes.HIT_HIT)
            order2 = Order(instr=sell_instr,
                           price=sell,
                           qty=-1,
                           order_type=MARKET,
                           event_type=EventTypes.HIT_HIT)

            self._fix_order_size(order1, order2)
            if self._check_book_depth(order1, buy_size, order2, sell_size):
                self.fire_orders([order1, order2])

    def _check_book_depth(self, order1: Order, buy_size, order2: Order,
                          sell_size):
        check = True

        if abs(order1.qty) * 5 > buy_size:
            self.logger.debug(
                f'orderbook is too thin: {order1.desc()} for {buy_size}')
            check = False
        if abs(order2.qty) * 5 > sell_size:
            self.logger.debug(
                f'orderbook is too thin: {order2.desc()} for {sell_size}')
            check = False
        return check

    def _check_order_size(self, orders: list[Order]) -> bool:
        check = True

        for order in orders:
            balance: Balance = self.exchanges.get(
                order.exchange_id).balances.get(order.instr.quote)
            order_amount = abs(order.qty * order.price)

            instr: InstrumentRedis = self.instruments.get(order.instr.id)
            if instr is None or instr.position is None:
                self.logger.critical(
                    f'Position not found for instr {order.instr}, instr_redis {instr}'
                )
                check = False
                continue
            pos = instr.position
            incr_pos = order.qty * pos.qty > 0

            # if incr_pos and order_amount > balance.qty * 0.09:
            if incr_pos and balance.qty < 35:
                self.logger.error(f'Order size too big {order}, {balance}')
                check = False
        return check

    def fire_orders(self, orders: list[Order]):
        if not self._check_order_size(orders):
            return

        event_key = uuid.uuid4()
        for order in orders:
            order.event_key = event_key
            self.redis.publish_event(OrderExchangeEvent, order)

        self.last_order_time = time.time()

        for order in orders:
            self._snap_strategy_info(order)

    def _fix_order_size(self, order1: Order, order2: Order):
        order1.qty = math.copysign(10 / order1.price, order1.qty)
        order2.qty = math.copysign(10 / order2.price, order2.qty)

        round_size = min(abs(order1.r_qty), abs(order2.r_qty))
        order1.qty = math.copysign(round_size, order1.qty)
        order2.qty = math.copysign(round_size, order2.qty)

    def _snap_strategy_info(self, order):
        orderbook = self.redis.get_orderbook(order.instr.id)
        strategy_info = StrategyInfo(order_id=order.id,
                                     event_key=order.event_key,
                                     payload=orderbook)
        self.redis.publish_event(StrategyInfoDBEvent, strategy_info)

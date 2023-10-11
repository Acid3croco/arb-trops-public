import time

from logging import Logger
from typing import Callable
from threading import Thread
from dataclasses import dataclass
from collections import defaultdict

from arb_logger.logger import get_logger
from redis_manager.redis_handler import RedisHandler
from redis_manager.orders_manager import OrdersManager
from redis_manager.redis_wrappers import ExchangeRedis, InstrumentRedis
from arb_defines.arb_dataclasses import Balance, Exchange, ExchangeApiPayload, ExchangeStatus, FundingRate, InstrStatus, Instrument, Order, OrderBook, Position, Trade
from redis_manager.redis_events import BalanceEvent, ExchangeApiEvent, ExchangeDrivenEvent, ExchangeStatusEvent, FundingRateEvent, InstrStatusEvent, InstrumentDrivenEvent, LiquidationEvent, OrderBookEvent, OrderEvent, OrderExchangeEvent, PositionEvent, RedisEvent, TradeEvent


@dataclass
class RedisManager:

    def __init__(self,
                 instruments: list[Instrument] = None,
                 exchanges: list[Exchange] = None,
                 has_orders=False,
                 has_status=False,
                 no_wrapper=False,
                 host='localhost',
                 port=6379,
                 logger=None):
        """Provide exchanges only if you dont provide instruments."""
        self.logger: Logger = logger or get_logger(self.__class__.__name__)

        if instruments and exchanges:
            raise ValueError(
                'You cant provide instruments or exchanges, not both.')

        self._exchanges_list = exchanges
        self._instruments_list = instruments
        self.redis_handler = RedisHandler(host, port, logger)
        self.publish_event = self.redis_handler.publish_event

        self.has_orders = has_orders
        if has_orders:
            self.orders_manager = OrdersManager(
                redis_handler=self.redis_handler,
                instruments=instruments,
                logger=self.logger)

        self.exchanges: dict[int, ExchangeRedis] = defaultdict(ExchangeRedis)
        self.instruments: dict[int,
                               InstrumentRedis] = defaultdict(InstrumentRedis)
        self._load_objects_redis()

        if has_status:
            self.subscribe_event(InstrStatusEvent(self.instruments))
            self.subscribe_event(ExchangeStatusEvent(self.exchanges))

        self.no_wrapper = no_wrapper
        self.hearthbeat_threads = []

    @property
    def redis_instance(self):
        return self.redis_handler.redis_instance

    def _load_objects_redis(self):
        if self._instruments_list:
            for instr in self._instruments_list:
                exchange = ExchangeRedis.from_exchange(instr.exchange,
                                                       self.redis_handler)
                self.exchanges[instr.exchange.id] = exchange
                instrument = InstrumentRedis.from_instrument(
                    instr, self.redis_handler)
                self.instruments[instr.id] = instrument

        if self._exchanges_list:
            for exchange in self._exchanges_list:
                exchange = ExchangeRedis.from_exchange(exchange,
                                                       self.redis_handler)
                self.exchanges[exchange.id] = exchange

    def run_heartbeat_events(self):
        for th in self.hearthbeat_threads:
            self.logger.info(f'Start heartbeat thread {th}')
            th.start()

    def run(self):
        for exchange in self.exchanges.values():
            exchange.refresh_all()
        for instrument in self.instruments.values():
            instrument.refresh_all()
        self.run_heartbeat_events()
        self.redis_handler.run()

    def add_instrument(self, instr: Instrument):
        """Add instrument to redis manager"""
        self.logger.info(f'Adding instrument {instr} to redis manager')
        if instr.exchange not in self.exchanges:
            self.logger.info(
                f'Adding exchange {instr.exchange} to redis manager')
            exchange = ExchangeRedis.from_exchange(instrument.exchange,
                                                   self.redis_handler)
            self.exchanges[instrument.exchange.id] = exchange
            for event in [
                    e for e in self.redis_handler.events.values()
                    if isinstance(e.event, ExchangeDrivenEvent)
            ]:
                self.subscribe_event(event.event, event.callbacks,
                                     event.deserialize)
        instrument = InstrumentRedis.from_instrument(instr, self.redis_handler)
        self.instruments[instrument.id] = instrument
        for event in [
                e for e in self.redis_handler.events.values()
                if isinstance(e.event, InstrumentDrivenEvent)
        ]:
            self.subscribe_event(event.event, event.callbacks,
                                 event.deserialize)
        if self.has_orders:
            self.orders_manager.add_instrument_manager(instrument)

    def subscribe_event(self,
                        redis_event: RedisEvent,
                        callbacks=None,
                        deserialize=True):
        if not callbacks:
            callbacks = []
        callbacks = self._wrap_callbacks(redis_event, callbacks)
        self.redis_handler.subscribe_event(redis_event, callbacks, deserialize)

    def psubscribe_event(self,
                         redis_event: RedisEvent,
                         callbacks=None,
                         deserialize=True):
        if not callbacks:
            callbacks = []
        if not self.no_wrapper:
            callbacks = self._wrap_callbacks(redis_event, callbacks)
        self.redis_handler.psubscribe_event(redis_event, callbacks,
                                            deserialize)

    def _wrap_heartbeat_callback(self, period, callback: Callable, is_pile=False, offset=0):
        start_time = (0 if is_pile else time.time()) + offset
        last_time = None
        while True:
            if not last_time and is_pile is True:
                last_time = time.time()
            else:
                last_time = time.time()
                self.logger.debug(f'Calling heartbeat callback {callback}, last time {last_time}')
                callback()
            duration = time.time() - last_time
            # monkey patch double heartbeat when duration too short
            # and callback is called 20 to 0 ms before realy pile time
            time.sleep(max(0.5 - duration, 0))

            if duration > period:
                self.logger.warning(
                    f'Heartbeat callback {callback} took {duration:.2f} seconds, which is longer than period {period}'
                )
            else:
                delta = period - ((time.time() - start_time) % period)
                self.logger.debug(f'Heartbeat callback {callback} took {duration:.2f} seconds, sleeping for {delta:.2f} seconds')
                time.sleep(delta)

    def heartbeat_event(self, period: float, callbacks: Callable | list[Callable], is_pile=False, offset=0):
        """
        It takes a period and a list of callbacks, and then creates a thread for
        each callback that calls the callback every period

        Args:
          period (float): the time between each callback in seconds
          callbacks (Callable | list[Callable]): a list of functions to be called
        at the specified period
          is_pile: ("a lheure pile") if True, the callback will be called at start of period, otherwise it
        will be called every period starting the moment the thread is started
        """
        if not isinstance(callbacks, list):
            callbacks = [callbacks]
        for callback in callbacks:
            th = Thread(target=self._wrap_heartbeat_callback,
                        args=(period, callback, is_pile, offset),
                        daemon=True)
            self.hearthbeat_threads.append(th)

    def _wrap_callbacks(self, redis_event: RedisEvent, callbacks):
        if not isinstance(callbacks, list):
            callbacks = [callbacks]

        match redis_event.__class__.__qualname__:
            case OrderBookEvent.__qualname__:
                return [self._on_orderbook_event_callback] + callbacks
            case OrderEvent.__qualname__ :
                self.subscribe_event(ExchangeApiEvent(redis_event.objects), self._on_exchange_api_event_callback)
                return [self._on_order_event_callback] + callbacks
            case OrderExchangeEvent.__qualname__:
                return [self._on_order_event_callback] + callbacks
            case TradeEvent.__qualname__ | LiquidationEvent.__qualname__:
                return [self._on_trade_event_callback] + callbacks
            case PositionEvent.__qualname__:
                return [self._on_position_event_callback] + callbacks
            case BalanceEvent.__qualname__:
                return [self._on_balance_event_callback] + callbacks
            case ExchangeStatusEvent.__qualname__:
                return [self._on_exchange_status_event_callback] + callbacks
            case InstrStatusEvent.__qualname__:
                return [self._on_instr_status_event_callback] + callbacks
            case FundingRateEvent.__qualname__:
                return [self._on_funding_rate_event_callback] + callbacks
            # case ReduceIdEvent.__qualname__:
            #     return [self._on_reduce_id_event_callback] + callbacks
            case _:
                return callbacks

    def get_instrument(
            self,
            instr_id: int | Instrument | Order | Trade) -> InstrumentRedis:
        """Get instrument from redis."""
        if isinstance(instr_id, Instrument):
            instr_id = instr_id.id
        elif isinstance(instr_id, Order | Trade):
            instr_id = instr_id.instr_id or instr_id.instr.id
        return self.instruments.get(instr_id)

    def get_exchange(
        self, exchange_id: int | Exchange | Instrument | Order | Trade
    ) -> ExchangeRedis:
        """Get exchange from redis."""
        if isinstance(exchange_id, Exchange):
            exchange_id = exchange_id.id
        elif isinstance(exchange_id, Instrument):
            exchange_id = exchange_id.exchange.id
        elif isinstance(exchange_id, Order | Trade):
            exchange_id = exchange_id.exchange_id
        return self.exchanges.get(exchange_id)

    def _on_reduce_id_event_callback(self, payload: dict):
        if 'instr_id' in payload:
            payload = self.get_instrument(payload['instr_id'])
        if 'exchange_id' in payload:
            payload = self.get_exchange(payload['instr_id'])

    def _on_trade_event_callback(self, trade: Trade):
        # instrument = self.instruments.get(trade.instr_id)
        trade.instr = self.get_instrument(trade)
        trade.instr.last_trade = trade

    def _on_orderbook_event_callback(self, orderbook: OrderBook):
        instrument = self.instruments.get(orderbook.instr_id)
        instrument.orderbook = orderbook

    def _on_funding_rate_event_callback(self, funding_rate: FundingRate):
        instrument = self.instruments.get(funding_rate.instr_id)
        instrument.funding_rate = funding_rate

    def _on_instr_status_event_callback(self, status: InstrStatus):
        instrument = self.instruments.get(status.instr_id)
        if not instrument.status:
            instrument.status = status
        else:
            instrument.status += status

    def _on_position_event_callback(self, position: Position):
        instrument = self.instruments.get(position.instr_id)
        instrument.position = position

    def _on_exchange_status_event_callback(self, status: ExchangeStatus):
        exchange = self.get_exchange(status.exchange_id)
        if not exchange.status:
            exchange.status = status
        else:
            exchange.status += status

    def _on_balance_event_callback(self, balance: Balance):
        exchange = self.get_exchange(balance.exchange_id)
        exchange.balances[balance.currency] = balance

    def _on_order_event_callback(self, order: Order):
        if self.has_orders:
            order.instr = self.get_instrument(order)
            self.orders_manager.handler_order(order)

    def _on_exchange_api_event_callback(self, payload: ExchangeApiPayload):
        if payload.action == 'reload_all_orders':
            self.orders_manager.reload_all_orders(
                exchange_id=payload.exchange_id)

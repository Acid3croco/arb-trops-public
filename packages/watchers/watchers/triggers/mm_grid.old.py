import time
import atexit

from threading import Thread
from datetime import datetime
from dataclasses import dataclass

import numpy as np
import pandas as pd

from cryptofeed.defines import LIMIT, BUY, SELL
from ta.volatility import AverageTrueRange

from arb_defines.event_types import EventTypes
from arb_utils.resolver import resolve_instruments
from redis_manager.redis_wrappers import InstrumentRedis
from arb_utils.args_parser import instruments_args_parser
from watchers.trigger_base import TriggerBase, TriggerClient
from arb_defines.defines import LONG, SHORT, START, STOP, CANCEL, PING, PONG
from redis_manager.redis_events import OrderBookEvent, TradeEvent, TradeExecEvent, TriggerEvent
from arb_defines.arb_dataclasses import Candle, Instrument, Order, OrderBook, TriggerPayload, Trade


@dataclass
class MMGridConfig:
    instr: Instrument = None
    order_qty: float = 1
    order_interval: int = 10
    nb_orders: int = 10
    q_mult: float = 1
    p_mult: float = 8
    _p_shift: float = 0.0
    volat_len: int = 14
    use_atr: bool = False
    atr_mult: float = 1
    atr_val: float = None
    buy_price_skew: float = 0.0
    sell_price_skew: float = 0.0

    def __post_init__(self):
        if self.instr and not isinstance(self.instr, Instrument):
            self.instr = Instrument(**self.instr)


class MMGrid(TriggerBase):
    config_class = MMGridConfig
    client_class = 'MMGridClient'
    short_logger = True

    def __init__(self, instruments) -> None:
        if len(instruments) != 1:
            raise ValueError('MMGrid needs exactly 1 instruments')

        super().__init__(instruments)
        self.instr = instruments[0]

        self.config: MMGridConfig = None
        self.running = False

        self.atr: float = None
        self.ltps: list[float] = []
        self.ohlc: list[list[float]] = []
        self.last_order_time = 0

    @property
    def instrument(self) -> InstrumentRedis:
        return self.redis_manager.get_instrument(self.instr)

    @property
    def atr_len(self):
        return self.config.volat_len if self.config and self.config.volat_len else 10

    @property
    def buy_orders(self):
        return sorted([
            o for o in self.redis_manager.orders_manager.orders.values()
            if o.side == BUY
        ],
                      key=lambda o: o.price,
                      reverse=True)

    @property
    def sell_orders(self):
        return sorted([
            o for o in self.redis_manager.orders_manager.orders.values()
            if o.side == SELL
        ],
                      key=lambda o: o.price)

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.heartbeat_event(60, self.update_state, is_pile=True)
        self.redis_manager.subscribe_event(TradeEvent(self.instruments),
                                           self.on_trade_event)
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments))
        self.redis_manager.subscribe_event(TradeExecEvent(self.instruments),
                                           self.on_trade_exec_event)

    def on_trigger_event(self, payload: TriggerPayload):
        super().on_trigger_event(payload)

        match payload.action:
            case 'ping':
                self._send_pong()
            case 'start':
                self.running = True
                if self.last_order_time == 0:
                    self.update_state()
            case 'stop':
                self.running = False
                self.cancel_all_pendings()
            case 'update':
                self.update_state()

    def _send_pong(self):
        self.send_trigger_client(
            TriggerPayload(trigger_id=self.client_id,
                           action=PONG,
                           config=self.config))

    def on_trade_event(self, trade: Trade):
        self.ltps.append((trade.time, trade.price, trade.qty))

    # def on_orderbook_event(self, orderbook: OrderBook):
    # ob_time = datetime.fromtimestamp(orderbook.timestamp)
    # self.ltps.append((ob_time, orderbook.mid(), 0))

    def on_trade_exec_event(self, trade: Trade):
        self.update_state()

    @staticmethod
    def calc_atr(ohlc, length):
        df = pd.DataFrame(
            ohlc, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        atr = AverageTrueRange(df['high'],
                               df['low'],
                               df['close'],
                               window=length).average_true_range()
        return atr.iloc[-1]

    def _compute_volat(self):
        if not self.config:
            return

        if self.config.atr_val and self.config.atr_val > 0:
            self.atr = self.config.atr_val
            return

        if not self.config.use_atr:
            self.atr = self.instrument.tick_size * self.config.atr_mult
            return

        candle = Candle.from_ltps(self.ltps)
        if candle:
            self.ohlc.append(candle.to_list())
            self.ltps = []
            self.ohlc = self.ohlc[-self.atr_len * 10:]

        if len(self.ohlc) >= self.atr_len:
            self.atr = self.calc_atr(self.ohlc, self.atr_len)
        else:
            self.atr = None

    def _get_order_qty(self, mult, side):
        qty = self.config.order_qty
        step = self.config.q_mult

        # if self.instrument.position and (
        #     (self.instrument.position.side == LONG and side == SELL) or
        #     ((self.instrument.position.side == SHORT and side == BUY))):
        #     return max(self.instrument.position.qty / 2,
        #                self.instrument.min_order_size)

        return qty * step

    def _get_order_price(self, mult, side):

        if side == BUY:
            price, _ = self.instrument.orderbook.bid(0)
            price = min(price, self.instrument.position.price if self.instrument.position.price != 0 else price)
            step = self.atr * (
                (self.config.p_mult + self.config.buy_price_skew) * mult)
            self.logger.debug(f'{side} price: {price} step: {step}')
            if mult == 0 and self.instrument.position.qty != 0:
                step = self.atr * ((self.config.p_mult + self.config.buy_price_skew) * 1)
            return (price - step) * (1 - self.config._p_shift), step
        else:
            price, _ = self.instrument.orderbook.ask(0)
            price = max(price, self.instrument.position.price if self.instrument.position.price != 0 else price)
            step = self.atr * (
                (self.config.p_mult + self.config.sell_price_skew) * mult)
            self.logger.debug(f'{side} price: {price} step: {step}')
            if mult == 0 and self.instrument.position.qty != 0:
                step = self.atr * ((self.config.p_mult + self.config.sell_price_skew) * 1)
            return (price + step) * (1 + self.config._p_shift), step

    def create_orders(self):
        orders = []

        bid, _ = self.instrument.orderbook.bid()
        ask, _ = self.instrument.orderbook.ask()
        nearest_buy = self.buy_orders[0].price if self.buy_orders else None
        furthest_buy = self.buy_orders[-1].price if self.buy_orders else None
        nearest_sell = self.sell_orders[0].price if self.sell_orders else None
        furthest_sell = self.sell_orders[-1].price if self.sell_orders else None
        self.logger.debug(
            f'nearest buy: {nearest_buy} furthest buy: {furthest_buy}')
        self.logger.debug(
            f'nearest sell: {nearest_sell} furthest sell: {furthest_sell}')
        for a in range(self.config.nb_orders):
            qty = self._get_order_qty(a, BUY)
            price, step = self._get_order_price(a, BUY)
            pos_check = not self.instrument.position or self.instrument.position.price == 0 or price < self.instrument.position.price
            if self.instrument.position and self.instrument.position.price != 0 and self.instrument.position.qty > 0:
                price_check = not nearest_buy or price <= furthest_buy + step
            else:
                price_check = not nearest_buy or (price >= nearest_buy + step
                                              or price <= furthest_buy - step)
            self.logger.debug(
                f'{a} pos check: {pos_check}, buy price check: {price_check}')
            if not pos_check:
                self.logger.warning(
                    f'{a} buy pos check failed: {self.instrument.position} {self.instrument.position.price if self.instrument.position else None}'
                )
            if not price_check:
                self.logger.warning(
                    f'{a} buy price check failed: {price}: nearest buy: {nearest_buy + step} furthest buy: {furthest_buy - step}'
                )
            if pos_check and price_check and price <= bid:
                order_buy = Order(instr=self.instrument,
                                  price=price,
                                  qty=qty,
                                  order_type=LIMIT,
                                  event_type=EventTypes.MM_GRID)
                orders.append(order_buy)

            qty = self._get_order_qty(a, SELL)
            price, step = self._get_order_price(a, SELL)
            pos_check = not self.instrument.position or self.instrument.position.price == 0 or price > self.instrument.position.price
            if self.instrument.position and self.instrument.position.price != 0 and self.instrument.position.qty < 0:
                price_check = not nearest_sell or price >= furthest_sell + step
            else:
                price_check = not nearest_sell or (price <= nearest_sell - step or
                                               price >= furthest_sell + step)
            self.logger.debug(
                f'{a} pos check: {pos_check}, sell price check: {price_check}')
            if not pos_check:
                self.logger.warning(
                    f'{a} sell pos check failed: {self.instrument.position} {self.instrument.position.price if self.instrument.position else None}'
                )
            if not price_check:
                self.logger.warning(
                    f'{a} sell price check failed: {price}: nearest sell: {nearest_sell - step} furthest sell: {furthest_sell + step}'
                )
            if pos_check and price_check and price >= ask:
                order_sell = Order(instr=self.instrument,
                                   price=price,
                                   qty=-qty,
                                   order_type=LIMIT,
                                   event_type=EventTypes.MM_GRID)
                orders.append(order_sell)

        return orders

    def compute_orders(self):
        orders = self.create_orders()
        for order in orders:
            self.logger.info('Sending order: {}'.format(order))
        self.logger.info(f'Sending {len(orders)} orders')
        if orders:
            self.last_order_time = time.time()
            self.send_orders(orders, checked=True)

    def update_state(self):
        self._compute_volat()

        self.logger.info(f'ATR: {self.atr}')
        if not self.atr:
            self.logger.warning(
                'ATR is not computed, skipping order management until it is')
            return

        if self.running:
            if self.last_order_time + self.config.order_interval > time.time():
                # Checking if the last order was sent more than
                # `self.config.order_interval` seconds ago. If it was, it will send
                # new orders.
                self.logger.warning(
                    f'Last order sent at {self.last_order_time}, next order at {self.last_order_time + self.config.order_interval}'
                )
                return
            self.compute_orders()


class MMGridClient(TriggerClient):
    linked_class = MMGrid
    config = MMGridConfig()

    def __init__(self, instruments):
        if len(instruments) != 1:
            raise ValueError('MMGrid needs exactly 1 instruments')

        self.is_ready = False
        super().__init__(instruments)
        self.config.instr = instruments[0]

    @property
    def prompt(self):
        return '(ready) ' if self.is_ready else '(not ready) '

    def on_trigger_event(self, payload: TriggerPayload):
        self.logger.debug(f'Received trigger event: {payload}')
        if payload.action == PONG:
            self.is_ready = True
            self.config = self.config.__class__(
                **payload.config) if payload.config else self.config
        elif payload.action == 'send_orders':
            if not payload.data:
                self.logger.info('No orders')
            for order in payload.data:
                self.logger.info(order)

    def do_update(self, _):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id,
                           action='update',
                           config=self.config))

    def do_ping(self, _):
        """
        It sends a PING trigger to the server, and waits for a response
        """
        self.is_ready = False
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id,
                           action=PING,
                           config=self.config))
        for _ in range(100):
            if not self.is_ready:
                time.sleep(0.01)
                continue
            else:
                break
        else:
            self.logger.error("Can't ping server")


def main():
    parser = instruments_args_parser('MMGrid')
    parser.add_argument('--server',
                        action='store_true',
                        help='Run in server mode')
    args = parser.parse_args()

    instruments = resolve_instruments(args)

    if args.server:
        trigger = MMGrid(instruments)
    else:
        trigger = MMGridClient(instruments)

    def clean_exit():
        nonlocal trigger
        if hasattr(trigger, 'disconnect'):
            trigger.disconnect()
        del trigger

    atexit.register(clean_exit)

    trigger.run()


if __name__ == '__main__':
    main()

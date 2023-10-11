import time
import atexit

from dataclasses import dataclass
from collections import defaultdict

from cryptofeed.defines import LIMIT, BUY, SELL

from arb_utils import arb_round
from arb_defines.event_types import EventTypes
from arb_utils.resolver import resolve_instruments
from redis_manager.redis_wrappers import InstrumentRedis
from arb_utils.args_parser import instruments_args_parser
from watchers.trigger_base import TriggerBase, TriggerClient
from redis_manager.redis_events import OrderBookEvent, TradeEvent, TradeExecEvent
from arb_defines.arb_dataclasses import Instrument, Order, OrderBook, Trade


@dataclass
class MMDumbConfig:
    instr: Instrument = None
    nb_orders: int = 1
    order_qty: float = 0.1
    buy_price_skew: float = 1
    sell_price_skew: float = 1
    update_freq: int = 30
    spread: float = 0.05

    def __post_init__(self):
        if self.instr and not isinstance(self.instr, Instrument):
            self.instr = Instrument(**self.instr)


class MMDumb(TriggerBase):
    config_class = MMDumbConfig
    client_class = 'MMDumbClient'
    short_logger = True

    def __init__(self, instruments) -> None:
        if len(instruments) != 1:
            raise ValueError('MMDumb needs exactly 1 instruments')

        super().__init__(instruments)
        self.instr = instruments[0]

        self.config: MMDumbConfig = None
        self.running = False
        self.is_ready = True
        self.last_update = 0

    @property
    def instrument(self) -> InstrumentRedis:
        return self.redis_manager.get_instrument(self.instr)

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.heartbeat_event(60, self.clean_orders, is_pile=True)
        self.redis_manager.subscribe_event(TradeEvent(self.instruments),
                                           self.on_trade_event)
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments),
                                           self.on_orderbook_event)
        self.redis_manager.subscribe_event(TradeExecEvent(self.instruments),
                                           self.on_trade_exec_event)

    def on_trade_event(self, trade: Trade):
        self.logger.info('on_trade_event')
        self.update_state()

    def on_orderbook_event(self, orderbook: OrderBook):
        self.logger.info('on_orderbook_event')
        self.update_state()

    def on_trade_exec_event(self, trade: Trade):
        self.logger.info(f'on_trade_exec_event {trade}')
        self.update_state()

    def _get_price_grid(self):
        if not self.instrument.orderbook:
            self.logger.warning('orderbook not ready')
            return

        buy_grid = []
        sell_grid = []
        for i in range(self.config.nb_orders):
            bid = self.instrument.orderbook.bid()[0]
            bid = bid * (1 - self.config.spread)
            buy_lv = (bid - i * self.instrument.tick_size)
            buy_lv = arb_round(buy_lv, self.instrument.tick_size)
            buy_grid.append(round(buy_lv, 8))

            ask = self.instrument.orderbook.ask()[0]
            ask = ask * (1 + self.config.spread)
            sell_lv = (ask + i * self.instrument.tick_size)
            sell_lv = arb_round(sell_lv, self.instrument.tick_size)
            sell_grid.append(round(sell_lv, 8))

        return buy_grid, sell_grid

    def update_state(self):
        if not self.is_ready:
            return

        if not self.config:
            self.logger.warning('config not ready')
            return

        if self.last_update + self.config.update_freq > time.time():
            self.logger.warning('update too fast')
            return

        self.logger.debug('update state')
        self.build_orders()

    def _get_orders_grid(self):
        orders = self.redis_manager.orders_manager.get_orders(self.instrument)
        orders_grid = {BUY: defaultdict(list), SELL: defaultdict(list)}
        for order in orders.values():
            price = arb_round(order.price, self.instrument.tick_size)
            orders_grid[order.side][round(price, 8)].append(order)
        return orders_grid

    def build_orders(self):
        self.logger.info('build orders')

        buy_grid, sell_grid = self._get_price_grid()
        self.logger.info(f'buy_grid: {buy_grid}')
        self.logger.info(f'sell_grid: {sell_grid}')
        orders = []
        orders_grid = self._get_orders_grid()
        self.logger.info(f'buy_orders_grid: {orders_grid[BUY].keys()}')
        self.logger.info(f'_orders_grid: {orders_grid[SELL].keys()}')

        for side, grid in zip((BUY, SELL), (buy_grid, sell_grid)):
            _side = 1 if side == BUY else -1
            if ((_side == 1 and self.config.buy_price_skew == 0)
                    or (_side == -1 and self.config.sell_price_skew == 0)):
                self.logger.warning(f'skipping {side} side')
                continue
            for price in grid:
                if orders_grid[side].get(price):
                    self.logger.debug(
                        f'{side} {price} already has {len(orders_grid[side][price])} orders'
                    )
                    continue
                order = Order(instr=self.instrument,
                              price=price,
                              qty=self.config.order_qty * _side,
                              order_type=LIMIT,
                              event_type=EventTypes.MM_DUMB)
                orders.append(order)

        self.logger.info(f'orders: {len(orders)}')
        if orders:
            self.last_update = time.time()
            self.send_orders(orders, checked=True)

    def clean_orders(self):
        pass


class MMDumbClient(TriggerClient):
    linked_class = MMDumb
    config = MMDumbConfig()

    def __init__(self, instruments):
        if len(instruments) != 1:
            raise ValueError('MMDumb needs exactly 1 instruments')

        self.is_ready = False
        super().__init__(instruments)
        self.config.instr = instruments[0]

    @property
    def prompt(self):
        return '(ready) ' if self.is_ready else '(not ready) '


def main():
    parser = instruments_args_parser('MMDumb')
    parser.add_argument('--server',
                        action='store_true',
                        help='Run in server mode')
    args = parser.parse_args()

    instruments = resolve_instruments(args)

    if args.server:
        trigger = MMDumb(instruments)
    else:
        trigger = MMDumbClient(instruments)

    def clean_exit():
        nonlocal trigger
        if hasattr(trigger, 'disconnect'):
            trigger.disconnect()
        del trigger

    atexit.register(clean_exit)

    trigger.run()


if __name__ == '__main__':
    main()

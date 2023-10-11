import time
import atexit

from dataclasses import dataclass
from arb_defines.event_types import EventTypes

from cryptofeed.defines import LIMIT, MARKET

from arb_defines.defines import CANCEL, START, STOP
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser
from watchers.trigger_base import TriggerBase, TriggerClient
from redis_manager.redis_events import OrderBookEvent, OrderEvent, TradeExecEvent
from arb_defines.arb_dataclasses import AggrBook, Instrument, Order, OrderBook, Trade, TriggerPayload


@dataclass
class MMTriggerConfig:
    left_leg: Instrument = None
    right_leg: Instrument = None
    order_qty: float = 0.01
    update_treshold: float = 5000.0

    def __post_init__(self):
        if self.left_leg and not isinstance(self.left_leg, Instrument):
            self.left_leg = Instrument(**self.left_leg)
        if self.right_leg and not isinstance(self.right_leg, Instrument):
            self.right_leg = Instrument(**self.right_leg)

    @property
    def has_legs(self):
        return self.right_leg and self.left_leg and (self.right_leg !=
                                                     self.left_leg)


class MMTrigger(TriggerBase):
    config_class = MMTriggerConfig

    def __init__(self, instruments) -> None:
        if len(instruments) != 2:
            raise ValueError('MMTrigger needs exactly 2 instruments')

        super().__init__(instruments)

        self.aggrbook = AggrBook()
        self.config: MMTriggerConfig = None
        self.last_update_time = 0
        self.may_i_run: bool = False
        self.cancel_all: bool = False

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments),
                                           self.on_order_book_event)
        self.redis_manager.subscribe_event(OrderEvent(self.instruments),
                                           self.on_order_event)
        self.redis_manager.subscribe_event(TradeExecEvent(self.instruments),
                                           self.on_trade_exec_event)

    def on_trigger_event(self, payload: TriggerPayload):
        super().on_trigger_event(payload)

        match payload.action:
            case 'start':
                self.may_i_run = True
            case 'stop':
                self.may_i_run = False
                self.cancel_all = True
            case 'cancel':
                self.cancel_all_pendings()
            case 'reset':
                self.last_update_time = 0
            case 'refresh':
                self.redis_manager.orders_manager.reload_all_orders()

    def on_order_book_event(self, orderbook: OrderBook):
        instr = self.redis_manager.get_instrument(orderbook.instr_id)
        self.aggrbook.update_aggrbook_maker(instr, orderbook)

        if not self.config:
            return

        if self.last_update_time + self.config.update_treshold < time.time():
            self.last_update_time = time.time()
            self.update_orders()

        if self.cancel_all is True:
            self.cancel_all_pendings()

    def on_trade_exec_event(self, trade: Trade):
        # market order the other leg for the right size
        ...

    def on_order_event(self, order: Order):
        self.logger.info(f'{self.id} order event: {order}')

    @property
    def spread(self):
        """Return liq_liq_spread"""
        liq_liq_spread = self.aggrbook.liq_liq_spread(
            excl_buys=[self.config.right_leg],
            excl_sells=[self.config.left_leg])

        return liq_liq_spread

    def maker_buy(self):
        return self.aggrbook.maker_buy(excl_instrs=[self.config.right_leg])

    def maker_sell(self):
        return self.aggrbook.maker_sell(excl_instrs=[self.config.left_leg])

    def _seeker_checks(self):
        if not self.config.has_legs:
            self.logger.error(f'No legs configured in config: {self.config}')
            return False
        if not all([i.orderbook is not None for i in self.instruments.values()]):
            self.logger.error(f'Orderbook missing')
            return False
        return True

    def cancel_all_pendings(self):
        self.cancel_all = False

        self.logger.info(f'Cancelling all pending orders')
        for instr in self.instruments.values():
            self.redis_manager.orders_manager.cancel_all_orders_instr(instr)

    def cancel_pending_orders(self, orders: list[Order]):
        for order in orders:
            not_same_orders = [
                o for o in self.redis_manager.orders_manager.get_orders(
                    order.instr).values() if not order.is_same_order(o)
            ]
            for not_same_order in not_same_orders:
                self.logger.info(f'Cancelling pending order {not_same_order}')
                self.redis_manager.orders_manager.cancel_order(not_same_order)

    def update_orders(self):
        if not self.may_i_run:
            return
        if not self._seeker_checks():
            self.logger.error('Trigger checks failed')
            return

        buy, buy_size, buy_instr = self.maker_buy()
        sell, sell_size, sell_instr = self.maker_sell()
        qty = self.config.order_qty

        buy_order = Order(instr=buy_instr,
                          price=buy * 0.85,
                          qty=qty,
                          order_type=LIMIT,
                          event_type=EventTypes.MM_TRIGGER)
        sell_order = Order(instr=sell_instr,
                           price=sell * 1.15,
                           qty=-qty,
                           order_type=LIMIT,
                           event_type=EventTypes.MM_TRIGGER)

        self._fix_order_qty(buy_order, sell_order)

        self.cancel_pending_orders([buy_order, sell_order])
        self.logger.info(f'Buy order: {buy_order}')
        self.logger.info(f'Sell order: {sell_order}')
        self.send_orders([buy_order, sell_order])


class MMTriggerClient(TriggerClient):
    prompt = '(not ready) '
    linked_class = MMTrigger
    config = MMTriggerConfig()

    def __init__(self, instruments):
        if len(instruments) != 2:
            raise ValueError('MMTrigger needs exactly 2 instruments')
        super().__init__(instruments)

        self._is_ready = False
        self.config.left_leg = instruments[0]
        self.config.right_leg = instruments[1]

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @is_ready.setter
    def is_ready(self, value: bool):
        self._is_ready = value
        if self.is_ready:
            self.prompt = '(ready) '
        else:
            self.prompt = '(not ready) '

    def do_revert(self, arg):
        tmp = self.config.right_leg
        self.config.right_leg = self.config.left_leg
        self.config.left_leg = tmp

    def do_s(self, arg):
        self.do_stop(arg)

    def do_start(self, arg):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id,
                           action=START,
                           config=self.config))

    def do_stop(self, arg):
        self.send_trigger(TriggerPayload(trigger_id=self.server_id, action=STOP))

    def do_reset(self, arg):
        self.send_trigger(TriggerPayload(trigger_id=self.server_id, action='reset'))

    def do_cancel(self, arg):
        self.send_trigger(TriggerPayload(trigger_id=self.server_id, action=CANCEL))


def main():
    parser = instruments_args_parser('MMTrigger')
    parser.add_argument('--server',
                        action='store_true',
                        help='Run in server mode')
    args = parser.parse_args()

    instruments = resolve_instruments(args)

    if args.server:
        trigger = MMTrigger(instruments)
    else:
        trigger = MMTriggerClient(instruments)

    def clean_exit():
        nonlocal trigger
        if hasattr(trigger, 'disconnect'):
            trigger.disconnect()
        del trigger

    atexit.register(clean_exit)

    trigger.run()


if __name__ == '__main__':
    main()

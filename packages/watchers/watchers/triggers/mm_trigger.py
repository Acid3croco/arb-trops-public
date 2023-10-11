import time
import atexit

from dataclasses import dataclass
from arb_defines.event_types import EventTypes

from cryptofeed.defines import LIMIT, MARKET

from arb_defines.defines import CANCEL, START, STOP
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser
from db_handler.wrapper import DBWrapper
from watchers.trigger_base import TriggerBase, TriggerClient
from redis_manager.redis_events import OrderBookEvent, OrderEvent, TradeExecEvent
from arb_defines.arb_dataclasses import AggrBook, Instrument, Order, OrderBook, Trade, TriggerPayload


@dataclass
class MMTriggerConfig:
    left_leg: Instrument = None
    right_leg: Instrument = None
    order_qty: float = 0.1
    depth: int = 1
    q_mult: float = 1.1
    p_mult: float = 1.1
    update_treshold: float = 5.0
    sp: float = 1.05
    bp: float = 0.95

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

        # db = DBWrapper()
        # curr = db.get_currencies(currencies='USDT',
        #                          quote='USD',
        #                          exchange_name=FTX)
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
        liq_liq_spread = self.aggrbook.liq_liq_spread()

        return liq_liq_spread

    @property
    def exchange(self):
        return self.redis_manager.get_exchange(
            self.config.left_leg.exchange.id)

    def maker_buy(self):
        return self.aggrbook.maker_buy()

    def maker_sell(self):
        return self.aggrbook.maker_sell()

    def _seeker_checks(self):
        if not self.config.has_legs:
            self.logger.error(f'No legs configured in config: {self.config}')
            return False
        if not all(
            [i.orderbook is not None for i in self.instruments.values()]):
            self.logger.error(f'Orderbook missing')
            return False
        return True

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
        orders = []
        buy_order = None
        sell_order = None

        qty = self.config.order_qty
        bp = 1 - self.config.bp
        sp = self.config.sp - 1

        buy_bal = self.exchange.get_balance(buy_instr.quote)
        self.logger.info(buy_instr)
        self.logger.info(buy_bal)
        if buy_bal and buy_bal > 0.00003:
            for a in range(1, self.config.depth + 1):
                lebp = 1 - (bp * (a**self.config.p_mult))
                leqty = qty * (a**self.config.q_mult)
                buy_order = Order(instr=buy_instr,
                                price=buy * lebp,
                                qty=leqty,
                                order_type=LIMIT,
                                event_type=EventTypes.MM_TRIGGER)
                orders.append(buy_order)

        sell_bal = self.exchange.get_balance(sell_instr.base)
        self.logger.info(sell_instr)
        self.logger.info(sell_bal)
        if sell_bal and sell_bal > qty:
            for a in range(1, self.config.depth + 1):
                lesp = 1 + (sp * (a**self.config.p_mult))
                leqty = qty * (a**self.config.q_mult)
                sell_order = Order(instr=sell_instr,
                                price=sell * lesp,
                                qty=-leqty,
                                order_type=LIMIT,
                                event_type=EventTypes.MM_TRIGGER)
                orders.append(sell_order)

        # self.cancel_pending_orders(orders)
        self.cancel_all_pendings()
        time.sleep(1)
        # self.cancel_pending_orders(orders)
        if self.spread > 0:
            self.logger.info(f'Buy order: {buy_order}')
            self.logger.info(f'Sell order: {sell_order}')
            self.send_orders(orders)


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

    def do_s(self, arg=None):
        self.do_stop(arg)

    def do_start(self, arg=None):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id,
                           action=START,
                           config=self.config))

    def do_stop(self, arg=None):
        self.send_trigger(TriggerPayload(trigger_id=self.server_id, action=STOP))

    def do_reset(self, arg=None):
        self.send_trigger(TriggerPayload(trigger_id=self.server_id, action='reset'))

    def _set_conf(self, key, value, v_type=float, restart=False):
        if hasattr(self.config, key):
            try:
                value = v_type(value)
            except Exception:
                self.logger.error('Invalid value')
                return
            old = getattr(self.config, key)
            self.logger.info(f'{key}: {old} -> {value}')
            setattr(self.config, key, value)
            self.logger.debug(f'{key} set to {value}')
            if restart is True:
                self.do_start()

    def do_cancel(self, arg):
        self.send_trigger(TriggerPayload(trigger_id=self.server_id, action=CANCEL))

    def do_sp(self, arg):
        """ price step multiplier (e.g if sp=1.2, at each depth price change by bp/sp * 1.2) """
        self._set_conf('p_mult', arg, restart=True)

    def do_sq(self, arg):
        """ qty step multiplier (e.g if sq=1.3, at each depth qty change by order_qty * 1.3) """
        self._set_conf('q_mult', arg, restart=True)

    def do_u(self, arg):
        """ update orders every x seconds """
        self._set_conf('update_treshold', arg, restart=True)

    def do_d(self, arg):
        """ number of orders for one side """
        self._set_conf('depth', arg, v_type=int, restart=True)

    def do_qt(self, arg):
        """ qty for first order """
        self._set_conf('order_qty', arg, restart=True)

    def do_f(self, arg):
        """ % quote around bid ask (e.g if 1 will quote 1% under bid and quote 1% above ask) """
        self._order_percent(arg, 'buy')
        self._order_percent(arg, 'sell')

    def do_b(self, arg):
        """ buy order percent (e.g if 1, order will quote 1% under bid) """
        self._order_percent(arg, 'buy')

    def do_s(self, arg):
        """ sell order percent (e.g if 1, order will quote 1% above ask) """
        self._order_percent(arg, 'sell')

    def _order_percent(self, arg, side):
        try:
            val = float(arg)
        except Exception:
            self.logger.error('Invalid bp format')
            return

        if side == 'buy':
            val = 1 - (val / 100)
            self.logger.info(f'bp: {self.config.bp} -> {val}')
            self.config.bp = val
        if side == 'sell':
            val = 1 + (val / 100)
            self.logger.info(f'sp: {self.config.sp} -> {val}')
            self.config.sp = val
        self.do_start(arg)


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

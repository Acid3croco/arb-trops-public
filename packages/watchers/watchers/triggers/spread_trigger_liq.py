import math
import time
import atexit

from copy import copy
from datetime import datetime

from dataclasses import dataclass
from arb_defines.event_types import EventTypes

from cryptofeed.defines import LIMIT

from arb_defines.defines import CANCEL, LONG, SHORT
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser
from watchers.trigger_base import TriggerBase, TriggerClient
from redis_manager.redis_events import OrderBookEvent, OrderEvent, TradeExecEvent
from arb_defines.arb_dataclasses import AggrBook, Instrument, Order, OrderBook, Trade, TriggerPayload


@dataclass
class SpreadTriggerLiqConfig:
    left_leg: Instrument = None
    right_leg: Instrument = None
    need_pos_spread: bool = True
    min_spread: float = 0.001
    order_qty: float = 0.0
    retry_seconds: float = 300.0
    bp: float = 0.05
    sp: float = 0.05

    def __post_init__(self):
        if self.left_leg and not isinstance(self.left_leg, Instrument):
            self.left_leg = Instrument(**self.left_leg)
        if self.right_leg and not isinstance(self.right_leg, Instrument):
            self.right_leg = Instrument(**self.right_leg)

    @property
    def has_legs(self):
        return self.right_leg and self.left_leg and (self.right_leg !=
                                                     self.left_leg)


class SpreadTriggerLiq(TriggerBase):
    config_class = SpreadTriggerLiqConfig

    def __init__(self, instruments) -> None:
        if len(instruments) != 2:
            raise ValueError('SpreadTriggerLiq needs exactly 2 instruments')

        super().__init__(instruments)

        self.aggrbook = AggrBook()
        self.config: SpreadTriggerLiqConfig = None
        self.trigger_timestamp = None
        self.side = None

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments),
                                           self.on_order_book_event)
        self.redis_manager.subscribe_event(OrderEvent(self.instruments),
                                           self.on_order_event)
        self.redis_manager.subscribe_event(TradeExecEvent(self.instruments),
                                           self.on_trade_exec_event)

    def on_order_book_event(self, orderbook: OrderBook):
        instr = self.instruments.get(orderbook.instr_id)
        self.aggrbook.update_aggrbook(instr, orderbook)

        if self.trigger_timestamp and self.config and self.config.retry_seconds and self.trigger_timestamp + self.config.retry_seconds > time.time(
        ):
            self.logger.info(
                f'Retrying trigger until {datetime.fromtimestamp(self.trigger_timestamp + self.config.retry_seconds)}'
            )
            self._build_orders(self.side)

    def on_order_event(self, order: Order):
        # handle rejects because of post only
        # wait for cancel ack before placing another order
        self.logger.info(f'Order event: {order}')
        pass

    def on_trade_exec_event(self, trade: Trade):
        # handle exec and stop updating order
        pass

    def on_trigger_event(self, payload: TriggerPayload):
        super().on_trigger_event(payload)
        self.logger.info(self.config)

        match payload.action:
            case 'long' | 'short':
                self.trigger_timestamp = time.time()
                self.side = payload.action
                self._build_orders(side=payload.action)
            case 'cancel':
                self._stop_retry()
                self.cancel_all_pendings()

    def _stop_retry(self):
        self.side = None
        self.trigger_timestamp = None

    @property
    def spread(self):
        return self.aggrbook.liq_liq_spread(excl_buys=[self.config.right_leg],
                                            excl_sells=[self.config.left_leg])

    def taker_buy(self):
        return self.aggrbook.taker_buy(excl_instrs=[self.config.right_leg])

    def taker_sell(self):
        return self.aggrbook.taker_sell(excl_instrs=[self.config.left_leg])

    def maker_buy(self):
        return self.aggrbook.maker_buy(excl_instrs=[self.config.right_leg])

    def maker_sell(self):
        return self.aggrbook.maker_sell(excl_instrs=[self.config.left_leg])

    def _check_spreads(self):
        if not self.config.need_pos_spread:
            return True

        spread = self.spread
        if spread and spread > self.config.min_spread:
            self.logger.info(f'Spread: {(spread or 0) * 100:.5f}%')
            return True
        self.logger.error(
            f'Spread too small: {(spread or 0) * 100:.5f}% < {self.config.min_spread * 100:.5f}%'
        )
        return False

    def _trigger_checks(self):
        if not self.config.has_legs:
            self.logger.error(f'No legs configured in config: {self.config}')
            return False
        return True

    def _build_orders(self, side: str):
        if not side:
            self.logger.error('No side configured')
            return
        if not self._trigger_checks():
            self.logger.error('Trigger checks failed')
            return
        if not self._check_spreads():
            self.logger.error('Spread too small')
            return

        self.logger.info(f'Building orders for side {side}')

        buy, buy_size, buy_instr = self.maker_buy()
        sell, sell_size, sell_instr = self.maker_sell()
        qty = self.config.order_qty

        buy_order = Order(instr=buy_instr,
                          price=buy * (1 - self.config.fp),
                          qty=qty,
                          order_type=LIMIT,
                          event_type=EventTypes.SPREAD_TRIGGER_LIQ)
        sell_order = Order(instr=sell_instr,
                           price=sell * (1 + self.config.fp),
                           qty=-qty,
                           order_type=LIMIT,
                           event_type=EventTypes.SPREAD_TRIGGER_LIQ)

        self._stop_retry()

        # self._fix_order_qty(buy_order, sell_order)
        self.logger.info(f'Buy: {buy_order}')
        self.logger.info(f'Sell: {sell_order}')
        self.send_orders([buy_order, sell_order])

    def _fix_order_qty(self, order1: Order, order2: Order):
        size = self.config.order_qty
        order1.qty = math.copysign(size / order1.price, order1.qty)
        order2.qty = math.copysign(size / order2.price, order2.qty)

        round_size = min(abs(order1.r_qty), abs(order2.r_qty))
        order1.qty = math.copysign(round_size, order1.qty)
        order2.qty = math.copysign(round_size, order2.qty)


class SpreadTriggerLiqClient(TriggerClient):
    prompt = '(not ready) '
    linked_class = SpreadTriggerLiq
    config = SpreadTriggerLiqConfig()

    def __init__(self, instruments):
        if len(instruments) != 2:
            raise ValueError('SpreadTriggerLiq needs exactly 2 instruments')
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

    def do_long(self, arg):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id, action=LONG,
                           config=self.config))

    def do_short(self, arg):
        config = copy(self.config)
        # Inverse legs to short
        self.logger.info(
            f'Inverting legs {config.left_leg} and {config.right_leg}')
        left_leg = config.left_leg
        config.left_leg = config.right_leg
        config.right_leg = left_leg
        self.logger.info(
            f'Inverted legs {config.left_leg} and {config.right_leg}')
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id, action=SHORT, config=config))

    def do_c(self, arg):
        self.do_cancel(arg)

    def do_cancel(self, arg):
        self.send_trigger(TriggerPayload(trigger_id=self.server_id, action=CANCEL))


def main():
    parser = instruments_args_parser('SpreadTriggerLiq')
    parser.add_argument('--server',
                        action='store_true',
                        help='Run in server mode')
    args = parser.parse_args()

    instruments = resolve_instruments(args)

    if args.server:
        trigger = SpreadTriggerLiq(instruments)
    else:
        trigger = SpreadTriggerLiqClient(instruments)

    def clean_exit():
        nonlocal trigger
        if hasattr(trigger, 'disconnect'):
            trigger.disconnect()
        del trigger

    atexit.register(clean_exit)

    trigger.run()


if __name__ == '__main__':
    main()

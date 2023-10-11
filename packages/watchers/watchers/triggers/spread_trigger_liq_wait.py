import math
import time
import atexit

from copy import copy
from datetime import datetime

from dataclasses import dataclass
from arb_defines.event_types import EventTypes

from cryptofeed.defines import LIMIT, FTX, BUY

from arb_defines.defines import CANCEL, LONG, SHORT, NEW
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser
from watchers.trigger_base import TriggerBase, TriggerClient
from redis_manager.redis_events import OrderBookEvent, OrderEvent, PositionEvent, TradeExecEvent
from arb_defines.arb_dataclasses import AggrBook, Instrument, Order, OrderBook, Position, Trade, TriggerPayload


@dataclass
class SpreadTriggerLiqWaitConfig:
    left_leg: Instrument = None
    right_leg: Instrument = None
    need_pos_spread: bool = True
    first_exch: str = FTX
    min_spread: float = 0.001
    order_qty: float = 1.0
    update_sec: float = 1.0
    retry_seconds: float = 3000.0
    fp: float = 0.05

    def __post_init__(self):
        if self.left_leg and not isinstance(self.left_leg, Instrument):
            self.left_leg = Instrument(**self.left_leg)
        if self.right_leg and not isinstance(self.right_leg, Instrument):
            self.right_leg = Instrument(**self.right_leg)

    @property
    def has_legs(self):
        return self.right_leg and self.left_leg and (self.right_leg !=
                                                     self.left_leg)


class SpreadTriggerLiqWait(TriggerBase):
    """
    This trigger place chase limit order on one side and wait to be executed, then place limit chase on the other side
    """
    config_class = SpreadTriggerLiqWaitConfig

    def __init__(self, instruments) -> None:
        if len(instruments) != 2:
            raise ValueError(
                'SpreadTriggerLiqWait needs exactly 2 instruments')

        super().__init__(instruments)

        self.aggrbook = AggrBook()
        self.config: SpreadTriggerLiqWaitConfig = None
        self.trigger_timestamp = None
        self.side = None
        self.leg_state = None
        self.last_update_ts = None
        self.first_order: Order = None
        self.hedge_order: Order = None

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments),
                                           self.on_order_book_event)
        self.redis_manager.subscribe_event(OrderEvent(self.instruments),
                                           self.on_order_event)
        self.redis_manager.subscribe_event(TradeExecEvent(self.instruments),
                                           self.on_trade_exec_event)
        self.redis_manager.subscribe_event(PositionEvent(self.instruments),
                                           self.on_position_event)

    def on_trigger_event(self, payload: TriggerPayload):
        super().on_trigger_event(payload)
        self.logger.info(self.config)

        match payload.action:
            case 'long' | 'short':
                self.trigger_timestamp = time.time()
                self.side = payload.action
                self.send_first_order(side=payload.action)
            case 'cancel':
                self._stop_retry()
                self.leg_state = None
                self.cancel_all_pendings()

    def on_order_book_event(self, orderbook: OrderBook):
        instr = self.instruments.get(orderbook.instr_id)
        self.aggrbook.update_aggrbook(instr, orderbook)

        if self.trigger_timestamp and self.config and self.config.retry_seconds and self.trigger_timestamp + self.config.retry_seconds > time.time(
        ):
            self.logger.info(
                f'Retrying trigger until {datetime.fromtimestamp(self.trigger_timestamp + self.config.retry_seconds)}'
            )
            self.send_first_order(self.side)
        elif self.leg_state == 1:
            self.update_order(self.first_order)
        elif self.leg_state == 2:
            self.update_order(self.hedge_order)

    def on_order_event(self, order: Order):
        # handle rejects because of post only
        # wait for cancel ack before placing another order
        self.logger.info(f'Order event: {order}')
        if self.first_order and order == self.first_order:
            self.first_order = order
        elif self.hedge_order and order == self.hedge_order:
            self.hedge_order = order

    def on_trade_exec_event(self, trade: Trade):
        trade.instr = self.redis_manager.get_instrument(trade)
        delta = self.curr_delta()
        self.logger.info(f'Trade executed: {trade}, adjusting hedge if necessary')

        if abs(delta) >= self.config.order_qty:
            self.cancel_pending_instr(trade.instr)
            self.send_hedge_order(trade, delta)
        else:
            self.logger.info(f'Delta {delta} < order qty {self.config.order_qty}, may be partial fill, do nothing')

        if delta >= self.config.order_qty:
            self.first_order = None
        elif delta <= -self.config.order_qty:
            self.hedge_order = None
        else:
            self.logger.info(
                f'Trade executed: {trade}, Correctly hedged, thanks for playing'
            )
            self.leg_state = None

    def on_position_event(self, position: Position):
        self.curr_delta()

    def curr_delta(self):
        instr1 = self.redis_manager.get_instrument(self.config.left_leg)
        instr2 = self.redis_manager.get_instrument(self.config.right_leg)
        pos1: Position = instr1.position
        pos2: Position = instr2.position
        delta = abs(pos1.qty) - abs(pos2.qty)
        self.logger.info(f'POS1 {pos1}')
        self.logger.info(f'POS2 {pos2}')
        self.logger.info(f'DELTA {delta}')
        self.delta = delta
        return delta

    def _stop_retry(self):
        self.side = None
        self.trigger_timestamp = None

    @property
    def spread(self):
        return self.aggrbook.liq_liq_spread(excl_buys=[self.config.right_leg],
                                            excl_sells=[self.config.left_leg])

    def maker_buy(self):
        return self.aggrbook.maker_buy(excl_instrs=[self.config.right_leg])

    def maker_sell(self):
        return self.aggrbook.maker_sell(excl_instrs=[self.config.left_leg])

    def _check_spreads(self):
        if self.leg_state == 2:
            return True
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

    def send_first_order(self, side: str):
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

        if buy_instr.exchange == self.config.first_exch:
            order = Order(instr=buy_instr,
                          price=buy * (1 - self.config.fp),
                          qty=qty,
                          order_type=LIMIT,
                          event_type=EventTypes.SPREAD_TRIGGER_LIQ_WAIT)
        else:
            order = Order(instr=sell_instr,
                          price=sell * (1 + self.config.fp),
                          qty=-qty,
                          order_type=LIMIT,
                          event_type=EventTypes.SPREAD_TRIGGER_LIQ_WAIT)

        self._stop_retry()
        self.logger.info(f'Placing first order: {order}')
        self.leg_state = 1
        self.first_order = order
        self.last_update_ts = time.time()
        self.send_order(order)

    def send_hedge_order(self, trade: Trade, delta):
        if delta < self.config.order_qty:
            self.logger.error(
                f'Hedge order qty too small: {trade.qty} < {self.config.order_qty}, maybe because of partial fills'
            )
            return
        instr = self.config.right_leg if trade.instr == self.config.left_leg else self.config.left_leg
        instr = self.redis_manager.get_instrument(instr)
        price, _ = instr.orderbook.ask(
        ) if trade.side == BUY else instr.orderbook.bid()
        qty = math.copysign(delta, -trade.qty)
        fp = (1 + self.config.fp) if trade.side == BUY else (1 -
                                                             self.config.fp)

        order = Order(instr=instr,
                      price=price * fp,
                      qty=qty,
                      order_type=LIMIT,
                      event_type=EventTypes.SPREAD_TRIGGER_LIQ_WAIT)

        self.logger.info(f'Placing hedge order {order}')
        self.leg_state = 2
        self.hedge_order = order
        self.last_update_ts = time.time()
        self.send_order(order)

    def update_order(self, old_order):
        if self.leg_state is None:
            self.logger.error('Leg state is None')
            return
        if old_order.order_status == NEW:
            self.logger.debug(f'Order {old_order} is still new')
            return
        if self.last_update_ts and self.last_update_ts + self.config.update_sec > time.time(
        ):
            self.logger.debug(f'Order {old_order} is too recent')
            return
        state = 'first' if self.leg_state == 1 else 'hedge'

        order = Order.from_order(old_order)
        if self.leg_state == 2:
            order.qty = -self.curr_delta()
        order.set_instr(self.redis_manager.get_instrument(old_order))
        if order.side == BUY:
            curr_price, _ = order.instr.orderbook.bid()
            if curr_price > old_order.price:
                order.price = curr_price * (1 - self.config.fp)
            else:
                return
        else:
            curr_price, _ = order.instr.orderbook.ask()
            if curr_price < old_order.price:
                order.price = curr_price * (1 + self.config.fp)
            else:
                return

        self.cancel_order(old_order)
        if self.leg_state == 1:
            self.first_order = order
        elif self.leg_state == 2:
            self.hedge_order = order

        self.logger.info(f'Sending updated {state} order: {order}')
        self.last_update_ts = time.time()
        self.send_order(order)


class SpreadTriggerLiqWaitClient(TriggerClient):
    prompt = '(not ready) '
    linked_class = SpreadTriggerLiqWait
    config = SpreadTriggerLiqWaitConfig()

    def __init__(self, instruments):
        if len(instruments) != 2:
            raise ValueError(
                'SpreadTriggerLiqWait needs exactly 2 instruments')
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
    parser = instruments_args_parser('SpreadTriggerLiqWait')
    parser.add_argument('--server',
                        action='store_true',
                        help='Run in server mode')
    args = parser.parse_args()

    instruments = resolve_instruments(args)

    if args.server:
        trigger = SpreadTriggerLiqWait(instruments)
    else:
        trigger = SpreadTriggerLiqWaitClient(instruments)

    def clean_exit():
        nonlocal trigger
        if hasattr(trigger, 'disconnect'):
            trigger.disconnect()
        del trigger

    atexit.register(clean_exit)

    trigger.run()


if __name__ == '__main__':
    main()

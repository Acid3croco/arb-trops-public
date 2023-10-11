import math
import uuid

from cryptofeed.defines import SPOT

from watchers.watcher_base import WatcherBase
from redis_manager.redis_wrappers import ExchangeRedis
from arb_defines.arb_dataclasses import Balance, Order, Position
from redis_manager.redis_events import BalanceEvent, OrderEvent, PositionEvent, TradeExecEvent


class ExecutorBase(WatcherBase):
    """Base class for executors."""
    has_orders = True
    has_status = True

    def __init__(self, instruments) -> None:
        if not instruments:
            self.logger.critical(f'Not instrument given, stopping now')
            exit(1)

        super().__init__(instruments)

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(BalanceEvent(self.exchanges))
        self.redis_manager.subscribe_event(PositionEvent(self.instruments))

        self.redis_manager.subscribe_event(OrderEvent(self.instruments))
        self.redis_manager.subscribe_event(TradeExecEvent(self.instruments))

    def check_order(self, order: Order) -> bool:
        # TODO: use codes to return instead of bool
        size = order.r_qty != 0
        status = self._check_status_exchange_api(order)
        bal = True  # self._check_balance_for_order(order)
        return size and status and bal

    def send_order(self, order: Order, checked=False):
        if checked == True or self.check_order(order):
            self.logger.info(f'Sending order: {order}')
            self.redis_manager.orders_manager.fire_order(order)
        else:
            self.logger.error(f'Order {order} is not valid, skipping')

    def send_orders(self, orders: list[Order], checked=False, eq_size=False):
        checks = [self.check_order(o) for o in orders]

        if checked or all(checks):
            event_key = uuid.uuid4()
            for order in orders:
                order.event_key = event_key
                self.send_order(order, checked=True)
        else:
            self.logger.error(
                f'Some orders are not valid, skipping - {checks} - {orders}')

    def cancel_all_pendings(self):
        self.logger.info(f'Cancelling all pending orders')
        for instr in self.instruments.values():
            self.redis_manager.orders_manager.cancel_all_orders_instr(instr)

    def cancel_pending_instr(self, instr):
        self.logger.info(f'Cancelling pending orders for instr {instr}')
        self.redis_manager.orders_manager.cancel_all_orders_instr(instr)

    def cancel_order(self, order):
        self.logger.info(f'Cancelling order {order}')
        self.redis_manager.orders_manager.cancel_order(order)

    def _check_status_exchange_api(self, order: Order) -> bool:
        ex: ExchangeRedis = self.exchanges.get(order.instr.exchange.id)
        if not ex.status.trading_up:
            self.logger.error(
                f'Exchange {ex} is not up, skipping order {order}')
            return False
        return True

    def _check_balance_for_order(self, order: Order) -> bool:
        # TODO: include leverage in the check
        bal: Balance = self.exchanges.get(order.instr.exchange.id).get_balance(
            order.instr.quote)

        # TODO: handle borrow short spot
        if order.instr.instr_type == SPOT:
            if bal.qty * 1.1 < order.cost:
                self.logger.error(
                    f'Not enough balance {bal} for order: {order}')
                return False

        pos: Position = order.instr.position
        incr_pos = order.qty * pos.qty > 0
        leverage = 1
        if incr_pos and (bal.qty * leverage) * 1.1 < order.cost:
            self.logger.error(
                f'Cant add to position {pos}: not enough balance {bal} for order: {order}'
            )
            return False

        return True

    def _fix_order_qty(self, order1: Order, order2: Order, qty=None):
        if qty is not None:
            order1.qty = math.copysign(qty, order1.qty)
            order2.qty = math.copysign(qty, order2.qty)

        round_size = min(abs(order1.r_qty), abs(order2.r_qty))
        order1.qty = math.copysign(round_size, order1.qty)
        order2.qty = math.copysign(round_size, order2.qty)

    def _fix_order_size(self, size, order1: Order, order2: Order):
        order1.qty = math.copysign(size / order1.price, order1.qty)
        order2.qty = math.copysign(size / order2.price, order2.qty)

        round_size = min(abs(order1.r_qty), abs(order2.r_qty))
        order1.qty = math.copysign(round_size, order1.qty)
        order2.qty = math.copysign(round_size, order2.qty)

    def _fix_orders_size(self, size, orders: list[Order]) -> list[Order]:
        """ONLY WORKS WITH ORDERS WITH COMMON BASE/QUOTE"""
        for order in orders:
            order.qty = math.copysign(size / order.price, order.qty)
        round_size = min([abs(o.r_qty) for o in orders])
        for order in orders:
            order.qty = math.copysign(round_size, order.qty)

        return orders

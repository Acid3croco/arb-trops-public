import logging

from datetime import datetime

from tabulate import tabulate
from cryptofeed.defines import *
from curses import curs_set, wrapper

from arb_defines.defines import *
from arb_logger.logger import get_logger
from arb_utils.resolver import resolve_instruments
from redis_manager.redis_events import OrderEvent
from redis_manager.redis_manager import RedisManager
from arb_defines.arb_dataclasses import Instrument, Order
from arb_utils.args_parser import instruments_args_parser
from redis_manager.orders_manager import ExchangeOrdersManager

LOGGER = get_logger('show_orders', log_in_file=False, level=logging.DEBUG)


class ShowOrders:
    header = ['Time', 'Qty', 'Price', 'Notio $', 'Status', 'ID']

    def __init__(self, instruments: list[Instrument], args) -> None:
        self.args = args
        if self.args.live:
            LOGGER.setLevel(logging.WARNING)
        self.redis_manager: RedisManager = RedisManager(instruments,
                                                        logger=LOGGER,
                                                        has_orders=True)

    @property
    def exch_managers(self) -> list[ExchangeOrdersManager]:
        return self.redis_manager.orders_manager.exchange_orders_managers.values(
        )

    def show(self):
        if self.args.live:
            wrapper(self._show_live)
        else:
            self._show_snap()

    def _print(self, row=0, col=0, text='BOUZA'):
        if self.args.live:
            self.stdout.addstr(row, col, text)
        else:
            print(f"{' ' * col}{text}")

    def draw_orders(self, exchange, instrument, orders: list[Order], row):
        self._print(row, 0, str(exchange))
        row += 1
        self._print(
            row, 4,
            f'{str(instrument).ljust(45)} count: {str(len(orders)).ljust(5)}')
        self._print(
            row, 70,
            f'sell: {str(sum([o[1] for o in orders if  o[1] < 0])).ljust(5)}')
        row += 1
        self._print(row, 50, f'notio: {round(sum([o[3] for o in orders]), 3)}')
        self._print(
            row, 70,
            f'buy: {str(sum([o[1] for o in orders if o[1] > 0])).ljust(5)}')
        row += 1
        orders.sort(key=lambda o: o[2], reverse=True)
        for l in tabulate(orders, headers=self.header).split('\n'):
            if row - 1 > self.stdout.getmaxyx()[0]:
                break
            row += 1
            self._print(row, 8, l)
        return row + 2

    def _show_snap(self):
        if self.args.live:
            self.stdout.clear()

        count = 0
        notional = 0
        row = 0

        for exch_manager in self.exch_managers:
            LOGGER.debug
            for instr_manager in exch_manager.instr_orders_managers.values():
                orders = []
                for order in instr_manager.orders.values():
                    count += 1
                    order_notio = abs(order.qty) * order.price
                    notional += order_notio
                    timez = order.time.strftime('%H:%M:%S:%f')
                    if order.time_open:
                        if isinstance(order.time_open, str):
                            order.time_open = datetime.fromisoformat(
                                order.time_open)
                        order.time_open.strftime('%H:%M:%S:%f')
                    if order.time_ack_mkt:
                        if isinstance(order.time_ack_mkt, str):
                            order.time_ack_mkt = datetime.fromisoformat(
                                order.time_ack_mkt)
                        order.time_ack_mkt.strftime('%H:%M:%S:%f')
                    orders.append([
                        timez, order.qty, order.price, order_notio,
                        order.order_status, order.id
                    ])
                if orders:
                    row = self.draw_orders(exch_manager.exchange,
                                           instr_manager.instrument, orders,
                                           row)

        if not count:
            if self.args.live:
                self._print(0, 0, 'No orders found')
            else:
                LOGGER.warning('No orders found')

        if self.args.live:
            self.stdout.refresh()

    def _subscribe_to_exchanges(self):
        self.redis_manager.subscribe_event(
            OrderEvent(self.redis_manager.instruments.values()),
            self._on_order_event)

    def _on_order_event(self, order):
        order.instr = self.redis_manager.get_instrument(order)
        self._refresh_live()

    def _show_live(self, stdout):
        curs_set(0)
        stdout.nodelay(True)
        self.stdout = stdout

        self._subscribe_to_exchanges()
        self._refresh_live()
        self.redis_manager.run()

    def _refresh_live(self):
        self._show_snap()


def main():
    parser = instruments_args_parser('Show orders on instruments')
    parser.add_argument('-s',
                        '--sort',
                        type=str,
                        choices=['instr', 'rate', 'predicted'],
                        default='predicted')
    parser.add_argument('-z',
                        '--zero',
                        action='store_true',
                        help='show null orders')
    parser.add_argument('-l', '--live', action='store_true')

    args = parser.parse_args()

    instruments = resolve_instruments(args)
    show_orders = ShowOrders(instruments, args)
    show_orders.show()


if __name__ == '__main__':
    main()

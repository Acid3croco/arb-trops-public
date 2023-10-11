import atexit
import sys

from cryptofeed.defines import LIMIT

from arb_defines.arb_dataclasses import Instrument, OrderBook, Order
from arb_utils.args_parser import instruments_args_parser
from arb_utils.resolver import resolve_instruments
from redis_manager.redis_events import OrderBookEvent
from watchers.executor_base import ExecutorBase


class CancelOrder(ExecutorBase):

    def __init__(self, instrument: Instrument, order_id: str):
        super().__init__([instrument])
        self.instrument = instrument

        orders: dict[str, Order] = self.redis_manager.orders_manager.all_orders
        order: Order | None = orders.get(order_id)
        self.redis_manager.orders_manager.cancel_order(order)


def main():
    parser = instruments_args_parser('Send orders')

    parser.add_argument('-o', '--order-id', type=str, help='Order ID')

    args = parser.parse_args()

    instruments = resolve_instruments(args)

    first_instr: Instrument = instruments[0]
    if len(instruments) > 1:
        print(f'Multiple instruments found: {instruments}')
        print('Use --instrument to specify one')
        return

    CancelOrder(first_instr, args.order_id)


if __name__ == '__main__':
    main()

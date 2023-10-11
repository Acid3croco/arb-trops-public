import atexit
import sys

from cryptofeed.defines import LIMIT

from arb_defines.arb_dataclasses import Instrument, OrderBook, Order
from arb_utils.args_parser import instruments_args_parser
from arb_utils.resolver import resolve_instruments
from redis_manager.redis_events import OrderBookEvent
from watchers.executor_base import ExecutorBase


class SingleOrder(ExecutorBase):

    def __init__(self,
                 instrument: Instrument,
                 qty: float,
                 limit: int,
                 price: int,
                 checked=True):
        super().__init__([instrument])
        self.instrument = instrument
        self.qty = qty
        self.limit = limit
        self.price = price
        self.checked = checked

        if self.limit is None and self.price is None:
            raise ValueError('Limit or price must be set')

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments),
                                           self.on_order_book_event)

    def on_order_book_event(self, orderbook: OrderBook):
        instr = self.instruments.get(orderbook.instr_id)
        if instr is None:
            self.logger.error(f'Instrument {orderbook.instr_id} not found')
            return
        self.logger.info(f'Orderbook {orderbook}')
        price = self.price
        if price is None and self.limit is not None:
            price, size = orderbook.ask(
                self.limit) if self.qty < 0 else orderbook.bid(self.limit)
        if self.limit is not None and abs(self.qty) > size:
            self.logger.info(
                f'Qty bigger than available market size {self.qty} {instr}')
            return
        self.logger.info(f'Price {price}')
        self.send_order(Order(
            instr=instr,
            price=price,
            qty=self.qty,
            order_type=LIMIT,
        ),
                        checked=self.checked)
        self.logger.info(f'Order sent {self.qty}@{price} {instr}')
        sys.exit(0)


def main():
    parser = instruments_args_parser('Send orders')
    parser.add_argument('--qty', type=float, help='Qty of the order')
    parser.add_argument('--price', type=float, help='price')
    parser.add_argument(
        '--limit',
        type=int,
        help='limit of orderbook. bid for qty<0, ask for qty>0')

    parser.add_argument('--checked', action='store_true')

    args = parser.parse_args()

    instruments = resolve_instruments(args)

    first_instr: Instrument = instruments[0]
    if len(instruments) > 1:
        print(f'Multiple instruments found: {instruments}')
        print('Use --instrument to specify one')
        return

    executor = SingleOrder(first_instr, args.qty, args.limit, args.price,
                           args.checked)

    def clean_exit():
        nonlocal executor
        if hasattr(executor, 'disconnect'):
            executor.disconnect()
        del executor

    atexit.register(clean_exit)

    executor.run()


if __name__ == '__main__':
    main()

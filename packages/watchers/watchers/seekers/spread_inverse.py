from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser

from watchers.seeker_base import SeekerBase
from arb_defines.arb_dataclasses import OrderBook
from redis_manager.redis_events import OrderBookEvent


class SpreadInverseSeeker(SeekerBase):
    short_logger = True

    def __init__(self, instruments) -> None:
        if len(instruments) != 2:
            raise ValueError("PairSeeker only works with 2 instruments")

        super().__init__(instruments)

    def subscribe_to_events(self):
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments),
                                           self.on_orderbook_event)
        super().subscribe_to_events()

    def on_orderbook_event(self, orderbook: OrderBook):
        self.logger.info(
            f"Orderbook event received for {orderbook.instr_id}: {orderbook.bid()[0]}"
        )


def main():
    parser = instruments_args_parser(SpreadInverseSeeker.__class__.__name__)
    args = parser.parse_args()

    instruments = resolve_instruments(args)

    SpreadInverseSeeker(instruments).run()

import logging

from dataclasses import dataclass
from collections import defaultdict

from watchers.watcher_base import WatcherBase
from arb_utils.resolver import resolve_instruments
from redis_manager.redis_events import OrderBookEvent
from arb_utils.args_parser import instruments_args_parser
from arb_defines.arb_dataclasses import AggrBook, Instrument


@dataclass
class SpreadInfo:
    instr1: Instrument
    instr2: Instrument
    spread: float


class MultiExchSpreadWatcher(WatcherBase):
    log_level = logging.INFO
    log_redis_handler = False

    def __init__(self, instruments):
        if len(instruments) < 2:
            self.logger.error(
                f'Need at least 2 instruments to watch: {instruments}')
            exit(1)

        super().__init__(instruments)

        self.all_spreads: dict[str, SpreadInfo] = {}
        self.aggr_books = defaultdict(AggrBook)

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments),
                                           self.on_orderbook_event)

        self.redis_manager.heartbeat_event(1, self.show_spreads)

    def on_orderbook_event(self, orderbook):
        instr = self.instruments[orderbook.instr_id]

        aggr_book = self.aggr_books[instr.base]
        aggr_book.update_aggrbook(instr, orderbook)

        if aggr_book and len(aggr_book.orderbooks) > 1:
            spread = aggr_book.hit_hit_spread()
            _, _, instr1 = aggr_book.taker_buy()
            _, _, instr2 = aggr_book.taker_sell()
            if spread > 0:
                self.all_spreads[instr.base] = SpreadInfo(
                    instr1, instr2, spread)
            elif instr.base in self.all_spreads:
                del self.all_spreads[instr.base]

    def show_spreads(self):
        if not self.all_spreads:
            return

        self.logger.info('\n\n\n\n\nCurrent spreads:')
        _spreads = sorted([a for a in self.all_spreads.items()],
                          key=lambda x: x[1].spread)

        for instr_base, spread_info in _spreads:
            self.logger.info(
                f'{instr_base.ljust(6)}: {spread_info.spread:.4f} - {spread_info.instr1} - {spread_info.instr2}'
            )


def main():
    parser = instruments_args_parser('SpreadWatcher')
    args = parser.parse_args()

    instruments = resolve_instruments(args)

    MultiExchSpreadWatcher(instruments).run()


if __name__ == '__main__':
    main()

import logging

from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser

from watchers.watcher_base import WatcherBase
from arb_defines.arb_dataclasses import Instrument
from redis_manager.redis_events import OrderBookEvent, TradeEvent


class SpreadWatcher(WatcherBase):
    log_level = logging.INFO
    log_redis_handler = False

    def __init__(self, instruments):
        super().__init__(instruments)

        self.all_spreads: dict[Instrument, float] = {}

    def subscribe_to_events(self):
        super().subscribe_to_events()
        # self.redis_manager.subscribe_event(TradeEvent(self.instruments),
        #                                    self.on_trade_event)
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments),
                                           self.on_orderbook_event)

        self.redis_manager.heartbeat_event(1, self.show_spreads)

    def on_orderbook_event(self, orderbook):
        instr = self.instruments[orderbook.instr_id]

        if instr.orderbook:
            spread = instr.orderbook.spread_pct()
            if spread < 0.15:
                self.all_spreads[instr] = spread
            elif instr in self.all_spreads:
                del self.all_spreads[instr]

    def show_spreads(self):
        if not self.all_spreads:
            return

        self.logger.info('\n\n\n\n\nCurrent spreads:')
        _spreads = sorted([a for a in self.all_spreads.items()],
                          key=lambda x: x[1])

        for instr, spread in _spreads:
            self.logger.info(f'{instr.instr_code}: {spread}')


def main():
    parser = instruments_args_parser('SpreadWatcher')
    args = parser.parse_args()

    instruments = resolve_instruments(args)

    SpreadWatcher(instruments).run()


if __name__ == '__main__':
    main()

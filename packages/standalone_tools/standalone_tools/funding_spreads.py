from collections import defaultdict

from tabulate import tabulate
from curses import curs_set, wrapper

from watchers.watcher_base import WatcherBase
from arb_utils.resolver import resolve_instruments
from arb_defines.arb_dataclasses import FundingRate
from redis_manager.redis_events import FundingRateEvent
from redis_manager.redis_wrappers import InstrumentRedis
from arb_utils.args_parser import instruments_args_parser


class FundingSpreads(WatcherBase):

    def __init__(self, instruments, args) -> None:
        instruments = self._exclude_instruments(instruments)
        super().__init__(instruments)
        self.logger.setLevel('WARNING')

        self.fundings: defaultdict[tuple(str, str),
                                   dict[InstrumentRedis,
                                        FundingRate]] = defaultdict(dict)

        self._load_fundings()

    def _exclude_instruments(self, instruments):
        new_instruments = []

        for instr in instruments:
            if instr.base in ['PRIV']:
                continue
            new_instruments.append(instr)

        return new_instruments

    def _load_fundings(self):
        for instr in self.instruments.values():
            if instr.funding_rate is not None and instr.funding_rate.is_up_to_date:
                key: tuple[str, str] = (instr.base, instr.contract_type)
                self.fundings[key][instr] = instr.funding_rate

    def subscribe_to_events(self):
        self.redis_manager.subscribe_event(FundingRateEvent(self.instruments),
                                           self.on_funding_rate_event)

    def on_funding_rate_event(self, funding_rate: FundingRate):
        self.logger.info(f'Funding rate event: {funding_rate}')
        instr = self.instruments.get(funding_rate.instr_id)
        if not instr:
            self.logger.error(
                f'Unknown instrument id: {funding_rate.instr_id}')

        key: tuple[str, str] = (instr.base, instr.contract_type)
        self.fundings[key][instr] = funding_rate

        self._refresh_screen()

    def _draw_table(self, table):
        row = 0
        for l in table.split('\n'):
            max_row = self.stdout.getmaxyx()[0] - 4
            if row > max_row:
                break
            row += 1
            self.stdout.addstr(row, 0, l)

    def _refresh_screen(self):
        self.stdout.clear()

        header = [
            'Base', 'APR spread', 'Exchange', 'APR Rate', 'APR Rate',
            'Exchange', 'len'
        ]
        fundings = []

        for key, _fundings in self.fundings.items():
            base, _ = key
            if len(_fundings) < 2:
                continue

            _fundings: list[tuple[InstrumentRedis, FundingRate]] = sorted(
                list(_fundings.items()), key=lambda x: x[1].rate)
            f_instr, f_fr = _fundings[0]
            l_instr, l_fr = _fundings[-1]

            spread = round(l_fr.apr - f_fr.apr, 4)
            if spread == 0:
                continue

            fundings.append((base, spread, f_instr.exchange, f_fr.apr,
                             l_fr.apr, l_instr.exchange, len(_fundings)))

        fundings.sort(key=lambda x: x[1], reverse=True)
        table = tabulate(fundings, headers=header)
        self._draw_table(table)

        self.stdout.refresh()

    def _show(self, stdout):
        curs_set(0)
        stdout.nodelay(True)
        self.stdout = stdout

        self._refresh_screen()
        self.run()

    def show(self):
        wrapper(self._show)


def main():
    parser = instruments_args_parser(description='Show funding spreads.')
    args = parser.parse_args()

    instruments = resolve_instruments(args)
    funding_spreads = FundingSpreads(instruments, args)
    funding_spreads.show()

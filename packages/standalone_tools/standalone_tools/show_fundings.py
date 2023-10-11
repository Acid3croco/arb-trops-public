from tabulate import tabulate

from cryptofeed.defines import PERPETUAL

from arb_logger.logger import get_logger
from arb_utils.resolver import resolve_instruments
from redis_manager.redis_manager import RedisManager
from redis_manager.redis_wrappers import InstrumentRedis
from arb_utils.args_parser import instruments_args_parser

tabulate.WIDE_CHARS_MODE = False
LOGGER = get_logger('show_fundings', log_in_file=False)


class ShowFundings:

    def __init__(self, args) -> None:
        self.args = args
        self._instruments = resolve_instruments(args, instr_types=PERPETUAL)
        self.redis_manager: RedisManager = RedisManager(self._instruments,
                                                        logger=LOGGER,
                                                        has_orders=False)

    @property
    def instruments(self) -> list[InstrumentRedis]:
        return self.redis_manager.instruments.values()

    def show(self):
        header = [
            'Instr',
            'Funding (%)',
            'Predicted (%)',
            'APR (%)',
            'APY (%)',
            'Update time',
        ]
        fundings = []
        for instrument in self.instruments:
            is_up_to_date = self.args.all or (
                instrument.funding_rate
                and instrument.funding_rate.is_up_to_date)
            to_show = self.args.pos is None and self.args.neg is None
            if self.args.pos is not None and self.args.pos is True and instrument.funding_rate and instrument.funding_rate.rate > 0:
                to_show = True
            if self.args.neg is not None and self.args.neg is True and instrument.funding_rate and instrument.funding_rate.rate < 0:
                to_show = True
            if instrument.funding_rate and is_up_to_date and to_show:
                fundings.append([
                    instrument,
                    instrument.funding_rate.rate * 100,
                    instrument.funding_rate.predicted_rate * 100,
                    abs(instrument.funding_rate.apr) * 100,
                    abs(instrument.funding_rate.apy) * 100,
                    instrument.funding_rate.time,
                ])

        if self.args.sort:
            if self.args.sort == 'rate':
                fundings.sort(key=lambda x: abs(x[1]), reverse=True)
            if self.args.sort == 'predicted':
                fundings.sort(key=lambda x: abs(x[2]), reverse=True)
        if self.args.limit:
            fundings = fundings[:self.args.limit]
        print(tabulate(fundings, headers=header, floatfmt=".6f"), end="\n\n")
        print(tabulate([["Total", len(fundings)]]))


def main():
    parser = instruments_args_parser('Show fundings')
    parser.add_argument('-s',
                        '--sort',
                        type=str,
                        choices=['instr', 'rate', 'predicted'],
                        default='rate')
    parser.add_argument('-l', '--limit', type=int)
    parser.add_argument('--all',
                        action='store_true',
                        help='Show even if not up to date')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--pos',
                       default=None,
                       action='store_true',
                       help='Show positive fundings')
    group.add_argument('--neg',
                       default=None,
                       action='store_true',
                       help='Show negative fundings')

    args = parser.parse_args()
    show_funding = ShowFundings(args)
    show_funding.show()


if __name__ == '__main__':
    main()

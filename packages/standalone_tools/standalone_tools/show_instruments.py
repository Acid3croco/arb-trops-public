import sys

from dataclasses import dataclass

from tabulate import tabulate
from cryptofeed.defines import *

from arb_defines.defines import *
from arb_logger.logger import get_logger
from arb_defines.arb_dataclasses import Instrument
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser

LOGGER = get_logger('show_instruments', log_in_file=False)


@dataclass
class ShowInstruments:
    instruments: list[Instrument]
    details: bool = False
    no_format: bool = False

    def show(self):

        if len(self.instruments) == 0:
            LOGGER.error(f"ERROR cannot find instruments in DB")
            exit(0)

        instruments = [[
            'ID', 'Code', 'Feed code', 'Exchange code', 'Contract type',
            'expiry'
        ]]
        if self.details:
            instruments[0] += [
                'settle_currency',
                'tick_size',
                'min_order_size',
                'min_size_incr',
                'contract_size',
                'lot_size',
                'maker_fee',
                'taker_fee',
            ]
        for instr in self.instruments:
            infos = [
                instr.id,
                instr.instr_code,
                instr.feed_code,
                instr.exchange_code,
                instr.contract_type,
                instr.expiry,
            ]
            if self.details:
                infos += [
                    instr.settle_currency,
                    instr.tick_size,
                    instr.min_order_size,
                    instr.min_size_incr,
                    instr.contract_size,
                    instr.lot_size,
                    instr.maker_fee.percent_value,
                    instr.taker_fee.percent_value,
                ]
            instruments.append(infos)

        if self.no_format:
            print(tabulate(instruments[1:], tablefmt='plain'))
        else:
            print(tabulate(instruments, headers='firstrow'), end="\n\n")
            print(tabulate([["Total", len(instruments) - 1]]))


def main():
    parser = instruments_args_parser(description='Show instruments')
    parser.add_argument('-d',
                        '--details',
                        action='store_true',
                        help='Show details')
    parser.add_argument('-n',
                        '--no-format',
                        action='store_true',
                        help='Remove format')

    args = parser.parse_args()

    instruments = resolve_instruments(args)
    show_instruments = ShowInstruments(instruments, args.details,
                                       args.no_format)
    show_instruments.show()


if __name__ == '__main__':
    main()

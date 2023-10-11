import os
import sys

from arb_logger.logger import get_logger
from arb_defines.arb_dataclasses import Instrument
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser

LOGGER = get_logger('start_api', short=True)


def spawn_daemon(exchange, instruments, args, trade=False):
    instr_ids = [str(i.id) for i in instruments]
    instr_ids = ' '.join(instr_ids)

    kill_cmd = f'pkill -f "exchange_api.* {exchange}"'
    LOGGER.info(kill_cmd)
    if not args.cmd:
        os.system(kill_cmd)

    cmd = f'exchange_api --exchange {exchange} --instr-ids {instr_ids}'
    if trade:
        cmd += ' --trade'
    run_cmd = f'nohup {cmd} </dev/null >/dev/null 2>&1 &'
    LOGGER.info(run_cmd)
    if not args.cmd:
        os.system(run_cmd)


def start_api_invoke(args):
    instruments: list[Instrument] = resolve_instruments(args)
    if not instruments:
        LOGGER.error('No instruments found')

    exchanges = set([i.exchange for i in instruments])
    if args.cmd:
        LOGGER.warning(f'Will only show commands, not run')
    for exchange in exchanges:
        LOGGER.info(f'Spawn daemon exchange api for exchange {exchange}')
        instrs = [i for i in instruments if i.exchange == exchange]
        spawn_daemon(exchange, instrs, args, trade=args.trade)


def main():
    parser = instruments_args_parser()
    parser.add_argument('--trade',
                        action='store_true',
                        help='Activate trading')
    parser.add_argument('--cmd',
                        action='store_true',
                        help='Only show commands')
    args = parser.parse_args()

    if not len(sys.argv) > 1:
        parser.print_help()
        LOGGER.error(
            'Need at least one arg to prevent loading all instr exisiting in the universe'
        )
        exit(0)

    start_api_invoke(args)

import os

from argparse import ArgumentParser

from arb_logger.logger import get_logger
from exchange_api.list_api import list_api_invoke

LOGGER = get_logger('stop_api', short=True)


def stop_api_invoke(args):
    exchanges = args.exchanges
    if not exchanges:
        exchanges = ['']

    list_api_invoke(args)

    if args.cmd:
        LOGGER.warning(f'Will only show commands, not run')
    for exchange in exchanges:
        kill_cmd = f'pkill -f "exchange_api.*{exchange}"'
        LOGGER.info(kill_cmd)
        if not args.cmd:
            os.system(kill_cmd)


def main():
    parser = ArgumentParser(description='stop exchange_api')

    parser.add_argument('-e', '--exchanges', metavar='EXCHANGE', nargs='+')
    parser.add_argument('--cmd',
                        action='store_true',
                        help='Only show commands')
    args = parser.parse_args()

    stop_api_invoke(args)

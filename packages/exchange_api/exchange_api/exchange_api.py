import importlib

from arb_logger.logger import get_logger
from exchange_api.base_api import exchange_api_run
from arb_utils.args_parser import simple_args_parser
from arb_utils.resolver import resolve_instruments_from_ids

LOGGER = get_logger('exchange_api', short=True)


def exchange_api_invoke(args):
    instruments = resolve_instruments_from_ids(args.instr_ids)
    method = 'api'
    ex_class = 'Api'

    ex_low = args.exchange.lower()
    exchange_module = importlib.import_module(
        f'exchange_api.{ex_low}.{ex_low}_{method}')
    exchange_class = [
        c for c in dir(exchange_module)
        if ex_low.replace('_', '') in c.lower() and ex_class in c
    ]
    if not exchange_class:
        LOGGER.error(f'No class found for {ex_low} {method}')
        return

    exchange_class = getattr(exchange_module, exchange_class[0])
    exchange_api_run(exchange_class, instruments, args.trade)
    method_run = getattr(exchange_module, f'{ex_low}_{method}_run')
    method_run(instruments)


def main():
    parser = simple_args_parser()
    parser.add_argument('--trade',
                        action='store_true',
                        help='Activate trading')

    args = parser.parse_args()
    exchange_api_invoke(args)

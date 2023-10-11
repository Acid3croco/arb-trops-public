import importlib

from cryptofeed.defines import L2_BOOK, TRADES, FUNDING, LIQUIDATIONS, BALANCES, POSITIONS, ORDER_INFO, FILLS, CANDLES

from arb_logger.logger import get_logger
from arb_defines.defines import PRIVATE, PUBLIC
from feed_handler.exchange_base import exchange_run
from arb_utils.args_parser import simple_args_parser
from arb_utils.resolver import resolve_instruments_from_ids

PUBLIC_CHANNELS = (L2_BOOK, TRADES, FUNDING, LIQUIDATIONS, CANDLES)
PRIVATE_CHANNELS = (BALANCES, POSITIONS, ORDER_INFO, FILLS)

LOGGER = get_logger('feed_handler', short=True)


def method_map(mode):
    lemap = {
        PUBLIC: 'websocket',
        PRIVATE: 'authenticated_websocket',
    }
    return lemap.get(mode)


def class_map(mode):
    lemap = {
        PUBLIC: 'Websocket',
        PRIVATE: 'AuthenticatedWebsocket',
    }
    return lemap.get(mode)


def mode_map(channels):
    mode = list(
        set([(PUBLIC if c in PUBLIC_CHANNELS else PRIVATE) for c in channels]))
    if len(mode) != 1:
        raise ValueError('Only one mode allowed')
    return mode[0]


def feed_handler_invoke(args):
    mode = mode_map(args.channels)
    method = method_map(mode)
    exchange_class = class_map(mode)
    instruments = resolve_instruments_from_ids(args.instr_ids)

    ex_low = args.exchange.lower()
    exchange_module = importlib.import_module(
        f'feed_handler.{ex_low}.{ex_low}_{method}')
    exchange_class = [
        c for c in dir(exchange_module)
        if ex_low.replace('_', '') in c.lower() and exchange_class in c
    ]
    if not exchange_class:
        LOGGER.error(f'No class found for {ex_low} {method}')
        return

    exchange_class = getattr(exchange_module, exchange_class[0])
    params = [exchange_class, instruments]
    if args.channels:
        params += [args.channels]
    exchange_run(*params)


def main():
    parser = simple_args_parser()
    parser.add_argument('-c',
                        '--channels',
                        nargs='*',
                        required=True,
                        choices=PUBLIC_CHANNELS + PRIVATE_CHANNELS)
    # parser.add_argument('--interval', help='Candle interval (in minutes)')

    args = parser.parse_args()
    feed_handler_invoke(args)

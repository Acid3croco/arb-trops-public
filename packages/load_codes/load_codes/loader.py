import argparse

from db_handler.wrapper import DBWrapper
from load_codes.base_loader import BaseLoader
from load_codes.exchanges.okx_loader import OKXLoader
from load_codes.exchanges.woo_loader import WooLoader
from load_codes.exchanges.mexc_loader import MexcLoader
from load_codes.exchanges.bingx_loader import BingXLoader
from load_codes.exchanges.bybit_loader import BybitLoader
from load_codes.exchanges.huobi_loader import HuobiLoader
from load_codes.exchanges.bitget_loader import BitgetLoader
from load_codes.exchanges.bitmex_loader import BitmexLoader
from load_codes.exchanges.gateio_loader import GateioLoader
from load_codes.exchanges.hitbtc_loader import HitbtcLoader
from load_codes.exchanges.kraken_loader import KrakenLoader
from load_codes.exchanges.binance_loader import BinanceLoader
from load_codes.exchanges.bittrex_loader import BittrexLoader
from load_codes.exchanges.bitvavo_loader import BitvavoLoader
from load_codes.exchanges.bitfinex_loader import BitfinexLoader
from load_codes.exchanges.poloniex_loader import PoloniexLoader
from load_codes.exchanges.huobi_swap_loader import HuobiSwapLoader
from load_codes.exchanges.mexc_futures_loader import MexcFuturesLoader
from load_codes.exchanges.gateio_futures_loader import GateioFuturesLoader
from load_codes.exchanges.kraken_futures_loader import KrakenFuturesLoader
from load_codes.exchanges.binance_futures_loader import BinanceFuturesLoader
from load_codes.exchanges.binance_delivery_loader import BinanceDeliveryLoader
from load_codes.exchanges.poloniex_futures_loader import PoloniexFuturesLoader

exchanges = [
    BinanceLoader,
    BinanceFuturesLoader,
    BinanceDeliveryLoader,
    BingXLoader,
    BitfinexLoader,
    BitgetLoader,
    BitmexLoader,
    BittrexLoader,
    BitvavoLoader,
    BybitLoader,
    GateioLoader,
    GateioFuturesLoader,
    HitbtcLoader,
    HuobiLoader,
    HuobiSwapLoader,
    KrakenLoader,
    KrakenFuturesLoader,
    MexcLoader,
    MexcFuturesLoader,
    OKXLoader,
    PoloniexLoader,
    PoloniexFuturesLoader,
    WooLoader,
]


def loader(args):
    db_wrapper = DBWrapper()

    for exchange in exchanges:
        if args.exchanges is None or exchange.feed_code in args.exchanges:
            e: BaseLoader = exchange(db_wrapper, args.bases, args.quotes,
                                     args.types)
            e.load_codes()


def main():
    parser = argparse.ArgumentParser(
        description='Load exchanges, instruments, fees in DB')

    parser.add_argument('-e',
                        '--exchanges',
                        nargs='+',
                        choices=[e.feed_code for e in exchanges],
                        metavar='EXCHANGE',
                        help='exchanges to load codes')
    parser.add_argument('-b',
                        '--bases',
                        nargs='*',
                        metavar='BASE',
                        help='base to load codes')
    parser.add_argument('-q',
                        '--quotes',
                        nargs='*',
                        metavar='QOTES',
                        help='base to load codes')
    parser.add_argument('-t',
                        '--types',
                        nargs='*',
                        metavar='TYPE',
                        help='instr types to load codes')
    parser.add_argument('--clean',
                        action='store_true',
                        help='clean DB by desactivating unknown codes')

    args = parser.parse_args()
    loader(args)

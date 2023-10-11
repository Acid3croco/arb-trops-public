from cryptofeed.defines import BINANCE
from ccxt.async_support.binance import binance as binance_ccxt

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument
from exchange_api.binance.binance_fetcher import BinanceFetcher


class binance(binance_ccxt):
    ...


class BinanceApi(ExchangeAPI):
    feed_name = BINANCE
    fetcher = BinanceFetcher

    def __init__(self, instruments: list[Instrument]):
        super().__init__(instruments, binance)

    def _overload_exchange_config(self, exchange_config):
        exchange_config['options'] = {
            'defaultType': 'spot',
            'quoteOrderQty': False
        }


def binance_api_run(instruments):
    exchange = BinanceApi(instruments)
    exchange.run()

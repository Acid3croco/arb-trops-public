from datetime import datetime, timezone

from cryptofeed.defines import BINANCE_FUTURES

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument
# binance ccxt from binance spot arb api wrapper
from exchange_api.binance.binance_api import binance
from exchange_api.binance_futures.binance_futures_fetcher import BinanceFuturesFetcher


class BinanceFuturesApi(ExchangeAPI):
    feed_name = BINANCE_FUTURES
    fetcher = BinanceFuturesFetcher

    def __init__(self,
                 instruments: list[Instrument],
                 fetch_only: bool = False):
        super().__init__(instruments, binance, fetch_only=fetch_only)

    def _overload_exchange_config(self, exchange_config):
        exchange_config['options'] = {
            'defaultType': 'future',
            'quoteOrderQty': False
        }

    @staticmethod
    def _get_order_res_timestamp(res):
        return (datetime.fromtimestamp(float(res['info']['updateTime']) / 1000,
                                       tz=timezone.utc))

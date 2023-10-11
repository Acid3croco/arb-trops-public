from datetime import datetime

from cryptofeed.defines import BYBIT
from ccxt.async_support.bybit import bybit as bybit_ccxt

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument, Order
from exchange_api.bybit.bybit_fetcher import BybitFetcher


class bybit(bybit_ccxt):
    ...


class BybitApi(ExchangeAPI):
    feed_name = BYBIT
    fetcher = BybitFetcher

    def __init__(self, instruments: list[Instrument]):
        super().__init__(instruments, bybit)

    @staticmethod
    def _get_order_res_timestamp(res):
        """2022-01-23T15:00:08Z"""
        try:
            return datetime.strptime(res['info'].get('updated_time'),
                                     '%Y-%m-%dT%H:%M:%SZ')
        except TypeError:
            # if updated_time is None, use current time
            datetime.now()

    def _add_params_to_order(self, order: Order, params):
        params['position_idx'] = 0

from datetime import datetime

from cryptofeed.defines import HUOBI
from ccxt.async_support.huobi import huobi as huobi_ccxt

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument, Order
from exchange_api.huobi.huobi_fetcher import HuobiFetcher


class huobi(huobi_ccxt):
    ...


class HuobiApi(ExchangeAPI):
    feed_name = HUOBI
    fetcher = HuobiFetcher

    def __init__(self, instruments: list[Instrument]):
        super().__init__(instruments, huobi)

    def _overload_exchange_config(self, exchange_config):
        exchange_config['options'] = {
            'defaultType': 'spot',
        }

    def _order_price(self, order: Order):
        return order.price

    @staticmethod
    def _get_order_res_timestamp(res):
        return datetime.utcnow()

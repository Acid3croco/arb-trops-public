from cryptofeed.defines import BITMEX
from ccxt.async_support.bitmex import bitmex as bitmex_ccxt

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument, Order
from exchange_api.bitmex.bitmex_fetcher import BitmexFetcher


class bitmex(bitmex_ccxt):
    ...


class BitmexApi(ExchangeAPI):
    feed_name = BITMEX
    fetcher = BitmexFetcher

    def __init__(self, instruments: list[Instrument]):
        super().__init__(instruments, bitmex)

    def _order_amount(self, order: Order):
        return round(order.amount)

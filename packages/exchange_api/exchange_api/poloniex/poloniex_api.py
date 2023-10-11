from ccxt.poloniex import poloniex
from cryptofeed.defines import POLONIEX

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument


class PoloniexApi(ExchangeAPI):
    feed_name = POLONIEX

    def __init__(self, instruments: list[Instrument]):
        super().__init__(instruments, poloniex)

from ccxt.okx import okx
from cryptofeed.defines import OKX

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument


class OKXApi(ExchangeAPI):
    feed_name = OKX

    def __init__(self, instruments: list[Instrument]):
        super().__init__(instruments, okx)

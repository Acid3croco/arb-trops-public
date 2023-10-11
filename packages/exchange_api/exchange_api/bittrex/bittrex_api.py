from ccxt.bittrex import bittrex
from cryptofeed.defines import BITTREX

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument


class BittrexApi(ExchangeAPI):
    feed_name = BITTREX

    def __init__(self, instruments: list[Instrument]):
        super().__init__(instruments, bittrex)

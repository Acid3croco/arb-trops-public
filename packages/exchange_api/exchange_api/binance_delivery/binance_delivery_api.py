from cryptofeed.defines import BINANCE_DELIVERY

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument
# binance ccxt from binance spot arb api wrapper
from exchange_api.binance.binance_api import binance


class BinanceDeliveryApi(ExchangeAPI):
    feed_name = BINANCE_DELIVERY

    def __init__(self, instruments: list[Instrument]):
        super().__init__(instruments, binance)

    def _overload_exchange_config(self, exchange_config):
        exchange_config['options'] = {
            'defaultType': 'delivery',
            'quoteOrderQty': False
        }

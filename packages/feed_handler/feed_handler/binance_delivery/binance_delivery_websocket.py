from cryptofeed.exchanges import BinanceDelivery

from feed_handler.exchange_websocket import ExchangeWebsocket
from feed_handler.binance.binance_websocket import BinanceWebsocket


class BinanceDeliveryWebsocket(BinanceWebsocket):

    def __init__(self, *args):
        ExchangeWebsocket.__init__(self, BinanceDelivery, *args)

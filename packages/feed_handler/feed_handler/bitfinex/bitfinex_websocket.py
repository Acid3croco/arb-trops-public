from cryptofeed.exchanges import Bitfinex

from feed_handler.exchange_websocket import ExchangeWebsocket


class BitfinexWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(Bitfinex, *args)

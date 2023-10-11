from cryptofeed.exchanges import Poloniex

from feed_handler.exchange_websocket import ExchangeWebsocket


class PoloniexWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(Poloniex, *args)

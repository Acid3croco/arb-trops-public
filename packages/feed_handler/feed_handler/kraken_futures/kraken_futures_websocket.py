from cryptofeed.exchanges import KrakenFutures
from feed_handler.exchange_websocket import ExchangeWebsocket


class KrakenFuturesWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(KrakenFutures, *args)

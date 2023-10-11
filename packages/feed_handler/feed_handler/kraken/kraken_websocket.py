from cryptofeed.exchanges import Kraken
from feed_handler.exchange_websocket import ExchangeWebsocket


class KrakenWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(Kraken, *args)

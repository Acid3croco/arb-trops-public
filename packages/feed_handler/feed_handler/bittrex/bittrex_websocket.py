from cryptofeed.exchanges import Bittrex

from feed_handler.exchange_websocket import ExchangeWebsocket


class BittrexWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(Bittrex, *args)

from cryptofeed.exchanges import OKX

from feed_handler.exchange_websocket import ExchangeWebsocket


class OKXWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(OKX, *args)

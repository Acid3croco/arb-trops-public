from cryptofeed.exchanges import Huobi

from feed_handler.exchange_websocket import ExchangeWebsocket


class HuobiWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(Huobi, *args)

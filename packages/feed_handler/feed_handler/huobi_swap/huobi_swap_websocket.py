from cryptofeed.exchanges import HuobiSwap

from feed_handler.exchange_websocket import ExchangeWebsocket


class HuobiSwapWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(HuobiSwap, *args)

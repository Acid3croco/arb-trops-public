from cryptofeed.exchanges import Gateio

from feed_handler.exchange_websocket import ExchangeWebsocket


class GateioWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(Gateio, *args)

from cryptofeed.exchanges import GateioFutures

from feed_handler.exchange_websocket import ExchangeWebsocket


class GateioFuturesWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(GateioFutures, *args)

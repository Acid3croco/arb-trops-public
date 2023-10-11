from cryptofeed.exchanges import PoloniexFutures

from feed_handler.exchange_websocket import ExchangeWebsocket


class PoloniexFuturesWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(PoloniexFutures, *args)

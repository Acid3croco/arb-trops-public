from cryptofeed.exchanges import BinanceFutures

from feed_handler.exchange_websocket import ExchangeWebsocket
from feed_handler.binance.binance_websocket import BinanceWebsocket


class BinanceFuturesWebsocket(BinanceWebsocket):

    def __init__(self, *args):
        ExchangeWebsocket.__init__(self, BinanceFutures, *args)

    def _get_predicted_rate(self, obj, instr):
        # there is no predicted rate in Binance Futures, only next rate
        return self._get_rate(obj, instr)

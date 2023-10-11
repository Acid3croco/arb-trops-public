from cryptofeed.exchanges import Bitmex
from feed_handler.exchange_websocket import ExchangeWebsocket


class BitmexWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(Bitmex, *args)

    def _get_predicted_rate(self, obj, instr):
        rate = float(obj.rate or 0)
        return rate * instr.funding_multiplier

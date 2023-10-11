from cryptofeed.exchanges import Bybit

from feed_handler.exchange_websocket import ExchangeWebsocket


class BybitWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(Bybit, *args)

    def _get_rate(self, obj, instr):
        if obj.rate:
            return super()._get_rate(obj, instr)
        return 0

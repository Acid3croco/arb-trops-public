import ccxt.pro as ccxtpro

from feed_handler.exchange_websocket_pro import ExchangeWebsocketPro


class BitvavoWebsocket(ExchangeWebsocketPro):

    def __init__(self, *args):
        super().__init__(ccxtpro.bitvavo({
            'enableRateLimit': True,
        }), *args)

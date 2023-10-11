import ccxt.pro as ccxtpro

from feed_handler.exchange_websocket_pro import ExchangeWebsocketPro


class BTCEXWebsocket(ExchangeWebsocketPro):

    def __init__(self, *args):
        super().__init__(ccxtpro.btcex({
            'enableRateLimit': True,
        }), *args)

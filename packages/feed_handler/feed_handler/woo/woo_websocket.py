import ccxt.pro as ccxtpro

from feed_handler.exchange_websocket_pro import ExchangeWebsocketPro


class WooWebsocket(ExchangeWebsocketPro):

    def __init__(self, *args):
        exc_cred = self._get_exchange_credentials()

        config = {
            'enableRateLimit': True,
            'apiKey': exc_cred['woo']['key_id'],
            'secret': exc_cred['woo']['key_secret'],
            'uid': exc_cred['woo']['key_app'],
        }
        super().__init__(ccxtpro.woo(config), *args)

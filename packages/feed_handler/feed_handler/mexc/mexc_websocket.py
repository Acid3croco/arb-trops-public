import ccxt.pro as ccxtpro

from feed_handler.exchange_websocket_pro import ExchangeWebsocketPro


class MexcWebsocket(ExchangeWebsocketPro):

    def __init__(self, *args):
        super().__init__(
            ccxtpro.mexc3({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            }), *args)

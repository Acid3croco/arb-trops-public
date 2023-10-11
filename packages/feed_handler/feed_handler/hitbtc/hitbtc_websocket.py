from cryptofeed.exchanges import HitBTC

from feed_handler.exchange_websocket import ExchangeWebsocket


class HitbtcWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(HitBTC, *args)


def hitbtc_websocket_run(instruments):
    exchange = HitbtcWebsocket(instruments)
    exchange.websocket_run()

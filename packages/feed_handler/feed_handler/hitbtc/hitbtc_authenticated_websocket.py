from cryptofeed.exchanges import HitBTC

from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket


class HitbtcAuthenticatedWebsocket(ExchangeAuthenticatedWebsocket):

    def __init__(self, *args):
        super().__init__(HitBTC, *args)

    def _get_order_id(self, order_info):
        return order_info.raw['data'].get('clientId')


def hitbtc_authenticated_websocket_run(instruments):
    exchange = HitbtcAuthenticatedWebsocket(instruments)
    exchange.websocket_run()
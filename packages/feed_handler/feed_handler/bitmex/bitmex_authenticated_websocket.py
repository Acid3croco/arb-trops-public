from cryptofeed.exchanges import Bitmex

from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket


class BitmexAuthenticatedWebsocket(ExchangeAuthenticatedWebsocket):

    def __init__(self, *args):
        super().__init__(Bitmex, *args)

    def _get_order_id(self, order_info):
        return order_info.raw['data'].get('clientId')


def bitmex_authenticated_websocket_run(instruments):
    exchange = BitmexAuthenticatedWebsocket(instruments)
    exchange.websocket_run()
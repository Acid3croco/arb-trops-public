from cryptofeed.exchanges import KrakenFutures

from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket


class KrakenFuturesAuthenticatedWebsocket(ExchangeAuthenticatedWebsocket):

    def __init__(self, *args):
        super().__init__(KrakenFutures, *args)

    def _get_order_id(self, order_info):
        return order_info.raw['data'].get('clientId')


def bitmex_authenticated_websocket_run(instruments):
    exchange = KrakenFuturesAuthenticatedWebsocket(instruments)
    exchange.websocket_run()

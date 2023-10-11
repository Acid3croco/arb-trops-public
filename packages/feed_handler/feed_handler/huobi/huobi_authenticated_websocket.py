import sys

from cryptofeed.defines import CLOSED, FILLED, PARTIAL

from arb_defines.defines import CANCELED
from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket

# sys.path.insert(0, "/Users/acid3croco/Trading/cryptofeed")
from cryptofeed.exchanges import Huobi


class HuobiAuthenticatedWebsocket(ExchangeAuthenticatedWebsocket):

    def __init__(self, *args):
        super().__init__(Huobi, *args)

    def _get_order_id(self, order_info):
        return order_info.raw['data'].get('clientOrderId')

    @staticmethod
    def _get_order_status(order_info):
        status = ExchangeAuthenticatedWebsocket._get_order_status(order_info)
        if status == 'partial-filled':
            status = PARTIAL
        return status


def huobi_authenticated_websocket_run(instruments):
    exchange = HuobiAuthenticatedWebsocket(instruments)
    exchange.websocket_run()
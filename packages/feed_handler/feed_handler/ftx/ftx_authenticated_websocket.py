from cryptofeed.exchanges import FTX
from cryptofeed.defines import CLOSED, FILLED

from arb_defines.defines import CANCELED
from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket


class FtxAuthenticatedWebsocket(ExchangeAuthenticatedWebsocket):

    def __init__(self, *args):
        super().__init__(FTX, *args, subaccount='Arb')

    def _get_order_id(self, order_info):
        return order_info.raw['data'].get('clientId')

    @staticmethod
    def _get_price(order_info):
        price = (order_info.price or order_info.raw['data']['price']
                 or order_info.raw['data']['avgFillPrice'])
        price = float(price or 0)
        return price

    @staticmethod
    def _get_order_status(order_info):
        status = ExchangeAuthenticatedWebsocket._get_order_status(order_info)
        if status == CLOSED and order_info.amount == 0 and order_info.remaining == 0:
            status = CANCELED
        elif status == CLOSED and order_info.remaining == 0:
            status = FILLED
        return status


def ftx_authenticated_websocket_run(instruments):
    exchange = FtxAuthenticatedWebsocket(instruments)
    exchange.websocket_run()
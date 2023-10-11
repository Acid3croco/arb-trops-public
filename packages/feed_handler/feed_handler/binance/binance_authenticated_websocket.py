from cryptofeed.defines import BUY
from cryptofeed.exchanges import Binance

from arb_defines.defines import TRADE
from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket


class BinanceAuthenticatedWebsocket(ExchangeAuthenticatedWebsocket):

    def __init__(self, *args):
        super().__init__(Binance, *args)

    def _order_info_cb(self, order_info, receipt_timestamp):
        if order_info.status == TRADE:
            return self._fills_cb(order_info, receipt_timestamp)

        return super()._order_info_cb(order_info, receipt_timestamp)

    def _get_order_id(self, order_info):
        return order_info.raw['o'].get('c')

    @staticmethod
    def _get_total_filled(order_info):
        filled = order_info.amount - order_info.remaining
        return (abs(filled) if order_info.side == BUY else -abs(filled))

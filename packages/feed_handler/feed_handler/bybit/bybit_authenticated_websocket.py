import ccxt.pro as ccxtpro

from cryptofeed.defines import BYBIT

from exchange_api.bybit.bybit_fetcher import BybitFetcher
from feed_handler.exchange_authenticated_websocket_pro import ExchangeAuthenticatedWebsocketPro


class BybitAuthenticatedWebsocket(ExchangeAuthenticatedWebsocketPro):
    fetcher = BybitFetcher
    feed_name = BYBIT

    def __init__(self, *args):
        super().__init__(ccxtpro.bybit({
            'enableRateLimit': True,
        }), *args)

    def _get_order_id(self, order_info):
        return order_info.get('clientOrderId', {}).get('order_link_id')


# from cryptofeed.defines import SELL
# from cryptofeed.exchanges import Bybit

# from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket

# class BybitAuthenticatedWebsocket(ExchangeAuthenticatedWebsocket):

#     def __init__(self, *args):
#         super().__init__(Bybit, *args)

#     def _get_order_id(self, order_info):
#         return order_info.raw.get('order_link_id')

#     @staticmethod
#     def _get_qty(order_info):
#         qty = float(order_info.amount or 0)
#         return -abs(qty) if order_info.side == SELL else qty

#     @staticmethod
#     def _get_total_filled(order_info):
#         qty = float(order_info.amount or 0)
#         filled = qty - float(order_info.remaining or 0)
#         return -abs(filled) if order_info.side == SELL else filled

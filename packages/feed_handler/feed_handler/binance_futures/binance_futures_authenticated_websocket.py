from cryptofeed.exchanges import BinanceFutures
from cryptofeed.defines import SELL, PARTIAL, FILLED

from arb_defines.defines import TRADE
from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket


class BinanceFuturesAuthenticatedWebsocket(ExchangeAuthenticatedWebsocket):

    def __init__(self, *args):
        super().__init__(BinanceFutures, *args)

    async def on_order_info_cb(self, order_info, receipt_timestamp):
        self.logger.info(order_info.raw)
        if order_info.status.lower() == TRADE:
            await self.on_fills_cb(order_info, receipt_timestamp)

        await super().on_order_info_cb(order_info, receipt_timestamp)

    def _get_order_id(self, order_info):
        return order_info.raw['o'].get('c')

    @staticmethod
    def _get_exchange_order_id(trade_info):
        return trade_info.id

    @staticmethod
    def _get_order_status(order_info):
        status = ExchangeAuthenticatedWebsocket._get_order_status(order_info)
        if status == TRADE and order_info.remaining > 0:
            status = PARTIAL
        elif status == TRADE and order_info.remaining == 0:
            status = FILLED
        return status

    @staticmethod
    def _get_trade_qty(trade_info):
        return float(trade_info.raw['o']['l'] or 0)

    @staticmethod
    def _get_trade_type(trade_info):
        return trade_info.type.lower()

    @staticmethod
    def _get_qty(order_info):
        """BINANCE has original qty as amount"""
        qty = float(order_info.amount or 0)
        return -abs(qty) if order_info.side == SELL else qty

    @staticmethod
    def _get_fee(trade_info):
        return float(trade_info.raw['o'].get('n') or 0)

    @staticmethod
    def _get_price(order_info):
        price = float(order_info.raw['o'].get('ap') or 0)
        if price == 0:
            price = float(order_info.raw['o'].get('p') or 0)
        return price

    @staticmethod
    def _get_total_filled(order_info):
        """amount is original qty, remaining is remaining qty"""
        # filled = order_info.amount - order_info.remaining
        filled = float(order_info.raw['o']['z'] or 0)
        return -abs(filled) if order_info.side == SELL else filled

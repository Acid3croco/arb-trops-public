from cryptofeed.defines import BUY
from cryptofeed.exchanges import BinanceDelivery

from arb_defines.defines import TRADE
from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket


class BinanceDeliveryAuthenticatedWebsocket(ExchangeAuthenticatedWebsocket):

    def __init__(self, *args):
        super().__init__(BinanceDelivery, *args)

    async def _order_info_cb(self, order_info, receipt_timestamp):
        """
        exchange: BINANCE_FUTURES
        symbol: ALGO-USDT-PERP
        id: 4042199290
        side: sell
        status: TRADE
        type: market
        price: 1.86480
        amount: 2.7
        remaining: 0.0
        timestamp: 1637515936.05
        """

        # * when BINANCE_FUTURES FILLS -> status = TRADE (does not go in fills)

        self.logger.info(f'ORDER_INFO - {order_info}')
        if order_info.status.lower() == TRADE:
            return self._fills_cb(order_info, receipt_timestamp)

        return super()._order_info_cb(order_info, receipt_timestamp)

    def _get_order_id(self, order_info):
        return order_info.raw['o'].get('c')

    @staticmethod
    def _get_total_filled(order_info):
        filled = order_info.amount - order_info.remaining
        return (abs(filled) if order_info.side == BUY else -abs(filled))

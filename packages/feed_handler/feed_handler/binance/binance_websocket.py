from cryptofeed.exchanges import Binance

from feed_handler.exchange_websocket import ExchangeWebsocket


class BinanceWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        super().__init__(Binance, *args)

    @staticmethod
    def _get_trade_count(trade):
        """
        trade.raw = {
            'e': 'aggTrade',
            'E': 1651932405134,
            'a': 1201649244,
            's': 'BTCUSDT',
            'p': '35894.90',
            'q': '1.001',
            'f': 2195639079,  # first trade id
            'l': 2195639082,  # last trade id
            'T': 1651932404975,
            'm': True
        }
        """
        first_id = trade.raw.get('f')
        last_id = trade.raw.get('l')
        if first_id and last_id:
            return last_id - first_id + 1
        return 1

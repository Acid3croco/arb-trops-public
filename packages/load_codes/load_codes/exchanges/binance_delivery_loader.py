import ccxt

from cryptofeed.defines import BINANCE_DELIVERY

from load_codes.base_loader import BaseLoader


class BinanceDeliveryLoader(BaseLoader):
    feed_code = BINANCE_DELIVERY

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        conf = {'options': {'defaultType': 'delivery'}}
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.binance(conf),
            self.feed_code,
        )

    def get_tick_size(self, market):
        quote_precision = float(market['precision']['price'] or 1)
        return 10**(-quote_precision)

    def get_min_size_incr(self, market):
        size_precision = float(market['precision']['amount'] or 1) - 1
        return 10**(-size_precision)

    def skip_instr(self, market):
        keep = (market['type'] in ['future', 'swap']
                and market['inverse'] is True)
        return not keep

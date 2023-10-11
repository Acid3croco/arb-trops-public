from math import ceil, log10

import ccxt

from load_codes.base_loader import BaseLoader


class BitvavoLoader(BaseLoader):
    is_pro = True
    feed_code = 'BITVAVO'

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.bitvavo(),
            self.feed_code,
        )

    def get_tick_size(self, market):
        # https://docs.bitvavo.com/#tag/General/paths/~1markets/get -> PricePrecision
        res = self.exchange.public_get_ticker_price(
            params={'market': market['id']})
        curr_price = float(res['price'])
        quote_precision = float(market['precision']['price'])
        tick = curr_price * 10**(-quote_precision)
        if tick > 1:
            tick - quote_precision
        tick_size = 10**(ceil(log10(tick)))
        return tick_size

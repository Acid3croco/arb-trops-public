import ccxt

from cryptofeed.defines import BITFINEX

from load_codes.base_loader import BaseLoader


class BitfinexLoader(BaseLoader):
    feed_code = BITFINEX

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.bitfinex2(),
            self.feed_code,
        )

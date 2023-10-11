import ccxt

from cryptofeed.defines import POLONIEX

from load_codes.base_loader import BaseLoader


class PoloniexLoader(BaseLoader):
    feed_code = POLONIEX

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.poloniex(),
            self.feed_code,
        )

import ccxt

from load_codes.base_loader import BaseLoader


class BingXLoader(BaseLoader):
    feed_code = 'BINGX'

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.bingx(),
            self.feed_code,
        )

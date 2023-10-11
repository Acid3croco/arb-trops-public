import ccxt

from cryptofeed.defines import KRAKEN

from load_codes.base_loader import BaseLoader


class KrakenLoader(BaseLoader):
    feed_code = KRAKEN

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.kraken(),
            self.feed_code,
        )

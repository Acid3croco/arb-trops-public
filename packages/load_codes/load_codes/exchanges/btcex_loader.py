import ccxt

from load_codes.base_loader import BaseLoader


class BTCEXLoader(BaseLoader):
    is_pro = True
    feed_code = 'BTCEX'

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.btcex(),
            self.feed_code,
        )

import ccxt

from load_codes.base_loader import BaseLoader


class WooLoader(BaseLoader):
    is_pro = True
    feed_code = ccxt.woo().id.upper()

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.woo(),
            self.feed_code,
        )

    def normalize_instr_status(self, market):
        # TODO: check if this is correct
        # seems like if the market is active it is in the list else it is not
        return 'active'

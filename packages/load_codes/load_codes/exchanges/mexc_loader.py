import ccxt

from load_codes.base_loader import BaseLoader


class MexcLoader(BaseLoader):
    is_pro = True
    feed_code = 'MEXC'

    # remove the 3 from the feed code to match pro + prevent multiple versions
    # feed_code = ccxt.mexc3().id.upper().replace('3', '')

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.mexc3(),
            self.feed_code,
        )

    def skip_instr(self, market):
        return market['spot'] is not True

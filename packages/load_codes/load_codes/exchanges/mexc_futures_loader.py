import ccxt

from load_codes.base_loader import BaseLoader


class MexcFuturesLoader(BaseLoader):
    is_pro = True
    feed_code = 'MEXC_FUTURES'

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.mexc3({'options': {
                'defaultType': 'future'
            }}),
            self.feed_code,
        )

    def skip_instr(self, market):
        return market['swap'] is not True

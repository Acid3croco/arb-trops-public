import ccxt

from cryptofeed.defines import HUOBI

from load_codes.base_loader import BaseLoader


class HuobiLoader(BaseLoader):
    feed_code = HUOBI

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.huobi(),
            self.feed_code,
        )

    def skip_instr(self, market):
        if market['type'] != 'spot':
            return True
        return super().skip_instr(market)

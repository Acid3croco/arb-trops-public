import ccxt

from cryptofeed.defines import BYBIT, OPTION

from load_codes.base_loader import BaseLoader


class BybitLoader(BaseLoader):
    feed_code = BYBIT

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.bybit(),
            self.feed_code,
        )

    def skip_instr(self, market):
        if market['type'] == OPTION:
            self.logger.info(f"Skip option {market['symbol']}")
            return True
        return super().skip_instr(market)

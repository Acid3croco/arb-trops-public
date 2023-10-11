import ccxt

from cryptofeed.defines import HUOBI_SWAP

from load_codes.base_loader import BaseLoader


class HuobiSwapLoader(BaseLoader):
    feed_code = HUOBI_SWAP

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        config = {'options': {'defaultType': 'swap'}}
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.huobi(config),
            self.feed_code,
        )

    def skip_instr(self, market):
        if market['type'] != 'swap':
            return True
        return super().skip_instr(market)

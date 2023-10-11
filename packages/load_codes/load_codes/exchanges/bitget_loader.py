import ccxt

from cryptofeed.defines import FUTURES, PERPETUAL, SPOT, OPTION, MAKER, TAKER

from arb_defines.defines import *
from load_codes.base_loader import BaseLoader


class BitgetLoader(BaseLoader):
    is_pro = True
    feed_code = 'BITGET'

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.bitget(),
            self.feed_code,
        )

    def skip_instr(self, market):
        return market.get('settleId') == 'USDC'

    def normalize_instr_status(self, market):
        if market['type'] == 'swap':
            return 'active'
        return super().normalize_instr_status(market)

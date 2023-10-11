import re

from datetime import datetime

import ccxt

from cryptofeed.defines import HITBTC

from load_codes.base_loader import BaseLoader


class HitbtcLoader(BaseLoader):
    feed_code = HITBTC

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.hitbtc3(),
            self.feed_code,
        )

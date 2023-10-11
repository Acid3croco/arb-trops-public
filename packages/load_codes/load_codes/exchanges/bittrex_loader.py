import ccxt

from cryptofeed.defines import BITTREX

from arb_defines.defines import BULL, BEAR
from load_codes.base_loader import BaseLoader


class BittrexLoader(BaseLoader):
    feed_code = BITTREX

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.bittrex(),
            self.feed_code,
        )

    def get_base(self, market, contract_type):
        base: str = super().get_base(market, contract_type)
        if base.endswith(contract_type.upper()):
            base = base.replace(contract_type.upper(), '')
            if not base:
                base = 'BTC'
        return base

    def normalize_contract_type(self, market, instr_type):
        contract_type = super().normalize_contract_type(market, instr_type)
        if 'BULL' in market.get('base'):
            contract_type = BULL
        if 'BEAR' in market.get('base'):
            contract_type = BEAR

        return contract_type

    def get_tick_size(self, market):
        quote_precision = float(market['precision']['price'] or 1)
        return 10**(-quote_precision)

    def get_min_size_incr(self, market):
        size_precision = float(market['precision']['amount'] or 1) - 1
        return 10**(-size_precision)

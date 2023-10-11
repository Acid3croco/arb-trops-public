from datetime import datetime

import ccxt

from cryptofeed.defines import FTX, MAKER

from arb_defines.defines import BEAR, BULL, HALF, HEDGE, MOVE
from load_codes.base_loader import BaseLoader


class FtxLoader(BaseLoader):
    feed_code = FTX

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.ftx(),
            self.feed_code,
        )

    def init_exchanges_specials_values(self):
        self.funding_multiplier = 8

    def get_base(self, market, contract_type):
        base: str = super().get_base(market, contract_type)
        if base.endswith(contract_type.upper()) or '-MOVE' in base:
            base = base.replace(contract_type.upper(), '')
            base = base.replace('-', '')
            if contract_type == MOVE:
                base = base.replace('WK', '')
            if not base:
                base = 'BTC'
        return base

    def get_fee_id(self, insturment, fee_type, percent_value, fixed_value=0):
        percent_value = 0.0 if fee_type == MAKER else 0.065 / 100

        return super().get_fee_id(insturment, fee_type, percent_value,
                                  fixed_value)

    def normalize_contract_type(self, market, instr_type):
        contract_type = super().normalize_contract_type(market, instr_type)
        if 'MOVE' in market.get('base'):
            contract_type = MOVE
        if 'BULL' in market.get('base'):
            contract_type = BULL
        if 'BEAR' in market.get('base'):
            contract_type = BEAR
        if 'HEDGE' in market.get('base'):
            contract_type = HEDGE
        if 'HALF' in market.get('base'):
            contract_type = HALF

        return contract_type

    def get_expi_date(self, market):
        if market['expiry'] is not None:
            """2022-03-25T03:00:00.000Z"""
            expi_date = datetime.strptime(market['expiryDatetime'],
                                          "%Y-%m-%dT%H:%M:%S.%fZ")
            return expi_date

        return None

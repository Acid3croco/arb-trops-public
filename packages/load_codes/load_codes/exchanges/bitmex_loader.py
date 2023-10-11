import ccxt

from datetime import datetime

from cryptofeed.defines import BITMEX, FUTURES, PERPETUAL, SPOT

from arb_defines.defines import *
from load_codes.base_loader import BaseLoader


class BitmexLoader(BaseLoader):
    feed_code = BITMEX

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.bitmex(),
            self.feed_code,
        )

    def skip_instr(self, market):
        if market['id'].startswith('.'):
            return True
        # temporary skip, we may want to follow indexes in the future
        # in this case we would have to custom build_feed_code() bcs cryptofeed cant handle index type
        if market['type'] == 'index':
            return True

    def normalize_contract_type(self, market, instr_type):
        if instr_type == SPOT:
            return LINEAR

        contract_type = LINEAR
        if market['info']['isInverse'] is True:
            contract_type = INVERSE
        elif market['info']['isQuanto'] is True:
            contract_type = QUANTO

        return contract_type

    def get_expi_date(self, market):
        if market['info']['expiry']:
            """2022-03-25T12:00:00.000Z"""
            expi_date = datetime.strptime(market['info']['expiry'],
                                          '%Y-%m-%dT%H:%M:%S.%fZ')
            return expi_date
        return None

    def get_lot_size(self, market):
        try:
            return float(market['info']['lotSize'])
        except (KeyError, ValueError, TypeError):
            return super().get_lot_size(market)

    def get_contract_size(self, market):
        try:
            contract_mult = float(
                market['info'].get('underlyingToPositionMultiplier', 1) or 1)
            return 1 / contract_mult
        except (KeyError, ValueError, TypeError):
            return super().get_contract_size(market)

    def get_min_size_incr(self, market):
        return self.get_min_order_size(market)

    def get_min_order_size(self, market):
        try:
            lot_size = float(market['info']['lotSize'])
            contract_value = (1 / float(
                market['info'].get('underlyingToPositionMultiplier', 1) or 1))
            return lot_size * contract_value
        except (KeyError, ValueError, TypeError):
            return super().get_min_order_size(market)

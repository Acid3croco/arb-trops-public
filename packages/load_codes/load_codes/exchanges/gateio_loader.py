import ccxt

from cryptofeed.defines import GATEIO

from load_codes.base_loader import BaseLoader


class GateioLoader(BaseLoader):
    feed_code = GATEIO

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.gateio(),
            self.feed_code,
        )

    def normalize_instr_status(self, market):
        res = market['info'].get('in_delisting', False)
        return 'inactive' if res else super().normalize_instr_status(market)

    def skip_instr(self, market):
        # derivatives are handled by gateio_futures_loader
        # because cryptofeed discriminates between spot and derivatives
        keep = market['type'] == 'spot'
        return not keep

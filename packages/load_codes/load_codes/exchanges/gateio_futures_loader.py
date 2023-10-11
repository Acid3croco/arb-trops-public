import ccxt

from cryptofeed.defines import GATEIO_FUTURES

from load_codes.base_loader import BaseLoader


class GateioFuturesLoader(BaseLoader):
    feed_code = GATEIO_FUTURES

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        conf = {'options': {'defaultType': 'future'}}
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.gateio(conf),
            self.feed_code,
        )

    def normalize_instr_status(self, market):
        res = market['info'].get('in_delisting', False)
        return 'inactive' if res else super().normalize_instr_status(market)

    def skip_instr(self, market):
        # spot markets are handled by gateio_loader
        # because cryptofeed discriminates between spot and derivatives
        skip = market['type'] == 'spot'
        return skip

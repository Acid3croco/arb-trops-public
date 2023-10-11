import ccxt

from cryptofeed.defines import KRAKEN_FUTURES, MAKER

from load_codes.base_loader import BaseLoader


class KrakenFuturesLoader(BaseLoader):
    feed_code = KRAKEN_FUTURES

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.krakenfutures(),
            self.feed_code,
        )

    def skip_instr(self, market):
        if market['type'] == 'index':
            return True
        return super().skip_instr(market)

    def normalize_instr_status(self, market):
        tradeable = market['info'].get('tradeable', False)
        return 'active' if tradeable else 'inactive'

    def get_fee_id(self, instrument, fee_type, percent_value, fixed_value=0):
        percent_value = 0.0002 if fee_type == MAKER else 0.0005
        return super().get_fee_id(instrument, fee_type, percent_value,
                                  fixed_value)

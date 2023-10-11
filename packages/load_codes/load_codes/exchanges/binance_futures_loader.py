import ccxt

from cryptofeed.defines import BINANCE_FUTURES, PERPETUAL, MAKER

from load_codes.base_loader import BaseLoader


class BinanceFuturesLoader(BaseLoader):
    feed_code = BINANCE_FUTURES

    def __init__(self, db_wrapper, bases, quotes, instr_types):
        conf = {'options': {'defaultType': 'future'}}
        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            ccxt.binance(conf),
            self.feed_code,
        )

    def get_fee_id(self, instrument, fee_type, percent_value, fixed_value=0):
        if instrument['quote'] == 'BUSD' and instrument[
                'instr_type'] == PERPETUAL:
            if fee_type == MAKER:
                percent_value = 0.00012
            else:
                percent_value = 0.0003
        return super().get_fee_id(instrument, fee_type, percent_value,
                                  fixed_value)

    def get_tick_size(self, market):
        quote_precision = float(market['precision']['price'] or 1)
        return 10**(-quote_precision)

    def get_min_size_incr(self, market):
        size_precision = float(market['precision']['amount'] or 1) - 1
        return 10**(-size_precision)

    def skip_instr(self, market):
        keep = (market['type'] in ['future', 'swap']
                and market['linear'] is True)
        return not keep

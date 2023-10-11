import traceback

from datetime import datetime, timezone

import ccxt

from cryptofeed.symbols import Symbol
from cryptofeed.defines import FUTURES, PERPETUAL, SPOT, OPTION, MAKER, TAKER

from arb_defines.defines import *
from arb_logger.logger import get_logger
from db_handler.wrapper import DBWrapper


class BaseLoader:
    # is_pro to know if we need to use ccxtpro or cryptofeed
    is_pro = False

    def __init__(
        self,
        db_wrapper,
        bases,
        quotes,
        instr_types,
        exchange,
        cryptofeed_name,
    ):
        self.logger = get_logger(self.__class__.__name__, short=True)
        self.db_wrapper: DBWrapper = db_wrapper
        self.bases = bases
        self.quotes = quotes
        self.instr_types = instr_types
        self.exchange: ccxt.Exchange = exchange
        self.cryptofeed_name: str = cryptofeed_name
        self.fee_ids = {}

        self.init_exchanges_specials_values()

        self.exchange_db, _ = self.db_wrapper.get_or_create_exchange(
            self.exchange.name, self.cryptofeed_name)

    def init_exchanges_specials_values(self):
        self.funding_multiplier = 1

    def build_feed_code_pro(self, instrument):
        return instrument.get('exchange_code')

    def build_feed_code(self, instrument):
        if self.is_pro:
            return self.build_feed_code_pro(instrument)

        # else its from cryptofeed and we need to build the feed code
        symbol = Symbol(
            instrument['base'],
            instrument['quote'],
            instrument['instr_type'],
            expiry_date=instrument.get('expiry'),
            strike_price=instrument.get('strike_price'),
            option_type=instrument.get('option_type'),
        )
        return symbol.normalized

    def get_fee_id(self, insturment, fee_type, percent_value, fixed_value=0):
        fee = float(percent_value or 0)
        exchange_id = self.exchange_db.id

        if self.fee_ids.get(exchange_id) and self.fee_ids.get(exchange_id).get(
                fee):
            return self.fee_ids.get(exchange_id).get((fee, fee_type))
        else:
            fee_db, _ = self.db_wrapper.get_or_create_fee(
                exchange_id, fee_type, fee)
            self.fee_ids[exchange_id] = {(fee, fee_type): fee_db.id}
            return fee_db.id

    def normalize_instr_type(self, market, expi_date):
        if market['type'] in ['futures', 'future', 'swap', 'delivery']:
            if expi_date is not None:
                return FUTURES
            return PERPETUAL
        return market['type']

    def normalize_contract_type(self, market, instr_type):
        if instr_type == SPOT:
            return LINEAR

        contract_type = LINEAR
        if (market.get('is_inverse') or market.get('inverse')
                or not market.get('linear')):
            contract_type = INVERSE

        return contract_type

    def normalize_instr_status(self, market):
        return 'active' if market['active'] else 'inactive'

    def get_base(self, market, contract_type):
        return market['base']

    def get_expi_date(self, market):
        expiry = market.get('expiry')

        if expiry is not None:
            return datetime.fromtimestamp(float(market['expiry']) / 1000,
                                          tz=timezone.utc)
        return None

    def get_settle_currency(self, market):
        return market.get('settleId')

    def get_expi_code(self, instrument):
        symbol = Symbol(
            instrument['base'],
            instrument['quote'],
            instrument['instr_type'],
            expiry_date=instrument.get('expiry'),
            strike_price=instrument.get('strike_price'),
            option_type=instrument.get('option_type'),
        )
        return symbol.expiry_date

    def get_tick_size(self, market):
        return float(market['precision']['price'])

    def get_min_order_size(self, market):
        return float(market['limits']['amount']['min'] or 1)

    def get_min_size_incr(self, market):
        return float(market['precision']['amount'])

    def get_contract_size(self, market):
        return float(market.get('contractSize', 1) or 1)

    def get_lot_size(self, market):
        return 1

    def get_quote(self, market):
        return market['quote']

    def format_instr(self, market):
        if self.quotes and market['quote'] not in self.quotes:
            return

        expi_date = self.get_expi_date(market)
        instr_type = self.normalize_instr_type(market, expi_date)
        contract_type = self.normalize_contract_type(market, instr_type)
        base = self.get_base(market, contract_type)

        if self.bases and base not in self.bases:
            return
        if self.instr_types and instr_type not in self.instr_types:
            return
        if instr_type == OPTION:
            return

        instr_code = f'{self.cryptofeed_name}:{base}:{market["quote"]}:{instr_type}:{contract_type}'
        instrument = {
            'exchange_id': self.exchange_db.id,
            'instr_code': instr_code,
            'symbol': market['symbol'],
            'base': base,
            'quote': self.get_quote(market),
            'instr_type': instr_type,
            'contract_type': contract_type,
            'tick_size': self.get_tick_size(market),
            'min_order_size': self.get_min_order_size(market),
            'min_size_incr': self.get_min_size_incr(market),
            'contract_size': self.get_contract_size(market),
            'lot_size': self.get_lot_size(market),
            'funding_multiplier': self.funding_multiplier,
            'expiry': expi_date,
            'settle_currency': self.get_settle_currency(market),
            'instr_status': self.normalize_instr_status(market),
            'exchange_code': market['symbol'],
        }
        instrument['feed_code'] = self.build_feed_code(instrument)
        instrument['maker_fee_id'] = self.get_fee_id(instrument, MAKER,
                                                     market['maker'])
        instrument['taker_fee_id'] = self.get_fee_id(instrument, TAKER,
                                                     market['taker'])
        if expi_date:
            instrument['instr_code'] += ":" + self.get_expi_code(instrument)

        try:
            instr_id = self.db_wrapper.create_or_update_instrument(instrument)
            self.logger.info(f"{instr_id}, {instrument['instr_code']}")
        except Exception as e:
            self.logger.error(f"{instrument['instr_code']}")
            self.logger.error(f"{instrument}")
            self.logger.error(traceback.format_exc())

    def skip_instr(self, market):
        return False

    def disable_all_instruments(self):
        self.logger.info('Disabling all matching instruments prior loading')
        self.db_wrapper.disable_instruments(self.bases, self.quotes,
                                            self.instr_types,
                                            self.exchange_db.id)

    def load_markets(self):
        return self.exchange.load_markets()

    def load_codes(self):
        markets = self.load_markets()
        self.disable_all_instruments()

        for market in markets.values():
            # TODO: set all matching instr to inactive?
            # TODO: set expired instr to inactive?
            try:
                if self.skip_instr(market):
                    continue

                self.format_instr(market)
            except Exception:
                self.logger.error(traceback.format_exc())

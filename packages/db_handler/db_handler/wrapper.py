from peewee import prefetch
from cryptofeed.defines import SPOT, BINANCE

from arb_logger.logger import get_logger
from arb_defines.defines import LINEAR
from arb_defines.arb_dataclasses import Exchange, Fee, Instrument, Latency, Order, Trade, StrategyInfo
from db_handler.models import BalanceModel, ExchangeModel, InstrumentModel, OrderModel, FeeModel, PositionModel, StrategyInfoModel, TradeExecModel, TradeModel, LatencyModel, get_database


class DBWrapper:

    def __init__(self, logger=None):
        self.logger = logger or get_logger(self.__class__.__name__, short=True)
        self.database = get_database()

    def execute_sql(self, query, params=None):
        cursor = self.database.execute_sql(query, params)
        return cursor.fetchall()

    def create_exchange(self, exchange_name, feed_name):
        res = ExchangeModel.create(exchange_name=exchange_name,
                                   feed_name=feed_name)
        return Exchange.from_model(res)

    def get_exchange(self, feed_name):
        res = ExchangeModel.get(feed_name=feed_name)
        return Exchange.from_model(res)

    def get_or_create_exchange(self, exchange_name, feed_name):
        res, is_new = ExchangeModel.get_or_create(exchange_name=exchange_name,
                                                  feed_name=feed_name)
        return Exchange.from_model(res), is_new

    def get_exchanges(self, exchange_names=None):
        if exchange_names:
            if isinstance(exchange_names, str):
                exchange_names = [exchange_names]
            return [
                Exchange.from_model(a) for a in ExchangeModel.select().where(
                    ExchangeModel.feed_name << exchange_names)
            ]
        return [Exchange.from_model(a) for a in ExchangeModel.select()]

    def create_instrument(self, instrument):
        res = InstrumentModel.create(**instrument)
        return Instrument.from_model(res)

    def create_or_update_instrument(self, instrument) -> int:
        """Return instr_id"""
        instr_id: int = InstrumentModel.insert(**instrument).on_conflict(
            conflict_target=[InstrumentModel.instr_code],
            preserve=[
                InstrumentModel.exchange,
                InstrumentModel.symbol,
                InstrumentModel.base,
                InstrumentModel.quote,
                InstrumentModel.instr_type,
                InstrumentModel.contract_type,
                InstrumentModel.expiry,
                InstrumentModel.settle_currency,
                InstrumentModel.tick_size,
                InstrumentModel.min_order_size,
                InstrumentModel.min_size_incr,
                InstrumentModel.contract_size,
                InstrumentModel.lot_size,
                InstrumentModel.leverage,
                InstrumentModel.funding_multiplier,
                InstrumentModel.maker_fee,
                InstrumentModel.taker_fee,
                InstrumentModel.instr_status,
                InstrumentModel.exchange_code,
                InstrumentModel.feed_code,
            ]).execute()
        return instr_id

    def get_or_create_instrument(self, instrument: dict):
        res, is_new = InstrumentModel.get_or_create(**instrument)
        return Instrument.from_model(res), is_new

    def get_all_instruments(self) -> list[InstrumentModel]:
        return [Instrument.from_model(a) for a in InstrumentModel.select()]

    def get_instruments_with_ids(self, ids) -> list[InstrumentModel]:
        if not isinstance(ids, list):
            ids = [ids]
        ids = [int(id) for id in ids]

        return [
            Instrument.from_model(a) for a in InstrumentModel.select().where(
                InstrumentModel.id << ids, InstrumentModel.instr_status ==
                'active')
        ]

    def get_instruments(self,
                        base=None,
                        quote=None,
                        instr_type=None,
                        exchange_name=None,
                        contract_type=LINEAR,
                        instr_status='active') -> list[Instrument]:
        if base and not isinstance(base, list):
            base = [base]
        if quote and not isinstance(quote, list):
            quote = [quote]
        if instr_type and not isinstance(instr_type, list):
            instr_type = [instr_type]
        if exchange_name and not isinstance(exchange_name, list):
            exchange_name = [exchange_name]
        if exchange_name:
            exchange_name = list(
                map(lambda x: ExchangeModel.get(feed_name=x.upper()),
                    exchange_name))
        if contract_type and not isinstance(contract_type, list):
            contract_type = [contract_type]
        # << means IN for the ORM, can also use `InstrumentModel.base.in_(base)`
        where_filter = [InstrumentModel.instr_status == instr_status]
        if base:
            where_filter += InstrumentModel.base << base,
        if quote:
            where_filter += InstrumentModel.quote << quote,
        if instr_type:
            where_filter += InstrumentModel.instr_type << instr_type,
        if exchange_name:
            where_filter += InstrumentModel.exchange << exchange_name,
        if contract_type:
            where_filter += InstrumentModel.contract_type << contract_type,

        # join on exchange to add exchange data in the query
        # instead of doing it when calling exchange for each instr
        _instr_query = InstrumentModel.select(
            InstrumentModel,
            ExchangeModel).join(ExchangeModel).where(*where_filter)

        # get all fees from the table independently,
        # then match then with instrs during prefetch call
        _fee_query = FeeModel.select()

        # prefetch perform the queries and merge them,
        # it does 2 queries but remove every fee query on each instr
        # when calling maker_fee or taker_fee models from the instr
        return [
            Instrument.from_model(a)
            for a in prefetch(_instr_query, _fee_query)
        ]

    def disable_instruments(self, base, quote, instr_type,
                            exchange) -> list[Instrument]:
        if base and not isinstance(base, list):
            base = [base]
        if quote and not isinstance(quote, list):
            quote = [quote]
        if instr_type and not isinstance(instr_type, list):
            instr_type = [instr_type]
        if exchange and not isinstance(exchange, list):
            exchange = [exchange]
        # << means IN for the ORM, can also use `InstrumentModel.base.in_(base)`
        where_filter = [InstrumentModel.instr_status == 'active']
        if base:
            where_filter += InstrumentModel.base << base,
        if quote:
            where_filter += InstrumentModel.quote << quote,
        if instr_type:
            where_filter += InstrumentModel.instr_type << instr_type,
        if exchange:
            where_filter += InstrumentModel.exchange << exchange,

        return InstrumentModel.update(instr_status='inactive').where(
            *where_filter).execute()

    def get_currencies(self,
                       currencies,
                       quote='USDT',
                       instr_type=SPOT,
                       exchange_name=BINANCE,
                       contract_type=LINEAR) -> list[InstrumentModel]:
        if not isinstance(currencies, list):
            currencies = [currencies]
        if not isinstance(quote, list):
            quote = [quote]
        if not isinstance(instr_type, list):
            instr_type = [instr_type]
        if not isinstance(exchange_name, list):
            exchange_name = [exchange_name]
        if not isinstance(contract_type, list):
            contract_type = [contract_type]

        exchange_name = list(
            map(lambda x: ExchangeModel.get(feed_name=x), exchange_name))

        where_filter = [InstrumentModel.instr_status == 'active']
        if currencies:
            where_filter += InstrumentModel.base << currencies,
        if quote:
            where_filter += InstrumentModel.quote << quote,
        if instr_type:
            where_filter += InstrumentModel.instr_type << instr_type,
        if exchange_name:
            where_filter += InstrumentModel.exchange << exchange_name,
        if contract_type:
            where_filter += InstrumentModel.contract_type << contract_type,

        return [
            Instrument.from_model(a)
            for a in InstrumentModel.select().where(*where_filter)
        ]

    def get_instruments_like(self,
                             base="",
                             quote="",
                             instr_type="",
                             exchange_name="") -> list[InstrumentModel]:
        return [
            Instrument.from_model(a) for a in InstrumentModel.select().where(
                InstrumentModel.base.contains(base),
                InstrumentModel.quote.contains(quote),
                InstrumentModel.instr_type.contains(instr_type),
                InstrumentModel.contract_type == LINEAR,
            )
        ]

    def get_instruments_with_instr_code_like(
            self, instr_code_pattern) -> list[InstrumentModel]:
        return [
            Instrument.from_model(a) for a in InstrumentModel.select().where(
                InstrumentModel.instr_code.contains(instr_code_pattern))
        ]

    def get_instrument_from_id(self, id):
        res = InstrumentModel.select().where(InstrumentModel.id == id).get()
        return Instrument.from_model(res)

    def get_instrument_from_feed_code(self, feed_code, exchange_id):
        res = InstrumentModel.select().where(
            InstrumentModel.feed_code == feed_code,
            InstrumentModel.exchange == exchange_id).get()
        return Instrument.from_model(res)

    def get_fees(self):
        return [Fee.from_model(a) for a in FeeModel.select()]

    def create_fee(self, exchange_id, fee_type, percent_value, fixed_value=0):
        res = FeeModel.create(exchange_id=exchange_id,
                              fee_type=fee_type,
                              percent_value=percent_value,
                              fixed_value=fixed_value)
        return Fee.from_model(res)

    def get_or_create_fee(self,
                          exchange_id,
                          fee_type,
                          percent_value,
                          fixed_value=0):
        res, is_new = FeeModel.get_or_create(exchange_id=exchange_id,
                                             fee_type=fee_type,
                                             percent_value=percent_value,
                                             fixed_value=fixed_value)
        return Fee.from_model(res), is_new

    def create_order(self, order: dict):
        if 'instr' in order:
            del order['instr']
        if 'exchange_id' in order:
            del order['exchange_id']
        res = OrderModel.create(**order)
        return Order.from_model(res)

    def create_or_update_order(self, order: dict):
        if 'instr' in order:
            del order['instr']
        if 'exchange_id' in order:
            del order['exchange_id']

        if order.get('id') and order.get('exchange_order_id'):
            where_filter = (OrderModel.id == order.get('id')) | (
                OrderModel.exchange_order_id == order.get('exchange_order_id'))
        elif order.get('exchange_order_id'):
            where_filter = OrderModel.exchange_order_id == order.get(
                'exchange_order_id')
        else:
            where_filter = OrderModel.id == order.get('id')
        order_db = OrderModel.get_or_none(where_filter)
        if order_db is not None:
            new_order = {
                'exchange_order_id':
                order.get('exchange_order_id', order_db.exchange_order_id),
                'order_status':
                Order.latest_status(order.get('order_status'),
                                    order_db.order_status),
                'order_type':
                order.get('order_type') or order_db.order_type,
                'price':
                order.get('price') or order_db.price,
                'qty':
                order.get('qty') or order_db.qty,
                'event_type':
                order.get('event_type') or order_db.event_type,
                'event_key':
                order.get('event_key') or order_db.event_key,
                'time_open':
                order.get('time_open') or order_db.time_open,
                'time_ack_mkt':
                order.get('time_ack_mkt') or order_db.time_ack_mkt,
                'time_filled_mkt':
                order.get('time_filled_mkt') or order_db.time_filled_mkt,
                'time_cancel':
                order.get('time_cancel') or order_db.time_cancel,
                'time_canceled_mkt':
                order.get('time_canceled_mkt') or order_db.time_canceled_mkt,
                'time_rejected_mkt':
                order.get('time_rejected_mkt') or order_db.time_rejected_mkt,
                'total_filled':
                max(order.get('total_filled', 0),
                    order_db.total_filled or 0,
                    key=abs)
            }
            res = OrderModel.update(**new_order).where(where_filter).execute()

            return res
        else:
            res = OrderModel.create(**order)
            return Order.from_model(res)

    def create_trade_exec(self, trade):
        if 'instr' in trade:
            del trade['instr']
        if 'exchange_id' in trade:
            del trade['exchange_id']
        if 'trade_count' in trade:
            del trade['trade_count']
        res = TradeExecModel.create(**trade)
        return TradeExecModel.from_model(res)

    def create_trade(self, trade):
        if 'instr' in trade:
            del trade['instr']
        if 'exchange_id' in trade:
            del trade['exchange_id']
        res = TradeModel.create(**trade)
        return Trade.from_model(res)

    def bulk_create_trades(self, trades):
        TradeModel.insert_many(trades).execute()

    def create_strategy_info(self, strategy_info):
        res = StrategyInfoModel.create(**strategy_info)
        return StrategyInfo.from_model(res)

    def create_latency(self, latency):
        res = LatencyModel.create(**latency)
        return Latency.from_model(res)

    def create_or_update_position(self, position) -> int:
        """Return instr_id"""
        instr_id: int = PositionModel.insert(**position).on_conflict(
            conflict_target=[PositionModel.instr_id],
            preserve=[
                PositionModel.instr,
                PositionModel.qty,
                PositionModel.price,
            ]).execute()
        return instr_id

    def create_or_update_balance(self, balance) -> int:
        """Return exchange_id"""
        exchange_id: int = BalanceModel.insert(**balance).on_conflict(
            conflict_target=[BalanceModel.exchange, BalanceModel.currency],
            preserve=[BalanceModel.currency, BalanceModel.qty]).execute()
        return exchange_id

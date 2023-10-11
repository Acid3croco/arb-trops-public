from peewee import *
from playhouse.postgres_ext import *

#! NOT USING POOLED DB FOR NOW BECAUSE IT KEEP A CONNECTION OPEN ALL THE TIME (can't close it using db.close())
# from playhouse.pool import PooledPostgresqlDatabase
# database = PooledPostgresqlDatabase(
#     'arb_trops_db',
#     **{
#         'host': 'localhost',
#         'user': 'arb_trops',
#         'password': 'root'
#     },
#     autorollback=True,
#     max_connections=8,
#     stale_timeout=300,
# )


def get_database():
    return PostgresqlDatabase(
        'arb_trops_db',
        **{
            'host': 'localhost',
            'user': 'arb_trops',
            'password': 'root'
        },
        autorollback=True,
    )


class UnknownField(object):

    def __init__(self, *_, **__):
        pass


class BaseModel(Model):

    class Meta:
        database = get_database()

    def __del__(self):
        # explicitly close the connection
        self._meta.database.close()


class ExchangeModel(BaseModel):
    exchange_name = CharField()
    feed_name = CharField(unique=True)
    exchange_status = CharField(null=True)

    class Meta:
        table_name = 'exchanges'


class BalanceModel(BaseModel):
    exchange = ForeignKeyField(column_name='exchange_id',
                               field='id',
                               model=ExchangeModel)
    currency = CharField()
    qty = DoubleField()
    total_qty = DoubleField()

    class Meta:
        table_name = 'balances'
        indexes = ((('exchange', 'currency'), True), )


class FeeModel(BaseModel):
    exchange = ForeignKeyField(column_name='exchange_id',
                               field='id',
                               model=ExchangeModel)
    fee_type = CharField()
    percent_value = DoubleField()
    fixed_value = DoubleField()

    class Meta:
        table_name = 'fees'
        indexes = ((('exchange', 'fee_type', 'percent_value', 'fixed_value'),
                    True), )


class InstrumentModel(BaseModel):
    exchange = ForeignKeyField(column_name='exchange_id',
                               field='id',
                               model=ExchangeModel)
    instr_code = CharField(unique=True)
    symbol = CharField()
    base = CharField()
    quote = CharField()
    instr_type = CharField()
    contract_type = CharField(null=True)
    expiry = DateTimeField(null=True)
    settle_currency = CharField(null=True)
    tick_size = DoubleField()
    min_order_size = DoubleField()
    min_size_incr = DoubleField()
    contract_size = DoubleField()
    lot_size = DoubleField()
    leverage = IntegerField(constraints=[SQL("DEFAULT 1")])
    funding_multiplier = DoubleField(constraints=[SQL("DEFAULT 1")])
    maker_fee = ForeignKeyField(column_name='maker_fee_id',
                                field='id',
                                model=FeeModel,
                                null=True)
    taker_fee = ForeignKeyField(backref='fees_taker_fee_set',
                                column_name='taker_fee_id',
                                field='id',
                                model=FeeModel,
                                null=True)
    instr_status = CharField()
    exchange_code = CharField()
    feed_code = CharField()

    class Meta:
        table_name = 'instruments'
        indexes = ((('exchange', 'base', 'quote', 'instr_type', 'expiry'),
                    True), )


class LatencyModel(BaseModel):
    id = UUIDField(constraints=[SQL("DEFAULT uuid_generate_v4()")])
    time = DateTimeField()
    event_id = UUIDField()
    event_type = CharField()

    class Meta:
        table_name = 'latencies'
        primary_key = False


class OrderModel(BaseModel):
    id = CharField()
    time = DateTimeField()
    instr = ForeignKeyField(column_name='instr_id',
                            field='id',
                            model=InstrumentModel,
                            null=True)
    exchange_order_id = CharField(null=True)
    order_type = CharField(null=True)
    price = DoubleField(null=True)
    qty = DoubleField(null=True)
    order_status = CharField(null=True)
    strat_id = IntegerField(null=True)
    event_type = CharField(null=True)
    event_key = UUIDField(null=True)
    time_open = DateTimeField(null=True)
    time_ack_mkt = DateTimeField(null=True)
    time_filled_mkt = DateTimeField(null=True)
    time_cancel = DateTimeField(null=True)
    time_canceled_mkt = DateTimeField(null=True)
    time_rejected_mkt = DateTimeField(null=True)
    total_filled = DoubleField(constraints=[SQL("DEFAULT 0")], null=True)

    class Meta:
        table_name = 'orders'
        indexes = ((('instr'), False), )
        primary_key = False


class PositionModel(BaseModel):
    instr = ForeignKeyField(column_name='instr_id',
                            field='id',
                            model=InstrumentModel,
                            unique=True)
    qty = DoubleField(constraints=[SQL("DEFAULT 0")], null=True)
    price = DoubleField(constraints=[SQL("DEFAULT 0")], null=True)
    liquidation_price = DoubleField(constraints=[SQL("DEFAULT 0")], null=True)

    class Meta:
        table_name = 'positions'


class StrategyInfoModel(BaseModel):
    time = DateTimeField()
    order_id = UUIDField(null=True)
    event_key = UUIDField(null=True)
    payload = BinaryJSONField()

    class Meta:
        table_name = 'strategy_infos'
        indexes = (
            (('event_key'), False),
            (('order_id'), False),
        )
        primary_key = False


class TradeExecModel(BaseModel):
    id = CharField(index=True)
    time = DateTimeField()
    exchange_order_id = CharField()
    instr = ForeignKeyField(column_name='instr_id',
                            field='id',
                            model=InstrumentModel)
    qty = DoubleField()
    price = DoubleField()
    fee = DoubleField(null=True)
    order_type = CharField()
    is_liquidation = BooleanField(default=False)

    class Meta:
        table_name = 'trades_exec'
        indexes = ((('instr'), False), )
        primary_key = False


class TradeModel(BaseModel):
    id = CharField(index=True)
    time = DateTimeField()
    exchange_order_id = CharField()
    instr = ForeignKeyField(column_name='instr_id',
                            field='id',
                            model=InstrumentModel)
    qty = DoubleField()
    price = DoubleField()
    order_type = CharField()
    is_liquidation = BooleanField(default=False)
    trade_count = IntegerField(default=1)

    class Meta:
        table_name = 'trades'
        indexes = ((('instr'), False), )
        primary_key = False

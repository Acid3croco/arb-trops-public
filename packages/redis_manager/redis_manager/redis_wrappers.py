from typing import Optional
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from redis import Redis
from cryptofeed.defines import FUNDING, PERPETUAL

from arb_defines.defines import *
from arb_defines.status import StatusEnum
from redis_manager.redis_events import BalanceEvent, CandleEvent, ExchangeStatusEvent, FundingRateEvent, InstrStatusEvent, LiquidationEvent, OrderBookEvent, PositionEvent, RedisEvent, TradeEvent
from arb_defines.arb_dataclasses import Balance, Candle, ConnectionStatus, Exchange, ExchangeStatus, FundingRate, InstrStatus, Instrument, OrderBook, Position, Trade
from redis_manager.redis_handler import RedisHandler


@dataclass(kw_only=True)
class ObjectRedis:
    redis_handler: RedisHandler

    @property
    def redis_instance(self) -> Redis:
        return self.redis_handler.redis_instance


class StatusRedis(ObjectRedis):
    status_event: RedisEvent = None

    @property
    def is_instr(self):
        return hasattr(self, 'instr_code')

    def set_status(self,
                   status: StatusEnum | ConnectionStatus = None,
                   **kwargs):
        if status and isinstance(status, StatusEnum | str):
            status = self.status_event.payload_class(self.id, status)
        if not status:
            status = self.status_event.payload_class(self.id)

        status_api = status.api or kwargs.get('api')
        status_trades = status.trades or kwargs.get('trades')
        status_l2_book = status.l2_book or kwargs.get('l2_book')
        status_funding = status.funding or kwargs.get('funding')
        status_private = status.private or kwargs.get('private')
        status_liquidations = status.liquidations or kwargs.get('liquidations')

        pipeline = self.redis_instance.pipeline()
        if status_api:
            status.api = status_api
            pipeline.hset(self.redis_hash, STATUS_API, status_api.name)
        if status_trades:
            status.trades = status_trades
            pipeline.hset(self.redis_hash, STATUS_TRADES, status_trades.name)
        if status_l2_book:
            status.l2_book = status_l2_book
            pipeline.hset(self.redis_hash, STATUS_L2_BOOK, status_l2_book.name)
        if status_funding:
            if not self.is_instr or self.is_instr and self.instr_type == PERPETUAL:
                status.funding = status_funding
                pipeline.hset(self.redis_hash, STATUS_FUNDING,
                              status_funding.name)
        if status_private:
            status.private = status_private
            pipeline.hset(self.redis_hash, STATUS_PRIVATE, status_private.name)
        if status_liquidations:
            status.liquidations = status_liquidations
            pipeline.hset(self.redis_hash, STATUS_LIQUIDATIONS,
                          status_liquidations.name)
        pipeline.execute()

        if self.status:
            self.status += status
        else:
            self.status = status

        self.redis_handler.publish_event(self.status_event, status)

    def refresh_status(self, redis_dict):
        self.status = self.status_event.payload_class(
            self.id,
            api=redis_dict.get(STATUS_API),
            trades=redis_dict.get(STATUS_TRADES),
            l2_book=redis_dict.get(STATUS_L2_BOOK),
            funding=redis_dict.get(STATUS_FUNDING),
            private=redis_dict.get(STATUS_PRIVATE),
            liquidations=redis_dict.get(STATUS_LIQUIDATIONS))

        if self.is_instr and self.instr_type != PERPETUAL:
            self.status.funding = StatusEnum.IGNORE


@dataclass(kw_only=True)
class ExchangeRedis(Exchange, StatusRedis):
    __hash__ = Exchange.__hash__

    status_event = ExchangeStatusEvent

    status: Optional[ExchangeStatus] = None
    balances: dict[str, Balance] = field(default_factory=defaultdict)
    positions: dict[int, Position] = field(default_factory=defaultdict)

    def __str__(self) -> str:
        return f'{self.feed_name} (current status: {self.status})'

    def __post_init__(self):
        self.status = ExchangeStatus(self.id)
        self.refresh_all()

    @property
    def redis_hash(self):
        return f'{EXCHANGE}:{self.id}'

    @staticmethod
    def from_exchange(exchange: Exchange, redis_handler):
        return ExchangeRedis(**asdict(exchange), redis_handler=redis_handler)

    @staticmethod
    def balance_key(balance: Balance) -> str:
        return f'{BALANCE}:{balance.currency}'

    @staticmethod
    def position_key(position: Position) -> str:
        return f'{POSITION}:{position.instr_id}'

    def refresh_all(self):
        redis_dict = self.redis_instance.hgetall(self.redis_hash)

        self.balances = {
            b.currency: b
            for b in [
                BalanceEvent.deserialize(v) for k, v in redis_dict.items()
                if k.startswith(BALANCE)
            ]
        }
        #! positions are not maintained in exchange
        self.positions = {
            p.instr_id: p
            for p in [
                PositionEvent.deserialize(v) for k, v in redis_dict.items()
                if k.startswith(POSITION)
            ]
        }
        self.refresh_status(redis_dict)

    def get_balance(self, currency) -> Balance:
        return self.balances.get(currency)

    def get_balance_from_redis(self, currency) -> Balance:
        """
        get balance from redis, dont use unless you know what you are doing
        """
        balance_key = self.balance_key(currency)
        balance = self.redis_instance.hget(self.redis_hash, balance_key)
        return BalanceEvent.deserialize(balance) if balance else None

    def get_position(self, instr_id) -> Position:
        """
        positions are not updated in realtime, so this method is not reliable
        """
        return self.positions.get(instr_id)

    def get_position_from_redis(self, currency) -> Position:
        """
        get position from redis, dont use unless you know what you are doing
        """
        position_key = self.position_key(currency)
        position = self.redis_instance.hget(self.redis_hash, position_key)
        return PositionEvent.deserialize(position) if position else None

    def set_balance(self, balance: Balance):
        self.balances[balance.currency] = balance
        balance_key = self.balance_key(balance)
        self.redis_handler.publish_event(BalanceEvent, balance)
        self.redis_instance.hset(self.redis_hash, balance_key,
                                 BalanceEvent.serialize(balance))

    def delete_all_redis_balances(self, excludes: list[Balance] = None):
        for balance in self.balances.values():
            if excludes is not None and balance in excludes:
                continue
            balance_key = self.balance_key(balance)
            balance.qty = 0
            balance.total_qty = 0
            self.redis_handler.publish_event(BalanceEvent, balance)
            self.redis_instance.hdel(self.redis_hash, balance_key)

    def set_position(self, position: Position):
        """
        positions are not updated in realtime, so this method is not reliable
        """
        self.positions[position.instr_id] = position
        position_key = self.position_key(position)
        self.redis_handler.publish_event(PositionEvent, position)
        self.redis_instance.hset(self.redis_hash, position_key,
                                 PositionEvent.serialize(position))

    def delete_all_redis_positions(self, excludes: list[Position] = None):
        for position in self.positions.values():
            if excludes is not None and position in excludes:
                continue
            position_key = self.position_key(position)
            position.qty = 0
            position.price = 0
            position.liquidation_price = None
            self.redis_handler.publish_event(PositionEvent, position)
            self.redis_instance.hdel(self.redis_hash, position_key)


@dataclass(kw_only=True)
class InstrumentRedis(Instrument, StatusRedis):
    __str__ = Instrument.__str__
    __hash__ = Instrument.__hash__

    status_event = InstrStatusEvent

    status: Optional[InstrStatus] = None
    timestamp: Optional[float] = None
    orderbook: Optional[OrderBook] = None
    funding_rate: Optional[FundingRate] = None
    position: Optional[Position] = None
    last_trade: Optional[Trade] = None
    last_candle: Optional[Candle] = None

    @property
    def redis_hash(self):
        return f'{INSTRUMENT}:{self.id}'

    def __post_init__(self):
        super().__post_init__()
        self.status = InstrStatus(self.id)
        self.refresh_all()

    @staticmethod
    def from_instrument(instrument: Instrument, redis_handler):
        return InstrumentRedis(**asdict(instrument),
                               redis_handler=redis_handler)

    def refresh_all(self):
        redis_dict = self.redis_instance.hgetall(self.redis_hash)
        po = redis_dict.get(POSITION)
        self.position = (PositionEvent.deserialize(po)
                         if po else Position(self.id))
        ob = redis_dict.get(ORDERBOOK)
        self.orderbook = OrderBookEvent.deserialize(ob) if ob else None
        fr = redis_dict.get(FUNDING)
        self.funding_rate = FundingRateEvent.deserialize(fr) if fr else None
        self.timestamp = redis_dict.get(TIMESTAMP)

        self.refresh_status(redis_dict)

    def get_status(self) -> InstrStatus:
        """
        get status from redis, dont use unless you know what you are doing
        """
        st = self.redis_instance.hget(self.redis_hash, STATUS)
        return InstrStatusEvent.deserialize(st) if st else None

    def set_last_trade(self,
                       trade: Trade,
                       event_type: TradeEvent | LiquidationEvent = TradeEvent):
        self.last_trade = trade
        self.redis_handler.publish_event(event_type, trade)

    def set_last_candle(self, candle: Candle, event_type=CandleEvent):
        self.last_candle = candle
        self.redis_handler.publish_event(event_type, candle)

    def set_orderbook(self, orderbook):
        self.orderbook = orderbook
        #* comment to reduce pressure on redis - need to think about this
        #* have to be able to ask a snapshot of the orderbook to the websocket?
        #* in case its needed when instantiating the instr from somewhere else
        # self.redis_instance.hset(self.redis_hash, ORDERBOOK,
        #                          OrderBookEvent.serialize(orderbook))
        self.redis_handler.publish_event(OrderBookEvent, orderbook)

    def get_orderbook(self):
        """
        get orderbook from redis, dont use unless you know what you are doing
        """
        #! Now useless since we do not store orderbook in redis anymore
        raise DeprecationWarning(
            'get_orderbook is deprecated, orderbook is not stored in redis anymore'
        )
        ob = self.redis_instance.hget(self.redis_hash, ORDERBOOK)
        return OrderBookEvent.deserialize(ob) if ob else None

    def set_position(self, position: Position):
        self.position = position
        self.redis_handler.publish_event(PositionEvent, position)
        self.redis_instance.hset(self.redis_hash, POSITION,
                                 PositionEvent.serialize(position))

    def get_position(self):
        """
        get position from redis, dont use unless you know what you are doing
        """
        po = self.redis_instance.hget(self.redis_hash, POSITION)
        return PositionEvent.deserialize(po) if po else None

    def set_funding_rate(self, funding_rate: FundingRate):
        self.funding_rate = funding_rate
        self.redis_handler.publish_event(FundingRateEvent, funding_rate)
        self.redis_instance.hset(self.redis_hash, FUNDING,
                                 FundingRateEvent.serialize(funding_rate))

    def get_funding_rate(self):
        """
        get funding rate from redis, dont use unless you know what you are doing
        """
        fr = self.redis_instance.hget(self.redis_hash, FUNDING)
        return FundingRateEvent.deserialize(fr) if fr else None

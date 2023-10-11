import uuid
import simplejson as json

from abc import ABC
from datetime import datetime
from dataclasses import asdict

from dacite import from_dict, Config as DaciteConfig

from arb_defines.defines import *
from arb_logger.logger import get_logger
from arb_defines.status import StatusEnum
from arb_defines.arb_dataclasses import Candle, ExchangeApiPayload, Latency, SentinelPayload, StrategyInfo, Order, Trade, Exchange, ExchangeStatus, Balance, Instrument, InstrStatus, OrderBook, FundingRate, Position, TriggerPayload

LOGGER = get_logger('redis_events', short=True)


def factory(data):

    def _factory_mapper(v):
        if isinstance(v, uuid.UUID):
            return str(v)
        if isinstance(v, StatusEnum):
            return v.name
        return v

    return {k: _factory_mapper(v) for (k, v) in data if v is not None}


class RedisEvent(ABC):
    dacite_config = DaciteConfig(cast=[uuid.UUID],
                                 type_hooks={datetime: datetime.fromisoformat})

    def __init__(self):
        if not hasattr(self, 'channel'):
            raise NotImplementedError('channel not defined')
        if not hasattr(self, 'payload_class'):
            raise NotImplementedError('payload_class not defined')

    def __str__(self) -> str:
        return f'{self.__class__.__name__} {self.channel}'

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def get_channels(cls) -> list[str]:
        return [cls.channel]

    @classmethod
    def deserialize(cls, payload: dict) -> object:
        if payload is None:
            return
        if isinstance(payload, str):
            payload = json.loads(payload)
        try:
            return from_dict(cls.payload_class, payload, cls.dacite_config)
        except Exception as e:
            LOGGER.error(e)
            LOGGER.error(f'{cls.payload_class} payload: {payload}')

    @staticmethod
    def serialize(payload) -> str:
        if not payload:
            return ''
        payload = asdict(payload, dict_factory=factory)
        payload = json.dumps(payload, separators=(',', ':'), default=str)
        return payload


class LatencyDBEvent(RedisEvent):
    channel = DB_ADD_LATENCY
    payload_class = Latency


class StrategyInfoDBEvent(RedisEvent):
    channel = DB_STRATEGY_INFO
    payload_class = StrategyInfo


class NoPayloadEvent:
    payload_class = None

    @staticmethod
    def serialize(payload) -> str:
        return payload


class CancelAllOrdersEvent(NoPayloadEvent, RedisEvent):
    channel = CANCEL_ALL_ORDERS


class ReduceInstrEvent:

    @staticmethod
    def serialize(payload) -> str:
        if hasattr(payload, 'instr'):
            payload.instr = None
        payload = asdict(payload, dict_factory=factory)
        payload = json.dumps(payload, separators=(',', ':'), default=str)
        return payload


class ReduceIdEvent(RedisEvent):

    @classmethod
    def deserialize(cls, payload: dict) -> object:
        if payload is None:
            return
        if isinstance(payload, str):
            payload = json.loads(payload)
        return payload

    @staticmethod
    def serialize(payload) -> str:
        if isinstance(payload, Instrument):
            payload = {'instr_id': payload.id}
        if isinstance(payload, Exchange):
            payload = {'exchange_id': payload.id}
        if not isinstance(payload, dict):
            raise ValueError(f'{payload} is not a dict, did not get reduced')
        payload = json.dumps(payload, separators=(',', ':'), default=str)
        return payload


class OrderDBEvent(ReduceInstrEvent, RedisEvent):
    channel = DB_ADD_ORDER
    payload_class = Order


class TradeDBEvent(ReduceInstrEvent, RedisEvent):
    channel = DB_ADD_TRADE
    payload_class = Trade


class ArbDataclassDriverEvent(RedisEvent):
    arb_dataclass = None

    def __init__(self,
                 objects: object | list[object] | dict[int, object]
                 | None = None):
        super().__init__()
        if not self.arb_dataclass:
            LOGGER.error(
                f'{self.__class__.__name__} arb_dataclass not defined')
            raise NotImplementedError('arb_dataclass not defined')

        if isinstance(objects, self.arb_dataclass):
            objects = [objects]
        if isinstance(objects, dict):
            objects = list(objects.values())
        if objects:
            objects = self._filter_objects(objects)
        self.objects = objects

    def get_channels(self):
        if self.objects:
            return [f'{self.channel}:{obj.id}' for obj in self.objects]
        else:
            return [self.channel]

    @staticmethod
    def _filter_objects(objects):
        return objects


# ███████╗██╗  ██╗ ██████╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗ ███████╗
# ██╔════╝╚██╗██╔╝██╔════╝██║  ██║██╔══██╗████╗  ██║██╔════╝ ██╔════╝
# █████╗   ╚███╔╝ ██║     ███████║███████║██╔██╗ ██║██║  ███╗█████╗
# ██╔══╝   ██╔██╗ ██║     ██╔══██║██╔══██║██║╚██╗██║██║   ██║██╔══╝
# ███████╗██╔╝ ██╗╚██████╗██║  ██║██║  ██║██║ ╚████║╚██████╔╝███████╗
# ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝


class ExchangeDrivenEvent(ArbDataclassDriverEvent):
    arb_dataclass = Exchange


class ExchangeStatusEvent(ExchangeDrivenEvent):
    channel = EXCHANGE_STATUS
    payload_class = ExchangeStatus


class BalanceEvent(ExchangeDrivenEvent):
    channel = BALANCE_UPDATE
    payload_class = Balance


class CancelAllOrdersExchangeEvent(ReduceIdEvent, ExchangeDrivenEvent):
    channel = CANCEL_ALL_ORDERS_ECHANGE
    payload_class = Exchange


class CancelAllOrdersInstrEvent(ReduceIdEvent, ExchangeDrivenEvent):
    channel = CANCEL_ALL_ORDERS_INSTR
    payload_class = Instrument


class CancelOrderEvent(ReduceInstrEvent, ExchangeDrivenEvent):
    channel = CANCEL_ORDER
    payload_class = Order


class OrderExchangeEvent(ReduceInstrEvent, ExchangeDrivenEvent):
    channel = ORDER_EXCHANGE
    payload_class = Order


class ExchangeApiEvent(ExchangeDrivenEvent):
    channel = EXCHANGE_API
    payload_class = ExchangeApiPayload


# ██╗███╗   ██╗███████╗████████╗██████╗ ██╗   ██╗███╗   ███╗███████╗███╗   ██╗████████╗
# ██║████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██║   ██║████╗ ████║██╔════╝████╗  ██║╚══██╔══╝
# ██║██╔██╗ ██║███████╗   ██║   ██████╔╝██║   ██║██╔████╔██║█████╗  ██╔██╗ ██║   ██║
# ██║██║╚██╗██║╚════██║   ██║   ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║   ██║
# ██║██║ ╚████║███████║   ██║   ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║   ██║
# ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝


class InstrumentDrivenEvent(ArbDataclassDriverEvent):
    arb_dataclass = Instrument


class InstrStatusEvent(InstrumentDrivenEvent):
    channel = INSTR_STATUS
    payload_class = InstrStatus


class OrderBookEvent(InstrumentDrivenEvent):
    channel = ORDERBOOK_UPDATE
    payload_class = OrderBook


class FundingRateEvent(InstrumentDrivenEvent):
    channel = FUNDING_RATE_UPDATE
    payload_class = FundingRate

    @staticmethod
    def _filter_objects(instruments: list[Instrument]):
        return [i for i in instruments if i.has_funding]


class PositionEvent(InstrumentDrivenEvent):
    channel = POSITION_UPDATE
    payload_class = Position


class OrderEvent(ReduceInstrEvent, InstrumentDrivenEvent):
    channel = ORDER_UPDATE
    payload_class = Order


class TradeEvent(ReduceInstrEvent, InstrumentDrivenEvent):
    channel = TRADE_UPDATE
    payload_class = Trade


class CandleEvent(ReduceInstrEvent, InstrumentDrivenEvent):
    channel = CANDLE_UPDATE
    payload_class = Candle


class LiquidationEvent(ReduceInstrEvent, InstrumentDrivenEvent):
    channel = LIQUIDATION_UPDATE
    payload_class = Trade

    @staticmethod
    def _filter_objects(instruments: list[Instrument]):
        return [i for i in instruments if i.has_liquidations]


class TradeExecEvent(ReduceInstrEvent, InstrumentDrivenEvent):
    channel = TRADE_EXEC
    payload_class = Trade


# ████████╗██████╗ ██╗ ██████╗  ██████╗ ███████╗██████╗
# ╚══██╔══╝██╔══██╗██║██╔════╝ ██╔════╝ ██╔════╝██╔══██╗
#    ██║   ██████╔╝██║██║  ███╗██║  ███╗█████╗  ██████╔╝
#    ██║   ██╔══██╗██║██║   ██║██║   ██║██╔══╝  ██╔══██╗
#    ██║   ██║  ██║██║╚██████╔╝╚██████╔╝███████╗██║  ██║
#    ╚═╝   ╚═╝  ╚═╝╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝


class TriggerEvent(RedisEvent):
    channel = TRIGGER_EVENT
    payload_class = TriggerPayload

    def __init__(self, trigger_id: str = None):
        super().__init__()

        # We have to default None for trigger_id because otherwise we
        # can't match the Event in redis_manager.py since its instantiated
        # if not trigger_id:
        #     raise ValueError('Trigger name must be given')
        self.trigger_id = trigger_id

    def get_channels(self) -> list[str]:
        return [f'{self.channel}:{self.trigger_id}']


class SentinelEvent(ArbDataclassDriverEvent):
    channel = SENTINEL_EVENT
    arb_dataclass = SentinelPayload
    payload_class = SentinelPayload

    def __init__(self, objects=None, sentinel_name=None, grp_instr=False):
        super().__init__(objects)
        self.sentinel_name = sentinel_name
        self.grp_instr = grp_instr

    def get_channels(self):
        if self.objects and self.grp_instr:
            obj_ids = '_'.join(
                [str(x) for x in sorted([obj.id for obj in self.objects])])
            return [f'{self.channel}:{self.sentinel_name}:{obj_ids}']
        elif self.objects:
            return [
                f'{self.channel}:{self.sentinel_name}:{obj.id}'
                for obj in self.objects
            ]
        else:
            return [self.channel]

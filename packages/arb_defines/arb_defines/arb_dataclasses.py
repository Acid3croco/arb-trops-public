import math
import time
import uuid

from uuid import UUID
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pandas as pd

from cryptofeed.defines import *

from arb_utils import arb_round
from arb_defines.defines import *
from arb_defines.status import StatusEnum

ORDER_FINAL_STATUS = [CANCELED, REJECTED, CLOSED, FILLED]


@dataclass
class Exchange:
    id: int
    feed_name: str
    exchange_name: str
    exchange_status: str = UNDEFINED

    @staticmethod
    def from_model(model):
        return Exchange(id=model.id,
                        feed_name=model.feed_name,
                        exchange_name=model.exchange_name,
                        exchange_status=model.exchange_status)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        if isinstance(other, int):
            return self.id == other
        if isinstance(other, str):
            return self.feed_name == other

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return self.feed_name


@dataclass
class Fee:
    id: int
    exchange: Exchange
    percent_value: float = 0
    fixed_value: float = 0

    def __post_init__(self):
        if not isinstance(self.exchange, Exchange):
            self.exchange = Exchange(**self.exchange)

    @staticmethod
    def from_model(model):
        return Fee(id=model.id,
                   exchange=Exchange.from_model(model.exchange),
                   percent_value=model.percent_value,
                   fixed_value=model.fixed_value)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        if isinstance(other, int):
            return self.id == other

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return f'{self.exchange.feed_name} {self.percent_value}'


@dataclass(order=True)
class Instrument:
    id: Optional[int] = None
    exchange: Optional[Exchange] = None
    instr_code: Optional[str] = None
    symbol: Optional[str] = None
    base: Optional[str] = None
    quote: Optional[str] = None
    instr_type: Optional[str] = None
    contract_type: Optional[str] = None
    expiry: Optional[datetime] = None
    settle_currency: Optional[str] = None
    tick_size: Optional[float] = None
    min_order_size: Optional[float] = None
    min_size_incr: Optional[float] = None
    contract_size: Optional[float] = None
    lot_size: Optional[float] = None
    leverage: int = 1
    funding_multiplier: float = 1
    maker_fee: Optional[Fee] = None
    taker_fee: Optional[Fee] = None
    instr_status: Optional[str] = None
    exchange_code: Optional[str] = None
    feed_code: Optional[str] = None

    def __post_init__(self):
        if self.exchange and not isinstance(self.exchange, Exchange):
            self.exchange = Exchange(**self.exchange)
        if self.maker_fee and not isinstance(self.maker_fee, Fee):
            self.maker_fee = Fee(**self.maker_fee)
        if self.taker_fee and not isinstance(self.taker_fee, Fee):
            self.taker_fee = Fee(**self.taker_fee)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        if isinstance(other, int):
            return self.id == other
        if isinstance(other, str):
            return self.instr_code == other
        if isinstance(other, dict):
            return self.instr_code == other['id']

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return self.instr_code

    @staticmethod
    def from_model(model):
        return Instrument(id=model.id,
                          exchange=Exchange.from_model(model.exchange),
                          instr_code=model.instr_code,
                          symbol=model.symbol,
                          base=model.base,
                          quote=model.quote,
                          instr_type=model.instr_type,
                          contract_type=model.contract_type,
                          expiry=model.expiry,
                          settle_currency=model.settle_currency,
                          tick_size=model.tick_size,
                          min_order_size=model.min_order_size,
                          min_size_incr=model.min_size_incr,
                          contract_size=model.contract_size,
                          lot_size=model.lot_size,
                          leverage=model.leverage,
                          funding_multiplier=model.funding_multiplier,
                          maker_fee=Fee.from_model(model.maker_fee),
                          taker_fee=Fee.from_model(model.taker_fee),
                          instr_status=model.instr_status,
                          exchange_code=model.exchange_code,
                          feed_code=model.feed_code)

    @property
    def orders_hash(self) -> str:
        return f'{ORDERS}:{self.exchange.id}:{self.id}'

    @property
    def has_liquidations(self) -> bool:
        return self.instr_type != SPOT

    @property
    def has_funding(self) -> bool:
        return self.instr_type == PERPETUAL


@dataclass
class Order:
    id: Optional[str | UUID] = None
    time: Optional[datetime] = None
    instr: Optional[Instrument] = None
    exchange_order_id: Optional[str] = None
    order_type: Optional[str] = None
    price: Optional[float] = None
    qty: Optional[float] = None
    order_status: str = NEW
    instr_id: Optional[int] = None
    exchange_id: Optional[int] = None
    strat_id: Optional[int] = None
    event_type: Optional[str] = None
    event_key: Optional[UUID] = None
    time_open: Optional[datetime] = None
    time_ack_mkt: Optional[datetime] = None
    time_filled_mkt: Optional[datetime] = None
    time_cancel: Optional[datetime] = None
    time_canceled_mkt: Optional[datetime] = None
    time_rejected_mkt: Optional[datetime] = None
    total_filled: Optional[float] = 0

    def __hash__(self) -> int:
        return hash(self.id)

    def __post_init__(self):
        if self.time is None:
            self.time = datetime.now(tz=timezone.utc)

        if isinstance(self.time, str):
            self.time = datetime.fromisoformat(self.time)
            self.time = self.time.replace(tzinfo=timezone.utc)

        if self.price and not isinstance(self.price, float):
            self.price = float(self.price)
        if self.qty and not isinstance(self.qty, float):
            self.qty = float(self.qty)
        if (self.total_filled is not None
                and not isinstance(self.total_filled, float)):
            self.total_filled = float(self.total_filled)

        if self.instr and isinstance(self.instr, dict):
            self.instr = Instrument(**self.instr)

        if self.instr and self.instr_id is None:
            self.instr_id = self.instr.id
        if self.instr and self.exchange_id is None:
            self.exchange_id = self.instr.exchange.id

        if self.exchange_order_id and self.id is None:
            self.id = self._built_id
        elif self.id is None:
            self.id = uuid.uuid4()

    def __eq__(self, other: 'Order') -> bool:
        if not other:
            return False
        return str(self.id) == str(other.id)

    def __or__(self, other: 'Order') -> 'Order':
        """Determine the most recent valid order bewtween two orders"""
        if self != other:
            raise ValueError('Cannot compare orders with different IDs')

        if self.is_final and not other.is_final:
            return self
        if not self.is_final and other.is_final:
            return other

        if self.is_final and other.is_final:
            # for final status we use the earlier final status timesamp
            if self.time_rejected_mkt and other.time_rejected_mkt:
                return self if self.time_rejected_mkt < other.time_rejected_mkt else other
            if self.time_canceled_mkt and other.time_canceled_mkt:
                return self if self.time_canceled_mkt < other.time_canceled_mkt else other
            if self.time_filled_mkt and other.time_filled_mkt:
                return self if self.time_filled_mkt < other.time_filled_mkt else other

        if self.order_status == other.order_status and self.order_status == PARTIAL:
            # because we dont know for sure what timestamp is used for time_filled_mkt (marker or received)
            # we use the total_filled to determine which order is more up to date
            return self if self.total_filled > other.total_filled else other

        if self.order_status != other.order_status:
            last_status = self.latest_status(self, other)
            # return the last order status
            return self if self.order_status == last_status else other

        # if order status is the same, we use the earlier created order
        return self if self.time < other.time else other

    def __str__(self) -> str:
        return f'ORDER {self.order_status} {self.id} {self.instr or self.instr_id} {self.order_type} {self.qty}@{self.price} {f"({self.r_qty})" if self.instr else ""})'

    def desc(self) -> str:
        return f' {self.order_status} {self.instr or self.instr_id} {self.qty}@{self.price}'

    def detailed_str(self) -> str:
        return f'{self.__str__()} {self.r_qty} {self.size}'

    def is_same_order(self, other: 'Order') -> bool:
        return self.instr == other.instr and self.price == other.price and self.qty == other.qty and self.order_type == other.order_type

    def set_instr(self, instr: Instrument) -> None:
        self.instr = instr
        self.instr_id = instr.id
        self.exchange_id = instr.exchange.id

    @staticmethod
    def latest_status(prev, curr) -> str:
        if isinstance(prev, Order):
            prev = prev.order_status
        if isinstance(curr, Order):
            curr = curr.order_status
        prev = prev.lower()
        curr = curr.lower()
        order = [
            None, NEW, UNKNOWN, OPEN, CANCEL, PARTIAL, CANCELED,
            CANCEL_REJECTED, REJECTED, FILLED, CLOSED, EXPIRED, FAILED
        ]
        return max([prev, curr], key=lambda x: order.index(x))

    @staticmethod
    def from_model(model):
        return Order(id=model.id,
                     time=model.time,
                     instr=Instrument.from_model(model.instr),
                     exchange_order_id=model.exchange_order_id,
                     order_type=model.order_type,
                     price=model.price,
                     qty=model.qty,
                     order_status=model.order_status,
                     strat_id=model.strat_id,
                     event_type=model.event_type,
                     event_key=model.event_key,
                     time_open=model.time_open,
                     time_ack_mkt=model.time_ack_mkt,
                     time_filled_mkt=model.time_filled_mkt,
                     time_cancel=model.time_cancel,
                     time_canceled_mkt=model.time_canceled_mkt,
                     time_rejected_mkt=model.time_rejected_mkt,
                     total_filled=model.total_filled)

    @staticmethod
    def from_order(order: 'Order') -> 'Order':
        instr = order.instr
        instr.__class__ = Instrument
        order_type = LIMIT if order.order_type == MAKER else MARKET if order.order_type == MAKER else order.order_type
        return Order(qty=order.qty,
                     price=order.price,
                     order_type=order_type,
                     event_type=order.event_type,
                     strat_id=order.strat_id,
                     instr=instr)
        return order

    @property
    def is_final(self):
        return self.order_status in ORDER_FINAL_STATUS

    @property
    def is_external(self):
        return self.id == self._built_id

    @property
    def _built_id(self):
        """Generate an order id based on the exchange order id if order is external"""
        return f'{self.exchange_order_id}:{self.exchange_id}:{self.instr_id}'

    @property
    def side(self) -> str:
        if not self.qty:
            return UND

        if self.qty > 0:
            return BUY
        elif self.qty < 0:
            return SELL

        return UND

    @property
    def r_price(self) -> float:
        """Return price with tick_size adjusted"""
        if not self.instr:
            raise ValueError('Instrument not set')
        return arb_round(self.price, self.instr.tick_size)

    @property
    def amount(self) -> float:
        """Return abs(size)"""
        if not self.size:
            return 0
        return abs(self.size)

    @property
    def size(self) -> float:
        """Return number of contracts to buy from r_qty"""
        if not self.qty:
            return 0
        return self.qty / self.instr.contract_size

    @property
    def cost(self) -> float:
        """Return cost of order according to price and qty"""
        if not self.qty:
            return 0
        return self.qty * self.price

    @property
    def r_qty(self) -> float:
        """Return the max rounded quantity of the order according to min_size_incr."""
        if not self.instr:
            raise ValueError('Instrument not set')
        return arb_round(self.qty, self.instr.min_size_incr)

    @property
    def r_cost(self) -> float:
        """Return cost of order according to r_price and r_qty"""
        if not self.r_qty:
            return 0
        return self.r_qty * self.r_price


@dataclass
class Latency:
    id: Optional[UUID] = None
    time: Optional[datetime] = None
    event_id: Optional[UUID] = None
    event_type: Optional[str] = None

    @staticmethod
    def from_model(model):
        return Latency(id=model.id,
                       time=model.time,
                       event_id=model.event_id,
                       event_type=model.event_type)


@dataclass
class Trade:
    id: Optional[str | UUID] = None
    time: datetime = None
    qty: float = None
    price: float = None
    order_type: str = MARKET
    exchange_order_id: str = None
    fee: Optional[float] = None
    instr: Optional[Instrument] = None
    instr_id: Optional[int] = None
    exchange_id: Optional[int] = None
    is_liquidation: bool = False
    trade_count: int = 1

    def __post_init__(self):
        if self.time is None:
            self.time = datetime.now(tz=timezone.utc)
        elif isinstance(self.time, int | float):
            self.time = datetime.fromtimestamp(self.time, tz=timezone.utc)

        if isinstance(self.time, str):
            self.time = datetime.fromisoformat(self.time)
        self.time = self.time.replace(tzinfo=timezone.utc)

        if isinstance(self.price, str):
            self.price = float(self.price)
        if isinstance(self.qty, str):
            self.qty = float(self.qty)

        if self.order_type is None:
            self.order_type = MARKET

        if self.instr and isinstance(self.instr, dict):
            self.instr = Instrument(**self.instr)

        if self.instr and self.instr_id is None:
            self.instr_id = self.instr.id
        if self.instr and self.exchange_id is None:
            self.exchange_id = self.instr.exchange.id

        if self.exchange_order_id == 'liq':
            self.exchange_order_id = uuid.uuid4()
        if self.exchange_order_id and self.id is None:
            self.id = self._built_id
        #TODO remove this section / think about it
        elif self.id is None:
            self.id = uuid.uuid4()

    def __eq__(self, other) -> bool:
        return self.id == other.id

    def __str__(self) -> str:
        return f'TRADE {self.id} {self.instr or self.instr_id} {self.qty}@{self.price}'

    def desc(self) -> str:
        return f'{self.instr or self.instr_id} {self.qty}@{self.price}'

    @staticmethod
    def from_model(model):
        return Trade(id=model.id,
                     time=model.time,
                     exchange_order_id=model.exchange_order_id,
                     instr=Instrument.from_model(model.instr),
                     qty=model.qty,
                     price=model.price,
                     fee=model.fee,
                     order_type=model.order_type)

    # def to_list(self) -> list:
    #     return [
    #         self.id, self.time, self.qty, self.price, self.order_type,
    #         self.exchange_order_id, self.fee, self.instr, self.instr_id,
    #         self.exchange_id, self.is_liquidation
    #     ]

    @property
    def _built_id(self):
        """Generate an order id based on the exchange order id if order is external"""
        return f'{self.exchange_order_id}:{self.exchange_id}:{self.instr_id}'

    @property
    def amount(self) -> float:
        """amount paid: qty * price"""
        return self.qty * self.price

    @property
    def side(self) -> str:
        if self.qty > 0:
            return BUY
        elif self.qty < 0:
            return SELL
        else:
            return UND

    @property
    def sign(self) -> int:
        if self.qty > 0:
            return 1
        elif self.qty < 0:
            return -1
        else:
            return 0

    @property
    def notional(self) -> float:
        return self.qty * self.instr.contract_size * self.price


@dataclass
class StrategyInfo:
    payload: dict
    order_id: Optional[UUID] = None
    event_key: Optional[UUID] = None
    time: Optional[datetime] = None

    def __post_init__(self):
        if not self.order_id and not self.event_key:
            raise ValueError(
                'StrategyInfo must have either order_id or event_key')
        if self.time is None:
            self.time = datetime.now(tz=timezone.utc)

    def __str__(self) -> str:
        return str(self.order_id) if self.order_id else str(self.event_key)

    @staticmethod
    def from_model(model):
        return StrategyInfo(time=model.time,
                            order_id=model.order_id,
                            event_key=model.event_key,
                            payload=model.payload)


@dataclass
class FundingRate:
    instr_id: int
    rate: Optional[float] = 0
    predicted_rate: Optional[float] = 0
    next_funding_time: Optional[datetime] = None
    timestamp: Optional[float] = None

    def __str__(self) -> str:
        return f'{self.instr_id} {self.rate} {self.predicted_rate} {self.next_funding_time}'

    def __eq__(self, other: 'FundingRate') -> bool:
        return (self.instr_id == other.instr_id and self.rate == other.rate
                and self.predicted_rate == other.predicted_rate
                and self.next_funding_time == other.next_funding_time)

    @property
    def apr(self):
        if self.predicted_rate:
            apr = abs(self.predicted_rate) * 3 * 365
            return math.copysign(apr, self.predicted_rate)
        return 0

    @property
    def apy(self):
        if self.predicted_rate:
            apy = (1 + abs(self.predicted_rate))**(3 * 365) - 1
            return math.copysign(apy, self.predicted_rate)
        return 0

    @property
    def time(self):
        if self.timestamp:
            return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)

    @property
    def is_up_to_date(self) -> bool:
        return (self.time and self.time >
                datetime.now(tz=timezone.utc) - timedelta(hours=8, minutes=1))


@dataclass
class OrderBook:
    #? Should we add instr like for Trade?
    instr_id: int
    bids: list
    asks: list
    timestamp: Optional[float] = None

    def __eq__(self, other) -> bool:
        return self.instr_id == other.instr_id and self.bid == other.bid and self.ask == other.ask

    def bid(self, limit=0) -> tuple[float, float]:
        """
        tuple[float, float]: (bid, bidsize)
        """
        bid, bidsize = self.bids[limit]
        return bid, bidsize

    def ask(self, limit=0) -> tuple[float, float]:
        """
        tuple[float, float]: (ask, asksize)
        """
        ask, asksize = self.asks[limit]
        return ask, asksize

    def mid(self):
        return (self.bid()[0] + self.ask()[0]) / 2

    def spread(self):
        ask, _ = self.ask()
        bid, _ = self.bid()
        return ask - bid

    def spread_pct(self):
        ask, _ = self.ask()
        bid, _ = self.bid()
        return (ask - bid) * 2 / (bid + ask)


@dataclass
class AggrBook:
    """
    init using currencies: dict[str, InstrumentRedis], class will resolve OrderBook
    """
    currencies: dict[str, OrderBook] = field(default_factory=dict)
    timestamp: float = 0

    def __post_init__(self):
        self.orderbooks: dict[int, tuple[Instrument, OrderBook]] = {}
        self.taker_buys: list[tuple[Instrument, list]] = None
        self.taker_sells: list[tuple[Instrument, list]] = None
        self.maker_buys: list[tuple[Instrument, list]] = None
        self.maker_sells: list[tuple[Instrument, list]] = None

        currencies = self.currencies
        if isinstance(currencies, dict):
            currencies = currencies.values()
        self.currencies = {c.base: c.orderbook for c in currencies}

    def set_orderbooks(self, instruments: list):
        for instrument in instruments:
            if hasattr(instrument, 'orderbook') and instrument.orderbook:
                if instrument.base in self.currencies:
                    self.currencies[instrument.base] = instrument.orderbook
                else:
                    instr: Instrument = instrument
                    self.orderbooks[instrument.id] = (instr,
                                                      instrument.orderbook)

        self.compute_aggrbook()

    def taker_buy(self,
                  limit=0,
                  fees=False,
                  excl_instrs=[]) -> tuple[float, float, Instrument]:
        """
        tuple[float, float, InstrumentRedis]: (ask, asksize, instr)
        """
        if not self.taker_buys:
            return None, None, None
        instr, ob = next(
            filter(lambda x: x[0] not in excl_instrs, self.taker_buys),
            (None, None))
        if instr is None:
            return None, None, None
        fee = (1 + instr.taker_fee.percent_value) if fees else 1
        ask, asksize = ob.ask(limit)
        return ask * fee, asksize, instr

    def taker_sell(self,
                   limit=0,
                   fees=False,
                   excl_instrs=[]) -> tuple[float, float, Instrument]:
        """
        tuple[float, float, InstrumentRedis]: (bid, bidsize, instr)
        """
        if not self.taker_sells:
            return None, None, None
        instr, ob = next(
            filter(lambda x: x[0] not in excl_instrs, self.taker_sells),
            (None, None))
        if instr is None:
            return None, None, None
        fee = (1 - instr.taker_fee.percent_value) if fees else 1
        bid, bidsize = ob.bid(limit)
        return bid * fee, bidsize, instr

    def maker_buy(self,
                  limit=0,
                  fees=False,
                  excl_instrs=[]) -> tuple[float, float, Instrument]:
        """
        tuple[float, float, InstrumentRedis]: (bid, bidsize, instr)
        """
        if not self.maker_buys:
            return None, None, None
        instr, ob = next(
            filter(lambda x: x[0] not in excl_instrs, self.maker_buys),
            (None, None))
        if instr is None:
            return None, None, None
        fee = (1 + instr.maker_fee.percent_value) if fees else 1
        bid, bidsize = ob.bid(limit)
        return bid * fee, bidsize, instr

    def maker_sell(self,
                   limit=0,
                   fees=False,
                   excl_instrs=[]) -> tuple[float, float, Instrument]:
        """
        tuple[float, float, InstrumentRedis]: (ask, asksize, instr)
        """
        if not self.maker_sells:
            return None, None, None
        instr, ob = next(
            filter(lambda x: x[0] not in excl_instrs, self.maker_sells),
            (None, None))
        if instr is None:
            return None, None, None
        fee = (1 - instr.maker_fee.percent_value) if fees else 1
        ask, asksize = ob.ask(limit)
        return ask * fee, asksize, instr

    def hit_hit_spread(self, fees=True, excl_buys=[], excl_sells=[]):
        buy_side = self.taker_buy(fees=fees, excl_instrs=excl_buys)
        sell_side = self.taker_sell(fees=fees, excl_instrs=excl_sells)

        return self.__spread(buy_side, sell_side)

    def hit_liq_spread(self, fees=True, excl_buys=[], excl_sells=[]):
        buy_side = self.taker_buy(fees=fees, excl_instrs=excl_buys)
        sell_side = self.maker_sell(fees=fees, excl_instrs=excl_sells)

        return self.__spread(buy_side, sell_side)

    def liq_hit_spread(self, fees=True, excl_buys=[], excl_sells=[]):
        buy_side = self.maker_buy(fees=fees, excl_instrs=excl_buys)
        sell_side = self.taker_sell(fees=fees, excl_instrs=excl_sells)

        return self.__spread(buy_side, sell_side)

    def liq_liq_spread(self, fees=True, excl_buys=[], excl_sells=[]):
        buy_side = self.maker_buy(fees=fees, excl_instrs=excl_buys)
        sell_side = self.maker_sell(fees=fees, excl_instrs=excl_sells)

        return self.__spread(buy_side, sell_side)

    def __spread(self, buy_side, sell_side):
        _buy, _, b_instr = buy_side
        _sell, _, s_instr = sell_side
        if not _buy or not _sell:
            return None

        buy = _buy * self.get_currency_rate(b_instr)
        sell = _sell * self.get_currency_rate(s_instr)
        spread = (sell - buy) * 2 / (buy + sell)

        return spread

    def update_aggrbook_taker(self, instr: Instrument, orderbook: OrderBook):
        self.update_aggrbook(instr, orderbook, maker=False, taker=True)

    def update_aggrbook_maker(self, instr: Instrument, orderbook: OrderBook):
        self.update_aggrbook(instr, orderbook, maker=True, taker=False)

    def update_aggrbook(self,
                        instr: Instrument,
                        orderbook: OrderBook,
                        taker=True,
                        maker=True):
        if instr.base in self.currencies:
            self.currencies[instr.base] = orderbook
            return

        self.orderbooks[orderbook.instr_id] = instr, orderbook
        self.compute_aggrbook(taker=taker, maker=maker)
        self.timestamp = orderbook.timestamp

    def compute_aggrbook(self, taker=True, maker=True):
        if taker:
            self.__update_taker_buy()
            self.__update_taker_sell()
        if maker:
            self.__update_maker_buy()
            self.__update_maker_sell()

    def get_currency_rate(self, instr: Instrument):
        ob = self.currencies.get(instr.quote)
        return ob.mid() if ob else 1

    def __get_ob_up(self):
        return [(instr, ob) for instr, ob in self.orderbooks.values()
                if instr.status.l2_book == StatusEnum.UP]

    def __update_taker_buy(self):
        val = self.__get_ob_up()
        if val:
            self.taker_buys = sorted(
                val,
                key=lambda x: x[1].ask()[0] * self.get_currency_rate(x[0]) *
                (1 + x[0].taker_fee.percent_value))
        else:
            self.taker_buys = []

    def __update_taker_sell(self):
        val = self.__get_ob_up()
        if val:
            self.taker_sells = sorted(
                val,
                key=lambda x: x[1].bid()[0] * self.get_currency_rate(x[0]) *
                (1 - x[0].taker_fee.percent_value),
                reverse=True)
        else:
            self.taker_sells = []

    def __update_maker_buy(self):
        val = self.__get_ob_up()
        if val:
            self.maker_buys = sorted(
                val,
                key=lambda x: x[1].bid()[0] * self.get_currency_rate(x[0]) *
                (1 + x[0].maker_fee.percent_value))
        else:
            self.maker_buys = []

    def __update_maker_sell(self):
        val = self.__get_ob_up()
        if val:
            self.maker_sells = sorted(
                val,
                key=lambda x: x[1].ask()[0] * self.get_currency_rate(x[0]) *
                (1 - x[0].maker_fee.percent_value),
                reverse=True)
        else:
            self.maker_sells = []


@dataclass
class AggrFundingRate:
    funding_rates: defaultdict[Instrument, FundingRate] = field(
        default_factory=defaultdict(FundingRate))

    def __post_init__(self):
        self.funding_rates = {
            i: f if f else FundingRate(i.id)
            for i, f in self.funding_rates.items()
        }
        self.ordered_rates: list[Instrument, FundingRate] = []
        self.compute_aggr_funding_rate()

    def upadte_funding_rate(self,
                            instr: Instrument,
                            funding_rate: FundingRate = None):
        if not funding_rate:
            funding_rate = self.funding_rates.get(instr)
        if not funding_rate:
            return
        self.funding_rates[instr] = funding_rate
        self.compute_aggr_funding_rate()
        self.timestamp = funding_rate.timestamp

    def compute_aggr_funding_rate(self):
        frs = [(instr, fr) for instr, fr in self.funding_rates.items()
               if instr.status.funding == StatusEnum.UP
               or instr.instr_type == SPOT]
        if frs:
            self.ordered_rates = sorted(frs, key=lambda x: x[1].predicted_rate)
        else:
            self.ordered_rates = []

    def spread(
        self,
        excl_buys: list[Instrument] = [],
        excl_sells: list[Instrument] = [],
        incl_buys: list[Instrument] = [],
        incl_sells: list[Instrument] = [],
    ) -> tuple[float, Instrument, Instrument]:
        """Return best rate spread with instr_ids excluding instr_id in in excl_buys and excl_sells

        Args:
            INCLUDE HAS PRECEDENCE OVER EXCLUDE

            excl_buys (list, optional): instr_id of buy to exclude. Defaults to [].
            excl_sells (list, optional): instr_id of buy to exclude. Defaults to [].
            incl_buys (list, optional): instr_id of buy to include. Defaults to [].
            incl_sells (list, optional): instr_id of buy to include. Defaults to [].

        Returns:
            tuple[float, int, int]: spread, buy instr, sell instr
        """
        b_instr, f_buy = self.__buy_rate(excl=excl_buys, incl=incl_buys)
        s_instr, f_sell = self.__sell_rate(excl=excl_sells, incl=incl_sells)

        if not b_instr or not s_instr:
            return None, None, None

        spread = f_sell.predicted_rate - f_buy.predicted_rate

        return spread, b_instr, s_instr

    def buy_side(self, excl: list[Instrument] = []):
        return self.__buy_rate(excl=excl)

    def sell_side(self, excl: list[Instrument] = []):
        return self.__sell_rate(excl=excl)

    def __buy_rate(
            self,
            excl: list[Instrument] = [],
            incl: list[Instrument] = []) -> tuple[Instrument, FundingRate]:
        if not self.ordered_rates:
            return None, None

        if incl:
            res = next(filter(lambda x: x[0] in incl, self.ordered_rates),
                       None)
        else:
            res = next(filter(lambda x: x[0] not in excl, self.ordered_rates),
                       None)

        if res is None:
            return None, None

        instr, rate = res
        return instr, rate

    def __sell_rate(
            self,
            excl: list[Instrument] = [],
            incl: list[Instrument] = []) -> tuple[Instrument, FundingRate]:
        if not self.ordered_rates:
            return None, None

        if incl:
            res = next(
                filter(lambda x: x[0] in incl, reversed(self.ordered_rates)),
                None)
        else:
            res = next(
                filter(lambda x: x[0] not in excl,
                       reversed(self.ordered_rates)), None)

        if res is None:
            return None, None

        instr, rate = res
        return instr, rate


@dataclass
class Candle:
    time: datetime
    close: float
    open: float = None
    high: float = None
    low: float = None
    volume: float = None
    trades: int = None
    instr: Optional[Instrument] = None
    instr_id: Optional[int] = None
    exchange_id: Optional[int] = None
    end_time: Optional[datetime] = None

    def __post_init__(self):
        if isinstance(self.time, int | float):
            if self.time > 9999999999:
                self.time /= 1000
            self.time = datetime.fromtimestamp(self.time, tz=timezone.utc)
        if isinstance(self.time, pd.Timestamp):
            self.time = self.time.to_pydatetime()

        if self.instr and isinstance(self.instr, dict):
            self.instr = Instrument(**self.instr)

        if self.instr and self.instr_id is None:
            self.instr_id = self.instr.id
        if self.instr and self.exchange_id is None:
            self.exchange_id = self.instr.exchange.id

        if isinstance(self.end_time, int | float):
            if self.end_time > 9999999999:
                self.end_time /= 1000
            self.end_time = datetime.fromtimestamp(self.end_time,
                                                   tz=timezone.utc)
        if isinstance(self.end_time, pd.Timestamp):
            self.end_time = self.end_time.to_pydatetime()

    @staticmethod
    def from_ltps(ltps: list[float]) -> 'Candle':
        if ltps:
            prices = [p for _, p, _ in ltps]
            volume = sum([abs(v) for _, _, v in ltps])
            return Candle(time=ltps[0][0],
                          open=prices[0],
                          high=max(prices),
                          low=min(prices),
                          close=prices[-1],
                          volume=volume)

    def to_list(self) -> list[float]:
        return [
            self.time, self.open, self.high, self.low, self.close, self.volume
        ]


@dataclass
class Position:
    instr_id: int
    qty: float = 0
    price: float = 0
    liquidation_price: Optional[float] = None

    def __str__(self) -> str:
        return f'{self.instr_id} {self.qty}@{self.price}'

    def __eq__(self, other: 'Position') -> bool:
        return self.instr_id == other.instr_id

    def __add__(self, other: 'Position') -> 'Position':
        if self != other:
            raise ValueError('Cannot add positions with different instruments')

        if other.qty == 0 or other.price == 0:
            return self
        if self.qty == 0 or self.price == 0:
            return other

        new_qty = self.qty + other.qty
        position = Position(self.instr_id, new_qty)

        is_reduce = self._is_reduce(other)
        is_reverse = self._is_reverse(other)

        if is_reduce:
            position.price = self.price
        elif is_reverse:
            position.price = other.price
        else:
            curr_amount = self.qty * self.price
            other_amount = other.qty * other.price
            position.price = (curr_amount + other_amount) / new_qty

        if position.qty == 0:
            position.price = 0

        return position

    def __sub__(self, other) -> 'Position':
        """UNKNOWN BEHAVIOR"""
        other.qty = -other.qty
        return self.__add__(other)

    @staticmethod
    def from_trade(trade: Trade):
        return Position(trade.instr_id, trade.qty, trade.price)

    def _is_reduce(self, other):
        new_qty = self.qty + other.qty
        is_reduce = (self.qty > 0 and new_qty >= 0 and self.qty > new_qty
                     or self.qty < 0 and new_qty <= 0 and self.qty < new_qty)
        return is_reduce

    def _is_reverse(self, other):
        new_qty = self.qty + other.qty
        return self.qty > 0 and new_qty < 0 or self.qty < 0 and new_qty > 0

    @staticmethod
    def calc_balance_consumption(pos1: 'Position', pos2: 'Position'):
        if pos1._is_reduce(pos2):
            amount = -abs(pos2.qty * pos2.price)
            return amount
        elif pos1._is_reverse(pos2):
            gain = abs(pos1.qty * pos1.price)
            cost = abs(pos2.qty * pos2.price)
            amount = -(gain + (gain - cost))
            return amount
        else:
            amount = abs(pos2.qty * pos2.price)
            return amount

    @property
    def notional(self):
        return round(self.qty * self.price, 9)

    @property
    def side(self):
        return LONG if self.qty > 0 else SHORT if self.qty < 0 else None


@dataclass
class Balance:
    # id: int
    exchange_id: int
    currency: str
    qty: float = 0
    total_qty: float = 0

    def __str__(self) -> str:
        return f'{self.exchange_id} {self.currency} {self.qty}'

    def __eq__(self, other) -> bool:
        return (self.exchange_id == other.exchange_id
                and self.currency == other.currency)

    def __gt__(self, other) -> bool:
        if isinstance(other, int | float):
            return self.qty > other
        if isinstance(other, 'Balance'):
            return self.qty > other.qty

    def __ge__(self, other) -> bool:
        return not self > other

    def __lt__(self, other) -> bool:
        if isinstance(other, int | float):
            return self.qty < other
        if isinstance(other, 'Balance'):
            return self.qty < other.qty

    def __le__(self, other) -> bool:
        return not self < other


@dataclass
class ConnectionStatus:
    #TODO Rework with generic attribute management...

    api: Optional[str | StatusEnum] = None
    trades: Optional[str | StatusEnum] = None
    l2_book: Optional[str | StatusEnum] = None
    funding: Optional[str | StatusEnum] = None
    private: Optional[str | StatusEnum] = None
    liquidations: Optional[str | StatusEnum] = None
    timestamp: Optional[float] = None

    def __init__(self, status: StatusEnum = None, **kwargs) -> None:
        self.api = status or kwargs.get('api')
        self.trades = status or kwargs.get('trades')
        self.l2_book = status or kwargs.get('l2_book')
        self.funding = status or kwargs.get('funding')
        self.private = status or kwargs.get('private')
        self.liquidations = status or kwargs.get('liquidations')
        self.timestamp = time.time()
        self.__post_init__()

    def __post_init__(self):
        if isinstance(self.api, str):
            self.api = StatusEnum[self.api]
        if isinstance(self.trades, str):
            self.trades = StatusEnum[self.trades]
        if isinstance(self.l2_book, str):
            self.l2_book = StatusEnum[self.l2_book]
        if isinstance(self.funding, str):
            self.funding = StatusEnum[self.funding]
        if isinstance(self.private, str):
            self.private = StatusEnum[self.private]
        if isinstance(self.liquidations, str):
            self.liquidations = StatusEnum[self.liquidations]

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self == other
        return self.api == self.trades == self.l2_book == self.funding == self.private == self.liquidations == other

    def __str__(self) -> str:
        return (f"{self.api.name if self.api else '_'} "
                f"{self.l2_book.name if self.l2_book else '_'} "
                f"{self.trades.name if self.trades else '_'} "
                f"{self.liquidations.name if self.liquidations else '_'} "
                f"{self.funding.name if self.funding else '_'} "
                f"{self.private.name if self.private else '_'} ")

    def __iadd__(self, other: 'ConnectionStatus') -> None:
        if other.api:
            self.api = other.api
        if other.trades:
            self.trades = other.trades
        if other.l2_book:
            self.l2_book = other.l2_book
        if other.funding:
            self.funding = other.funding
        if other.private:
            self.private = other.private
        if other.liquidations:
            self.liquidations = other.liquidations
        self.timestamp = other.timestamp or time.time()
        return self

    @property
    def trading_up(self) -> StatusEnum:
        return ((self.api == self.l2_book == self.private == StatusEnum.UP)
                or (self.api == self.trades == self.private == StatusEnum.UP))

    def set_all(self, status: StatusEnum):
        self.api = self.trades = self.l2_book = self.funding = self.private = self.liquidations = status


@dataclass(kw_only=True)
class ExchangeStatus(ConnectionStatus):
    exchange_id: int
    __eq__ = ConnectionStatus.__eq__

    def __init__(self,
                 exchange_id,
                 status: StatusEnum = None,
                 **kwargs) -> None:
        super().__init__(status, **kwargs)
        self.exchange_id = exchange_id

    def __iadd__(self, other: 'ExchangeStatus') -> None:
        if self.exchange_id != other.exchange_id:
            self.set_all(StatusEnum.UNKNOWN)
            raise ValueError(
                f'Cannot add exchange status with different exchange id {self.exchange_id} vs {other.exchange_id}'
            )
        return super().__iadd__(other)


@dataclass(kw_only=True)
class InstrStatus(ConnectionStatus):
    instr_id: int

    def __init__(self, instr_id, status: StatusEnum = None, **kwargs) -> None:
        super().__init__(status, **kwargs)
        self.instr_id = instr_id

    def __iadd__(self, other: 'InstrStatus') -> None:
        if self.instr_id != other.instr_id:
            self.set_all(StatusEnum.UNKNOWN)
            raise ValueError(
                f'Cannot add exchange status with different exchange id {self.exchange_id} vs {other.exchange_id}'
            )
        return super().__iadd__(other)


# WILL BE USED ALTER
@dataclass
class BasePayload:
    target_id: int
    action: str
    data: dict = None
    config: dict = None
    client_id: int = None


@dataclass
class ExchangeApiPayload:
    exchange_id: int
    action: str


@dataclass
class TriggerPayload:
    trigger_id: str
    action: str
    data: dict = None
    config: dict = None


@dataclass
class SentinelPayload:
    sentinel_id: str
    action: str  # snapshot, update, ...
    data: dict = None
    config: dict = None

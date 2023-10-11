from logging import Logger
from dataclasses import dataclass
from datetime import datetime, timezone
import traceback

from unsync import unsync
from cryptofeed.defines import *
# from ccxt.base.exchange import Exchange as ExchangeCcxt
from ccxt.async_support.base.exchange import Exchange as ExchangeCcxt

from arb_defines.defines import *
from arb_defines.arb_dataclasses import Balance, Candle, Exchange, Order, Position, Trade


@dataclass
class BaseFetcher:
    exchange: Exchange
    exchange_api: ExchangeCcxt
    code_mapping: object
    instr_id_mapping: object
    logger: Logger

    @unsync
    async def fetch_candles(self,
                            symbol,
                            tf='1m',
                            *args,
                            **kwargs) -> list[Candle]:
        try:
            self.logger.info(
                f'Fetching candles for {symbol}, {tf}, {args}, {kwargs}')
            raw_candles = await self.exchange_api.fetch_ohlcv(
                symbol, tf, *args, **kwargs)
            self.logger.info(f'Got {len(raw_candles)} candles')
            candles: list[Candle] = [Candle(*c) for c in raw_candles]
            return candles
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc())

    @unsync
    async def fetch_balance(self) -> list[Balance]:
        raw_balance = await self.exchange_api.fetch_balance()
        total_balance = raw_balance['total']
        free_balance = raw_balance['free']

        balances: list[Balance] = [
            Balance(self.exchange.id, currency, free_balance[currency],
                    total_qty)
            for currency, total_qty in total_balance.items() if total_qty != 0
        ]

        return balances

    @unsync
    async def fetch_positions(self) -> list[Position]:
        raw_positions = await self.exchange_api.fetch_positions()
        positions: list[Position] = []

        for p in raw_positions:
            instr_id = self.code_mapping.get(p['symbol'])
            if not instr_id:
                continue

            price = float(p.get('entryPrice') or 0)
            qty = float(p.get('contracts') or 0)
            qty = qty if p.get('side', LONG) == LONG else -qty
            pos = Position(instr_id, qty, price)
            if pos.qty != 0:
                positions.append(pos)

        return positions

    @unsync
    async def fetch_orders(self) -> list[Order]:
        raw_orders = await self.exchange_api.fetch_open_orders()

        return self.parse_orders(raw_orders)

    def parse_orders(self, raw_orders):
        orders = []
        for raw_order in raw_orders:
            parsed_order = self.parse_order(raw_order)
            if parsed_order:
                orders.append(parsed_order)

        return orders

    def parse_order(self, _order) -> Order:
        order_id = _order.get('clientOrderId')
        time = self._get_timestamp(_order)
        instr = self._get_instr_from_code(_order)
        exchange_order_id = _order['id']
        order_type = self._get_order_type(_order)
        order_status = self._get_order_status(_order)
        price = self._get_price(_order)
        qty = self._get_qty(_order)

        total_filled = float(_order['filled'])

        if not instr:
            self.logger.warning(
                f'Discarding order {_order} from {self.exchange.id}')
            return

        return Order(id=order_id,
                     time=time,
                     instr=instr,
                     exchange_order_id=exchange_order_id,
                     order_type=order_type,
                     order_status=order_status,
                     price=price,
                     qty=qty,
                     time_ack_mkt=time,
                     total_filled=total_filled)

    def parse_trade(self, _trade) -> Trade:
        instr = self._get_instr_from_code(_trade)
        time = self._get_timestamp(_trade)
        qty = self._get_qty(_trade)
        price = self._get_price(_trade)
        price = float(_trade.get('price', 0) or 0)
        order_type = self._get_order_type(_trade)
        fee = self._get_fee(_trade)

        return Trade(instr=instr,
                     time=time,
                     price=price,
                     qty=qty,
                     order_type=order_type,
                     fee=fee,
                     exchange_order_id=_trade['id'])

    def _get_instr_from_code(self, _order):
        instr_id = self.code_mapping.get(_order['symbol'])
        return self.instr_id_mapping.get(instr_id)

    @staticmethod
    def _get_timestamp(_order):
        return datetime.fromtimestamp(float(_order['timestamp']) / 1000,
                                      tz=timezone.utc)

    @staticmethod
    def _get_order_type(_order):
        """MAKER TAKER"""
        order_type = _order.get('type') or _order.get('takerOrMaker')
        if not order_type:
            return order_type
        order_type = order_type.lower()
        if order_type in [LIMIT, MAKER]:
            return MAKER
        if order_type in [MARKET, TAKER]:
            return TAKER
        return order_type

    @staticmethod
    def _get_order_status(_order):
        """OPEN PARTIAL FILLED CANCELLED REJECTED CLOSED"""
        status = _order['status'].lower()
        if status in [NEW, SUBMITTING, SUBMIT, SUBMITED, SUBMITTED, OPEN]:
            return OPEN
        if status in [FILL]:
            return FILLED
        if status in [CANCEL, CANCELED, CANCELLED]:
            return CANCELED
        if status in [REJECT, REJECTED]:
            return REJECTED
        if status in [CLOSE, CLOSED]:
            return CLOSED
        return status

    @staticmethod
    def _get_order_status_simulate(_order: Order):
        """SIMULATE ORDER STATUS, FILL ALL"""
        status = _order.order_status
        if status == OPEN:
            return FILLED
        return status

    @staticmethod
    def _get_fee(_order):
        fee = _order.get('fee') or _order.get('cost')
        if fee is not None:
            fee = fee.get('cost')
            if fee is not None:
                fee = float(fee)
        return fee

    @staticmethod
    def _get_qty(_order):
        qty = float(_order.get('amount', 0) or 0)
        qty = qty if _order.get('side', 'buy') == 'buy' else -abs(qty)
        return qty

    @staticmethod
    def _get_price(_order):
        return float(_order.get('price') or _order.get('stopPrice') or 0)

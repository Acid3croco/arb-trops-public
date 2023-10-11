from datetime import datetime, timezone

from cryptofeed.defines import *
from cryptofeed.feed import Feed
from cryptofeed.feedhandler import FeedHandler

from arb_defines.defines import *
from arb_defines.status import StatusEnum
from feed_handler.exchange_base import ExchangeBase
from redis_manager.redis_events import CandleEvent, LiquidationEvent
from arb_defines.arb_dataclasses import Candle, FundingRate, Instrument, OrderBook, Trade


class ExchangeWebsocket(ExchangeBase):

    def __init__(self, feed: Feed, instruments: list[Instrument], channels):
        super().__init__(feed, instruments, channels)
        self.instruments_status = {c: [] for c in channels}
        self.instruments_fundings = {
            i.id: [None, None, None]
            for i in instruments
        }
        self.feed_config = {'ignore_invalid_instruments': True}

    def disconnect(self):
        self.logger.info(f'Closing websocket {self.exchange}')
        kwargs = {chan: StatusEnum.UNAVAILABLE for chan in self.channels}
        self.exchange.set_status(**kwargs)
        for instrument in self.redis_manager.instruments.values():
            instrument.set_status(**kwargs)
        self.logger.info(f'Closed websocket {self.exchange}')

    def run(self):
        f = FeedHandler(config=self._get_handler_config())

        self.max_depth = 10
        self.candle_interval = '1m'
        channels = self.callbacks.keys()
        f.add_feed(
            self.feed(
                symbols=self.feed_codes,
                max_depth=self.max_depth,
                #   candle_interval=self.candle_interval,
                channels=channels,
                callbacks=self.callbacks,
                config=self.feed_config))
        # exceptions=[Exception],  # Add exceptions we want to handle

        self.logger.info(
            f'run websocket {self.exchange} - {list(channels)} - {len(self.instruments)} instruments: {self.instruments}'
        )
        # f.run(exception_handler=self.handle_exception)

        self._init_status()

        f.run()

    # async def handle_exception(self, loop, context):
    #     # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_exception_handler
    #     self.logger.error(f"handle_exception {context['message']}")

    def _init_status(self):
        for instr in self.redis_manager.instruments.values():
            if instr.instr_type != PERPETUAL:
                instr.set_status(ffh=StatusEnum.STARTING)

    def _handle_status(self, instr, channel):
        kwargs = {channel: StatusEnum.UP}
        if getattr(self.exchange.status, channel) != StatusEnum.UP:
            self.exchange.set_status(**kwargs)
        if instr.id not in self.instruments_status[channel]:
            self.instruments_status[channel].append(instr.id)
            instr.set_status(**kwargs)

    async def on_l2_book_cb(self, book, timestamp: float):
        instr = self.get_instr_from_code(book.symbol)
        self._handle_status(instr, L2_BOOK)

        letimestamp = book.timestamp or timestamp
        book = book.to_dict(numeric_type=float)
        bids = list(book[BOOK][BID].items())[:self.max_depth]
        asks = list(book[BOOK][ASK].items())[:self.max_depth]
        ob = OrderBook(instr_id=instr.id,
                       bids=bids,
                       asks=asks,
                       timestamp=letimestamp)

        instr.set_orderbook(ob)

    async def on_trades_cb(self, trade, timestamp: float):
        # exchange: BINANCE_FUTURES symbol: BTC-USDT-PERP side: sell amount: 0.048 price: 38952.80 id: 1195950340 type: None timestamp: 1651660007.272 - (exchange_websocket.py:75)
        instr = self.get_instr_from_code(trade.symbol)
        self._handle_status(instr, TRADES)

        qty = -trade.amount if trade.side == 'sell' else trade.amount
        trade = Trade(instr=instr,
                      price=trade.price,
                      qty=qty,
                      time=trade.timestamp,
                      order_type=trade.type,
                      exchange_order_id=trade.id,
                      trade_count=self._get_trade_count(trade))
        instr.set_last_trade(trade)

    async def on_liquidations_cb(self, liquidation, timestamp):
        # exchange: BINANCE_FUTURES symbol: BTC-USDT-PERP side: buy quantity: 0.002 price: 39199.20 id: None status: filled timestamp: 1651665953.216
        instr = self.get_instr_from_code(liquidation.symbol)
        self._handle_status(instr, LIQUIDATIONS)

        # in case the liquidation comes from a TRADES feed instead of a LIQUIDATIONS feed
        qty = liquidation.quantity if hasattr(
            liquidation, 'quantity') else liquidation.amount
        qty = -qty if liquidation.side == 'sell' else qty
        trade = Trade(instr=instr,
                      price=liquidation.price,
                      qty=qty,
                      time=liquidation.timestamp,
                      exchange_order_id=liquidation.id or 'liq',
                      is_liquidation=True)
        instr.set_last_trade(trade, LiquidationEvent)

    async def on_candles_cb(self, _candle, timestamp: float):
        # exchange: BYBIT symbol: BTC-USDT-PERP start: 1681462500.0 stop: 1681462560.0 interval: 1m trades: True open: 30712.2 close: 30716.6 high: 30716.6 low: 30710 volume: 37.388 closed: False timestamp: 1681462560.321062
        instr = self.get_instr_from_code(_candle.symbol)
        candle = Candle(
            instr=instr,
            trades=_candle.trades,
            open=_candle.open,
            high=_candle.high,
            low=_candle.low,
            close=_candle.close,
            volume=_candle.volume,
            time=_candle.start,
            end_time=_candle.stop,
        )
        self.logger.info(f'candle {candle}')
        instr.set_last_candle(candle, CandleEvent)

    async def on_funding_cb(self, obj, timestamp: float):
        instr = self.get_instr_from_code(obj.symbol)
        self._handle_status(instr, FUNDING)

        rate = self._get_rate(obj, instr)
        predicted_rate = self._get_predicted_rate(obj, instr)
        next_funding_time = self._get_next_funding_time(obj)

        funding_rate = FundingRate(instr_id=instr.id,
                                   rate=rate,
                                   predicted_rate=predicted_rate,
                                   next_funding_time=next_funding_time,
                                   timestamp=timestamp)
        instr.set_funding_rate(funding_rate)

    def _get_rate(sefl, obj, instr):
        rate = float(obj.rate or 0)
        return rate * instr.funding_multiplier

    def _get_predicted_rate(self, obj, instr):
        rate = float(obj.predicted_rate or 0)
        return rate * instr.funding_multiplier

    def _get_next_funding_time(self, obj):
        if obj.next_funding_time:
            return datetime.fromtimestamp(float(obj.next_funding_time),
                                          tz=timezone.utc)
        return None

    @staticmethod
    def _get_trade_count(trade):
        return 1

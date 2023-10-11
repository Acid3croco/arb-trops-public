import time
import asyncio

from datetime import datetime, timezone

from cryptofeed.defines import *

from arb_defines.defines import *
from redis_manager.redis_events import LiquidationEvent
from feed_handler.exchange_websocket import ExchangeWebsocket
from arb_defines.arb_dataclasses import FundingRate, Instrument, OrderBook, Trade


class ExchangeWebsocketPro(ExchangeWebsocket):
    is_pro = True
    depth_limit = None

    def run(self):
        self.max_depth = 10
        channels = self.callbacks.keys()

        self.logger.info(
            f'run websocket pro {self.exchange} - {list(channels)} - {len(self.instruments)} instruments: {self.instruments}'
        )

        self._init_status()

        tasks = []
        for instr in self.instruments:
            for channel in channels:
                tasks.append(self.callbacks[channel](instr))
        asyncio.run(self.run_tasks(tasks))

    async def run_tasks(self, tasks):
        await asyncio.gather(*tasks)

    async def on_l2_book_cb(self, instr):
        while True:
            try:
                orderbook = await self.feed.watch_order_book(
                    instr.feed_code, limit=self.depth_limit or self.max_depth)
            except Exception as e:
                self.logger.error(f'error on l2 book {instr.feed_code}: {e}')
                continue
            else:
                instr = self.get_instr_from_code(orderbook['symbol'])
                self._handle_status(instr, L2_BOOK)

                ob_ts = orderbook.get('timestamp')
                letimestamp = float(ob_ts) / 1000 if ob_ts else time.time()
                bids = orderbook['bids'][:self.max_depth]
                asks = orderbook['asks'][:self.max_depth]
                ob = OrderBook(instr_id=instr.id,
                               bids=bids,
                               asks=asks,
                               timestamp=letimestamp)

                instr.set_orderbook(ob)

    async def on_trades_cb(self, instr):
        while True:
            try:
                trades = await self.feed.watch_trades(instr.feed_code)
            except Exception as e:
                self.logger.error(f'error on trades {instr.feed_code}: {e}')
                continue
            else:
                instr = self.get_instr_from_code(trades[0]['symbol'])
                self._handle_status(instr, TRADES)

                for trade in trades:
                    qty = trade['amount'] * (1
                                             if trade['side'] == 'buy' else -1)
                    trade = Trade(instr=instr,
                                  price=trade['price'],
                                  qty=qty,
                                  time=trade['timestamp'] / 1000,
                                  order_type=trade['type'] or TAKER,
                                  exchange_order_id=trade['id'],
                                  trade_count=self._get_trade_count(trade))
                    instr.set_last_trade(trade)

    async def on_funding_cb(self, instr: Instrument):
        #! ONLY WORKS FOR BYBIT

        while True:
            try:
                ticker_info = await self.feed.watch_ticker(instr.feed_code)
            except Exception as e:
                self.logger.error(f'error on funding {instr.feed_code}: {e}')
                continue
            else:
                instr = self.get_instr_from_code(ticker_info['symbol'])
                self._handle_status(instr, FUNDING)

                rate = ticker_info.get('info', {}).get('fundingRate')
                predicted_rate = ticker_info.get('info', {}).get('fundingRate')
                next_funding_time = ticker_info.get('info',
                                                    {}).get('nextFundingTime')

                if rate:
                    rate = float(rate)
                if predicted_rate:
                    predicted_rate = float(predicted_rate)
                if next_funding_time:
                    next_funding_time = datetime.fromtimestamp(
                        float(next_funding_time) / 1000, tz=timezone.utc)

                rate = rate or self.instruments_fundings.get(
                    instr.id, (None, None, None))[0]
                predicted_rate = predicted_rate or self.instruments_fundings.get(
                    instr.id, (None, None, None))[1]
                next_funding_time = next_funding_time or self.instruments_fundings.get(
                    instr.id, (None, None, None))[2]

                if rate and predicted_rate and next_funding_time and (
                    (rate, predicted_rate, next_funding_time) !=
                        self.instruments_fundings.get(instr.id)):
                    funding_rate = FundingRate(
                        instr_id=instr.id,
                        rate=rate,
                        predicted_rate=predicted_rate,
                        next_funding_time=next_funding_time,
                        timestamp=ticker_info['timestamp'] / 1000,
                    )
                    instr.set_funding_rate(funding_rate)

                self.instruments_fundings[instr.id] = (rate, predicted_rate,
                                                       next_funding_time)

    # async def on_liquidations_cb(self, liquidation, timestamp):
    #     # exchange: BINANCE_FUTURES symbol: BTC-USDT-PERP side: buy quantity: 0.002 price: 39199.20 id: None status: filled timestamp: 1651665953.216
    #     instr = self.get_instr_from_code(liquidation.symbol)
    #     self._handle_status(instr, LIQUIDATIONS)

    #     # in case the liquidation comes from a TRADES feed instead of a LIQUIDATIONS feed
    #     qty = liquidation.quantity if hasattr(
    #         liquidation, 'quantity') else liquidation.amount
    #     qty = -qty if liquidation.side == 'sell' else qty
    #     trade = Trade(instr=instr,
    #                   price=liquidation.price,
    #                   qty=qty,
    #                   time=liquidation.timestamp,
    #                   exchange_order_id=liquidation.id or 'liq',
    #                   is_liquidation=True)
    #     instr.set_last_trade(trade, LiquidationEvent)

import uuid
import asyncio
import os.path
import pathlib

import ccxt.pro.bybit

from abc import abstractmethod
from datetime import datetime, timezone

from feed_handler.exchange_authenticated_websocket import ExchangeAuthenticatedWebsocket

from cryptofeed.defines import *
from cryptofeed.feed import Feed
from cryptofeed.symbols import Symbol
from cryptofeed.feedhandler import FeedHandler
from cryptofeed.defines import ORDER_INFO, FILLS, BALANCES, POSITIONS
from ccxt.async_support.base.exchange import Exchange as ExchangeCcxt

from arb_defines.defines import *
from db_handler.wrapper import DBWrapper
from arb_defines.status import StatusEnum
from exchange_api.base_fetcher import BaseFetcher
from feed_handler.feed_handler import PRIVATE_CHANNELS
from redis_manager.redis_wrappers import InstrumentRedis
from redis_manager.redis_events import BalanceEvent, PositionEvent, TradeExecEvent
from arb_defines.arb_dataclasses import Balance, Instrument, Order, Position, Trade


class ExchangeAuthenticatedWebsocketPro(ExchangeAuthenticatedWebsocket):
    is_pro = True
    feed_name = None
    has_orders = True
    fetcher: BaseFetcher = None

    def __init__(self, exchange, instruments: list[Instrument], *args):
        credentials = self._get_exchange_credentials()
        exchange.apiKey = credentials[exchange.id]['key_id']
        exchange.secret = credentials[exchange.id]['key_secret']
        super().__init__(exchange, instruments, *args)

        if not self.feed_name:
            raise NotImplementedError('Feed name not given in subclass')
        if not self.fetcher:
            raise NotImplementedError('Fetcher not given in subclass')

        self.code_mapping: dict[str, int] = {}
        self.instr_id_mapping: dict[int, Instrument] = {}
        for instr in instruments:
            self.code_mapping[instr.exchange_code] = instr.id
            self.instr_id_mapping[instr.id] = instr

        self._exchange = DBWrapper(logger=self.logger).get_exchange(
            feed_name=self.feed_name)

        self.fetcher = self.fetcher(self._exchange, self.exchange,
                                    self.code_mapping, self.instr_id_mapping,
                                    self.logger)

        self.logger.info(self.fetcher)

    def run(self):
        channels = self.callbacks.keys()

        self.logger.info(
            f'run authenticated websocket pro {self.exchange} - {list(channels)} - {len(self.instruments)} instruments: {self.instruments}'
        )

        self._init_status()

        tasks = []
        for instr in self.instruments:
            for channel in channels:
                tasks.append(self.callbacks[channel](instr))
        asyncio.run(self.run_tasks(tasks))

    def _init_status(self):
        for instr in self.redis_manager.instruments.values():
            instr.set_status(private=StatusEnum.UP)
        self.exchange.set_status(private=StatusEnum.UP)

    async def run_tasks(self, tasks):
        await asyncio.gather(*tasks)

    async def on_fills_cb(self, instr: Instrument):
        while True:
            trades = await self.feed.watch_my_trades(instr.feed_code)

            for trade_info in trades:
                self.logger.info(f'FILLS - {trade_info}')

                trade = self.fetcher.parse_trade(trade_info)
                trade.instr = self.get_instr_from_code(trade_info['symbol'])

                self.logger.debug(f'TRADE_INFO extract - {trade}')

                balance_consumption = self._update_position_from_trade(trade)
                self._update_balance_from_trade(trade, balance_consumption)

                self.redis.publish_event(TradeExecEvent, trade)

    async def on_order_info_cb(self, instr: Instrument):
        while True:
            orders = await self.feed.watch_orders(instr.feed_code)

            for order_info in orders:
                self.logger.info(f'ORDER_INFO - {order_info}')

                order = self.fetcher.parse_order(order_info)
                order.instr = self.get_instr_from_code(order_info['symbol'])
                self.logger.debug(f'ORDER_INFO extract - {order}')
                self.redis_manager.orders_manager.received_order(order)

import os
import yaml
import atexit
import logging
import pathlib

from abc import ABC, abstractmethod

from cryptofeed.feed import Feed
from cryptofeed.defines import L2_BOOK, TRADES, FUNDING, LIQUIDATIONS, ORDER_INFO, FILLS, BALANCES, CANDLES

from arb_logger.logger import get_logger
from arb_defines.arb_dataclasses import Instrument
from db_handler.wrapper import DBWrapper
from redis_manager.redis_manager import RedisManager


class ExchangeBase(ABC):
    has_orders = False
    # override this to add custom callbacks (ex: ftx_websocket.py)
    custom_callbacks = {}
    # is_pro to know if we need to use ccxtpro or cryptofeed
    is_pro = False

    def __init__(self, feed: Feed, instruments: list[Instrument],
                 channels: list[str]):
        if ORDER_INFO in channels:
            chanz = 'private'
        else:
            chanz = '_'.join(channels)
        self.logger = get_logger(f'{self.__class__.__name__}_{chanz}',
                                 short=True)

        self.feed: Feed = feed
        self.channels = channels

        self._build_mapping(instruments)
        if not self.instruments:
            self.logger.critical(f'Not instrument given, stoping now')
            exit(1)

        # used to cache exchange id to use exchange property
        self._exchange_id = self.instruments[0].exchange.id

        self.redis_manager: RedisManager = RedisManager(
            self.instruments, has_orders=self.has_orders, logger=self.logger)
        self.callbacks = self._get_callbacks()
        if not self.callbacks:
            raise ValueError(
                f'{self.feed.id} has no callbacks found for {self.channels} channels'
            )

    def _build_mapping(self, instruments: list[Instrument]):
        self.feed_codes = []
        self.code_mapping = {}
        self.instruments: list[Instrument] = [
            i for i in instruments
            #! COMMENTED THIS LINE TO FIX MEXC
            #! (IDS ARE NOW PRE FILTERED SO THIS LINE SHOULD BE USELESS BY NOW)
            # if i.exchange.feed_name == self.feed.id.upper()
        ]
        for instr in instruments:
            self.feed_codes.append(instr.feed_code)
            self.code_mapping[instr.feed_code] = instr.id

    @property
    def exchange(self):
        return self.redis_manager.get_exchange(self._exchange_id)

    @property
    def redis(self):
        return self.redis_manager.redis_handler

    @abstractmethod
    def run(self):
        raise NotImplementedError

    @abstractmethod
    def disconnect(self):
        raise NotImplementedError

    def _get_exchange_credentials(self):
        dirname = os.environ.get("ARB_TROPS_CONFIG_KEYS")
        config = pathlib.Path(dirname, "config_exchanges.yaml")
        config = yaml.load(config.read_text(), Loader=yaml.FullLoader)
        return config

    def _get_handler_config(self):
        handlers = [
            h for h in self.logger.handlers if hasattr(h, 'baseFilename')
        ]
        if handlers:
            filename = handlers[0].baseFilename
            return {'log': {'filename': filename, 'level': logging.INFO}}

    def get_instr_from_code(self, code: str):
        instr_id = self.code_mapping.get(code)
        if instr_id is None:
            instr = self._add_new_instr(code)
            instr_id = instr.id
        return self.redis_manager.get_instrument(instr_id)

    def _add_new_instr(self, feed_code: str) -> Instrument:
        db = DBWrapper(logger=self.logger)
        instr = db.get_instrument_from_feed_code(feed_code, self.exchange.id)
        self.redis_manager.add_instrument(instr)
        self.code_mapping[feed_code] = instr.id
        return instr

    def _get_available_callbacks(self):
        if self.is_pro is False:
            return self.feed.websocket_channels

        cb_pro_mapping = {
            # BALANCES: 'watchBalance',
            FILLS: self.feed.__dict__['has']['watchMyTrades'],
            ORDER_INFO: self.feed.__dict__['has']['watchOrders'],
            L2_BOOK: self.feed.__dict__['has']['watchOrderBook'],
            TRADES: self.feed.__dict__['has']['watchTrades'],
            FUNDING: self.feed.__dict__['has']['watchTicker'],
            # XXX: 'watchOHLCV',
            # XXX: 'watchTickers',
        }
        return {k: v for k, v in cb_pro_mapping.items() if v}

    def _get_callbacks(self):
        base_callbacks = {
            # BALANCES: self.on_balances_cb,
            # POSITIONS: self.on_positions_cb,
            FILLS: self.on_fills_cb,
            ORDER_INFO: self.on_order_info_cb,
            L2_BOOK: self.on_l2_book_cb,
            TRADES: self.on_trades_cb,
            LIQUIDATIONS: self.on_liquidations_cb,
            FUNDING: self.on_funding_cb,
            CANDLES: self.on_candles_cb,
        } | self.custom_callbacks

        return {
            k: v
            for k, v in base_callbacks.items()
            if k in self.channels and k in self._get_available_callbacks()
        }

    async def on_fills_cb(self, *args):
        raise NotImplementedError

    async def on_order_info_cb(self, *args):
        raise NotImplementedError

    async def on_l2_book_cb(self, *args):
        raise NotImplementedError

    async def on_trades_cb(self, *args):
        raise NotImplementedError

    async def on_funding_cb(self, *args):
        raise NotImplementedError

    async def on_liquidations_cb(self, *args):
        raise NotImplementedError

    async def on_candles_cb(self, *args):
        raise NotImplementedError


def exchange_run(exchange: ExchangeBase, instruments, channels=None):
    if channels is not None:
        exchange = exchange(instruments, channels)
    else:
        exchange = exchange(instruments)

    def clean_exit(sig=None, frame=None):
        nonlocal exchange
        exchange.disconnect()
        del exchange

    atexit.register(clean_exit)

    exchange.run()

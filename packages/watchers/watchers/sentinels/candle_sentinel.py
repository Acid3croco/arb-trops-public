import math

from datetime import datetime, timedelta, timezone

import pandas as pd

from arb_utils import arb_round
from arb_logger.logger import get_logger
from redis_manager.redis_events import TradeEvent
from data_manager.candle_manager import CandleManager
from arb_defines.arb_dataclasses import Candle, Instrument, Trade
from watchers.sentinel_base import SentinelBase, SentinelClientBase, sentinel_main

LOGGER = get_logger('candle_sentinel', short=True)


class CandleSentinel(SentinelBase):
    sentinel_name = 'candle'
    max_nb_candles = 10000

    def __init__(self, instruments) -> None:
        if len(instruments) != 1:
            raise ValueError(
                f'{self.__class__.__name__} needs exactly 1 instruments')

        self.instr: Instrument = instruments[0]
        super().__init__(instruments)

        self.tf = 60
        self.ltps = []

        self.load_candles()

    def load_candles(self):
        self.logger.info(f'Loading candles for {self.instr}')

        since = datetime.now(tz=timezone.utc) - timedelta(days=2)
        df: pd.DataFrame = CandleManager(self.instr).get_candles(since)

        self.values: list[Candle] = [
            Candle(*c) for c in df.reset_index().values.tolist()
        ]

        self.logger.info(f'Loaded {len(self.values)} candles')
        self.send_snapshot()

    def subscribe_to_events(self):
        self.redis_manager.heartbeat_event(self.tf,
                                           self.update_candles,
                                           is_pile=True)
        self.redis_manager.subscribe_event(TradeEvent(self.instruments),
                                           self.on_trade_event)
        super().subscribe_to_events()

    def on_trade_event(self, trade: Trade):
        self.ltps.append((trade.time, trade.price, trade.qty))

    def send_last_candle(self):
        self.send_update({'values': [self.values[-1]]})

    def update_candles(self):
        self.logger.info(f'Updating candle for {self.instr.id}')
        candle = Candle.from_ltps(self.ltps)
        self.ltps = []
        if candle:
            # round timestamp to start timestamp of candle period <-- not very clear but iykyk
            candle.time = datetime.fromtimestamp(arb_round(
                candle.time.timestamp(), self.tf, math.floor),
                                                 tz=timezone.utc)
        elif self.values:
            self.logger.info(
                f'No candle for {self.instr.id}, BUILD FROM LAST ONE')
            last_candle: Candle = self.values[-1]
            candle = Candle(last_candle.time + timedelta(seconds=self.tf),
                            last_candle.close, last_candle.close,
                            last_candle.close, last_candle.close, 0)

        if candle:
            self.values.append(candle)
            self.values = self.values[-self.max_nb_candles:]
            self.send_last_candle()


class CandleSentinelClient(SentinelClientBase):
    sentinel_class = CandleSentinel

    def _format_values(self, values):
        return [Candle(**c) for c in values]


def main():
    sentinel_main(CandleSentinel, grp_instr=False, logger=LOGGER)

import os
import json
import time

import numpy as np
import pandas as pd

from arb_logger.logger import get_logger

from data_manager.candle_manager import CandleManager

from redis_manager.redis_events import CandleEvent
from arb_defines.arb_dataclasses import Candle, Instrument
from watchers.sentinel_base import SentinelBase, sentinel_main

LOGGER = get_logger('target_sentinel', short=True)
TARGET_FILENAME = os.path.expandvars('$ARB_MODELS_PATH/targets.json')


class TargetSentinel(SentinelBase):
    grp_instr = True
    sort_instr = True
    sentinel_name = 'target'

    def __init__(self, instruments: list[Instrument]) -> None:
        if len(instruments) < 1:
            raise ValueError(
                f'{self.__class__.__name__} needs at least 1 instruments')

        self.tf = '1h'
        self.update_period = 60 * 60
        super().__init__(instruments)

        self.all_data = False
        self.loaded_candles = {instr.base: False for instr in instruments}
        [self._load_candles(instr) for instr in instruments]

    def subscribe_to_events(self):
        self.redis_manager.heartbeat_event(self.update_period,
                                           self.update_targets,
                                           is_pile=True,
                                           offset=1)

        self.redis_manager.subscribe_event(CandleEvent(self.instruments),
                                           self.on_candle_event)
        super().subscribe_to_events()

    def on_candle_event(self, candle: Candle):
        instr: Instrument = self.redis_manager.get_instrument(candle.instr_id)
        hist_candles = self.loaded_candles.get(instr.base)

        # unknow instrument
        if hist_candles is None:
            return

        if hist_candles is False or hist_candles.empty:
            hist_candles = self._load_candles(instr)
        if len(hist_candles.index) < 1:
            self.logger.warning(f'{instr} No candles loaded')
            return
        if (candle.time > hist_candles.index[-1] +
                np.timedelta64(self.update_period, 's') * 2):
            self.logger.info(
                f'Missing candles in between {candle} and {hist_candles.index[-1]}'
            )
            hist_candles = self._load_candles(instr)

        if candle.time < hist_candles.index[-2]:
            self.logger.info(f'{instr} Old candle')
            return
        if (candle.time == hist_candles.index[-2]
                or candle.time == hist_candles.index[-1]):
            self.logger.info(f'{instr} Updating candle')
        else:
            self.logger.info(f'{instr} New candle')
        hist_candles.loc[candle.time] = candle.close

        # Keep only the last 2000 candles
        self.loaded_candles[instr.base] = hist_candles[-2000:]

    def _load_candles(self, instrument: Instrument) -> pd.Series:
        hist_candles = CandleManager(instrument).get_candles(tf=self.tf)

        self.loaded_candles[instrument.base] = hist_candles['close']

        return hist_candles['close']

    def _has_all_data(self):
        if not self.all_data:
            self.logger.info('Check missing data')
            self.all_data = all(value is not False
                                for value in self.loaded_candles.values())
            if self.all_data:
                self.logger.info('All candles loaded')
            else:
                self.logger.info('Not all candles loaded')
        return self.all_data

    def _has_last_data(self):
        if self.all_data:
            self.logger.info('Check last data')
            last_minute = (pd.Timestamp.utcnow().floor('1min') -
                           np.timedelta64(self.update_period, 's'))
            missing_last = [
                value.index[-1] < last_minute
                for value in self.loaded_candles.values()
            ]
            if any(missing_last):
                self.logger.info(
                    f'missing_last {[x for x in missing_last if x]}')
                return False
            return True

    def update_targets(self):
        target = {}

        if not self._has_all_data():
            return

        self.logger.info('Will compute targets')
        retry = 0
        while not self._has_last_data() and retry < 5:
            retry += 1
            time.sleep(1)
        else:
            if retry == 5:
                self.logger.info(f'on est perdu')
                return

        df = pd.DataFrame(self.loaded_candles)
        targets = self.compute_targets(df)
        self.save_targets(targets)

    @staticmethod
    def zscore(x, window):
        r = x.rolling(window=window)
        m = r.mean().shift(1)
        s = r.std(ddof=0).shift(1)
        z = (x - m) / s
        return z

    def compute_targets(self, df):
        self.logger.info('Computing targets')

        base_df = np.log(df / df.shift(1))
        pdf = base_df.dropna(how='all',
                             axis=0).iloc[1:].dropna(axis=1).sort_index()

        selected_assets = pdf.columns

        smoothed_returns = pdf.ewm(alpha=0.9).mean()
        basket_returns = pdf.ewm(alpha=0.1).mean().mean(axis=1)

        ewma_volatility = smoothed_returns.ewm(span=10).std()
        _normalized_weights = 1 / ewma_volatility

        spreads = pd.DataFrame(index=pdf.index, columns=selected_assets)

        for asset in selected_assets:
            spreads[asset] = smoothed_returns[asset] - basket_returns

        rolling_window = 300
        spreads_rolling_zscore = self.zscore(spreads, rolling_window)

        target_position_size_long = spreads_rolling_zscore.rank(
            axis=1) / len(selected_assets)
        target_position_size_short = spreads_rolling_zscore.rank(
            axis=1, ascending=False) / len(selected_assets)

        long_threshold = 0.3  # Choose an appropriate threshold for long positions
        short_threshold = 0.3  # Choose an appropriate threshold for short positions

        long_signals = (target_position_size_long <=
                        long_threshold).astype(int)
        short_signals = (target_position_size_short <=
                         short_threshold).astype(int) * -1

        signals = long_signals + short_signals

        targets = signals.iloc[-1]
        timestamp = targets.name.timestamp()
        data = {'timestamp': timestamp, 'targets': targets.to_dict()}

        return data

    def save_targets(self, targets):
        json.dump(targets, open(TARGET_FILENAME, 'w'))


def main():
    sentinel_main(TargetSentinel, grp_instr=True, logger=LOGGER)


if __name__ == '__main__':
    main()

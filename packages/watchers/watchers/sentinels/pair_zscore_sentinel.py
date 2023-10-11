import pandas as pd

from statsmodels.regression.rolling import RollingOLS

from arb_logger.logger import get_logger
from watchers.sentinels.candle_sentinel import CandleSentinelClient
from watchers.sentinel_base import SentinelBase, SentinelClientBase, sentinel_main

LOGGER = get_logger('pair_zscore_sentinel', short=True)


# It's a sentinel that computes the z-score + beta of a pair
class PairZscoreSentinel(SentinelBase):
    sentinel_name = 'pair_zscore'
    grp_instr = True
    sort_instr = False

    def __init__(self,
                 instruments,
                 tf=60,
                 window=1440,
                 refresh_period=60) -> None:
        if len(instruments) != 2:
            raise ValueError(
                f'{self.__class__.__name__} needs exactly 2 instruments')

        super().__init__(sorted(instruments))
        # self.logger.setLevel('INFO')

        self.tf = tf
        self.window = window
        self.refresh_period = refresh_period or self.tf

        self.candle_sentinels = {
            i.id: CandleSentinelClient(self.redis_manager, [i])
            for i in instruments
        }

    def subscribe_to_events(self):
        self.redis_manager.heartbeat_event(self.refresh_period,
                                           self.update,
                                           is_pile=True,
                                           offset=1)
        super().subscribe_to_events()

    def update(self):
        self.logger.info('Updating')
        sym1, sym2 = self.candle_sentinels.values()
        if not sym1.values or not sym2.values:
            self.logger.warning('Not enough data to update')
            return

        self.logger.info(f'sym1 {len(sym1.values)}, sym2 {len(sym2.values)}')

        df = pd.DataFrame([[c.time, c.close] for c in sym1.values],
                          columns=['time', 'instr1'])
        df = df.set_index('time').sort_index()
        _df = pd.DataFrame([[c.time, c.close] for c in sym2.values],
                           columns=['time', 'instr2'])
        df = df.join(_df.set_index('time'), how='outer')
        df.sort_index(inplace=True)
        df.dropna(inplace=True)
        df = df.iloc[-self.window * 2:]
        self.logger.info(f'{len(df)} candles, computing z-score')

        base_sym = df.columns[0]
        test_sym = df.columns[1]
        model = RollingOLS(df[base_sym], df[test_sym],
                           window=self.window).fit()
        df['beta'] = model.params.bfill()
        df[f'{test_sym}_norm'] = df['beta'] * df[test_sym]
        df['spread'] = df[base_sym] - df[f'{test_sym}_norm']

        df['col_mean'] = df['spread'].rolling(window=self.window).mean()
        df['col_std'] = df['spread'].rolling(window=self.window).std()
        df['r_zscore'] = (df['spread'] - df['col_mean']) / df['col_std']

        last_beta = df['beta'].iloc[-1]
        last_zscore = df['r_zscore'].iloc[-1]
        self.logger.info(f'Z-score: {last_zscore}, beta: {last_beta}')
        if not self.values:
            self.values = [
                (b, z) for b, z in df[['beta', 'r_zscore']].dropna().values
            ]
        else:
            self.values.append((last_beta, last_zscore))
        self.send_update()


class PairZscoreSentinelClient(SentinelClientBase):
    sentinel_class = PairZscoreSentinel


def main():
    sentinel_main(PairZscoreSentinel, grp_instr=True, logger=LOGGER)

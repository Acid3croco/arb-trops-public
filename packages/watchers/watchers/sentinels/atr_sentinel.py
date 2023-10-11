import os

import pandas as pd

from ta.volatility import AverageTrueRange

from arb_logger.logger import get_logger
from redis_manager.redis_events import TradeEvent
from arb_utils.resolver import resolve_instruments
from arb_defines.arb_dataclasses import Candle, Trade
from redis_manager.redis_wrappers import InstrumentRedis
from arb_utils.args_parser import instruments_args_parser
from watchers.sentinel_base import SentinelBase, SentinelClientBase

LOGGER = get_logger('atr_sentinel', short=True)


class AtrSentinel(SentinelBase):
    sentinel_name = 'atr'

    def __init__(self, instruments, atr_len, tf) -> None:
        if len(instruments) != 1:
            raise ValueError(
                f'{self.__class__.__name__} needs exactly 1 instruments')

        super().__init__(instruments)
        self.instr = instruments[0]

        self.tf = tf
        self.atr_len = atr_len

        self.ohlc = []
        self.ltps = []

    @property
    def instrument(self) -> InstrumentRedis:
        return self.redis_manager.get_instrument(self.instr)

    def subscribe_to_events(self):
        self.redis_manager.heartbeat_event(self.tf,
                                           self.update_atr,
                                           is_pile=True)
        self.redis_manager.subscribe_event(TradeEvent(self.instrument),
                                           self.on_trade_event)

    def on_trade_event(self, trade: Trade):
        self.ltps.append((trade.time, trade.price, trade.qty))

    @staticmethod
    def calc_atr(ohlc, length):
        df = pd.DataFrame(
            ohlc, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        atr = AverageTrueRange(df['high'],
                               df['low'],
                               df['close'],
                               window=length).average_true_range()
        return atr.iloc[-1]

    def send_atr_update(self):
        data = {'value': self.values[-1][1]}
        self.send_update(data)

    def update_atr(self):
        self.logger.info(f'Updating atr for {self.instr.id}')
        candle = Candle.from_ltps(self.ltps)
        if candle:
            self.ohlc.append(candle.to_list())
            self.ltps = []
            self.ohlc = self.ohlc[-self.atr_len * 10:]

        if len(self.ohlc) >= self.atr_len:
            atr = self.calc_atr(self.ohlc, self.atr_len)
            self.logger.info(f'{self.instr.id} atr: {atr}')
            timestamp = self.ohlc[-1][0]
            # arb_round(self.ohlc[-1][0], self.tf, method=math.floor)
            self.values.append((timestamp, atr))
            self.send_atr_update()
        else:
            self.values = []


class AtrSentinelClient(SentinelClientBase):
    sentinel_class: SentinelBase = AtrSentinel


def start_sentinel(args, instruments):
    process_name = f'atr_sentinel'
    kill_cmd = f'pkill -f "{process_name}"'
    LOGGER.info(kill_cmd)
    os.system(kill_cmd)

    if args.kill:
        return

    instr_ids = ' '.join([str(i.id) for i in instruments])
    cmd = f'{process_name} --daemon --instr-ids {instr_ids} --atr-len {args.atr_len} --tf {args.tf}'
    run_cmd = f'nohup {cmd} </dev/null >/dev/null 2>&1 &'
    LOGGER.info(run_cmd)
    os.system(run_cmd)


def main():
    parser = instruments_args_parser('AtrSentinel')
    parser.add_argument('--atr-len', type=int, default=5)
    parser.add_argument('--tf',
                        type=int,
                        default=10,
                        help='Timeframe in seconds')

    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--kill', action='store_true', help='Kill recorder')

    args = parser.parse_args()

    instruments = resolve_instruments(args)

    if args.daemon:
        sentinel = AtrSentinel(instruments, args.atr_len, args.tf)
        return sentinel.run()
    start_sentinel(args, instruments)


if __name__ == '__main__':
    main()

# def main():
#     arb_daemon_main(AtrSentinel, parser=instruments_args_parser('AtrSentinel'))

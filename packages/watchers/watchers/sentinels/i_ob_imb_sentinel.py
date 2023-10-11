from datetime import datetime

import pandas as pd

from arb_logger.logger import get_logger
from arb_defines.arb_dataclasses import OrderBook, Trade
from redis_manager.redis_events import OrderBookEvent, TradeEvent
from watchers.sentinel_base import SentinelBase, SentinelClientBase, sentinel_main

LOGGER = get_logger('i_ob_imb_sentinel', short=True)


class IObImbSentinel(SentinelBase):
    sentinel_name = 'i_ob_imb'

    def __init__(self, instruments, window=30) -> None:
        if len(instruments) != 1:
            raise ValueError(
                f'{self.__class__.__name__} needs exactly 1 instruments')

        super().__init__(instruments)
        self.instr = instruments[0]
        self.logger.setLevel('INFO')

        self.window = window

        self.trades = []
        self.fair_cvd = None
        self.fair_value = None
        self.fair_mid = None

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(OrderBookEvent(self.instr),
                                           self.on_order_book_event)
        self.redis_manager.subscribe_event(TradeEvent(self.instr),
                                           self.on_trade_event)

    def on_order_book_event(self, orderbook: OrderBook):
        # instr = self.instruments.get(orderbook.instr_id)
        # self.logger.info(f'Orderbook {orderbook}')
        depth = len(orderbook.bids)
        columns = []
        for side in ['bid', 'ask']:
            for a in range(depth):
                columns.append(f'{side}_{a}')
                columns.append(f'{side}_size_{a}')
        book = ([item for sublist in orderbook.bids for item in sublist] +
                [item for sublist in orderbook.asks for item in sublist])
        df = pd.DataFrame([book], columns=columns)
        bids_size_col = [f'bid_size_{a}' for a in range(depth)]
        asks_size_col = [f'ask_size_{a}' for a in range(depth)]
        df['bids_sum'] = df[bids_size_col].sum(axis=1)
        df['asks_sum'] = df[asks_size_col].sum(axis=1)
        # self.logger.info(f'SUMS: {df["bids_sum"].values[-1]} {df["asks_sum"].values[-1]}')
        bid_w = 0
        ask_w = 0
        mid_w = 0
        # weights =
        for a in range(depth):
            bid_w += df[f'bid_{a}'] * df[f'bid_size_{a}']
            ask_w += df[f'ask_{a}'] * df[f'ask_size_{a}']
            mid_w += df[f'bid_{a}'] * df[f'bid_size_{a}'] + df[
                f'ask_{a}'] * df[f'ask_size_{a}']
        df['weighted_bid_price'] = bid_w / df['bids_sum']
        df['weighted_ask_price'] = ask_w / df['asks_sum']
        df['weighted_mid_price'] = mid_w / (df['bids_sum'] + df['asks_sum'])
        df['spread'] = df['ask_0'] - df['bid_0']
        df['mid'] = (df['bid_0'] + df['ask_0']) / 2
        df['imbalance'] = df['bids_sum'] / (df['bids_sum'] + df['asks_sum'])

        mid = df['mid'].values[-1]
        w_mid = df['weighted_mid_price'].values[-1]
        fair_mid = mid + (mid - w_mid)
        w_bid = df['weighted_bid_price'].values[-1]
        w_ask = df['weighted_ask_price'].values[-1]
        fair_value = (w_bid + w_ask) / 2
        fair_value = mid + (mid - fair_value)

        self.fair_value = fair_value
        self.fair_mid = fair_mid
        self._send_update()

    def on_trade_event(self, trade: Trade):
        self.trades.append([trade.time, trade.price, trade.amount])

        cdv_delta_sec = 15

        df = pd.DataFrame(self.trades, columns=['time', 'price', 'amount'])
        df = df.set_index('time')
        df.index = pd.to_datetime(df.index, unit='s')
        df = df[df.index > pd.Timestamp.utcnow() -
                pd.Timedelta(seconds=cdv_delta_sec)]
        cum_amount = df['amount'].cumsum()
        cvd = cum_amount.values[-1]

        self.fair_cvd = cvd
        self._send_update()
        self.trades = df.reset_index().values.tolist()
        # df['cum_amount'].values[-1] / df['amount'].sum()

    def _send_update(self):
        data = [
            datetime.now().timestamp(),
            self.fair_value,
            self.fair_mid,
            self.fair_cvd,
        ]
        self.logger.info(f'Sending data: {data}')
        self.send_update(data)


class IObImbSentinelClient(SentinelClientBase):
    sentinel_class = IObImbSentinel


def main():
    sentinel_main(IObImbSentinel,
                  grp_instr=IObImbSentinel.grp_instr,
                  logger=LOGGER)

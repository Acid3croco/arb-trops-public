from datetime import datetime
from collections import defaultdict

from arb_logger.logger import get_logger
from arb_utils import arb_round

from cryptofeed.defines import BUY, SELL
from redis_manager.redis_events import TradeEvent
from arb_defines.arb_dataclasses import Instrument, Trade
from watchers.sentinel_base import SentinelBase, sentinel_main

LOGGER = get_logger('price_impact', short=True)


class PriceImpactSentinel(SentinelBase):
    sentinel_name = 'price_impact'
    grp_instr = False
    log_level = 'INFO'

    def __init__(self, instruments):
        if len(instruments) != 1:
            raise ValueError(
                f'{self.__class__.__name__} needs exactly 1 instrument')

        self.log_name = f'{self.__class__.__name__}.{instruments[0].id}'
        super().__init__(instruments)

        self.instr: Instrument = instruments[0]

        self.last_trade: dict[Instrument, dict[str,
                                               Trade]] = defaultdict(lambda: {
                                                   BUY: None,
                                                   SELL: None
                                               })

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(TradeEvent(self.instruments),
                                           self.on_trade_event)
        self.redis_manager.heartbeat_event(60 * 60,
                                           self.clean_stream,
                                           is_pile=True)

    def on_trade_event(self, trade: Trade):
        instr = self.instruments[trade.instr_id]
        trade.instr = instr

        prev_trade = self.last_trade[instr][trade.side]

        # if no prev trade, just update prev trade
        if not prev_trade:
            self.last_trade[instr][trade.side] = trade
            return
        # here we have a prev trade and a new trade that are on the same side

        # if prev trade.time == trade.time
        #   -> aggregate them as its the samer taker
        # or prev trade.price == trade.price
        #   -> aggregate them as its the same price (we consider its the same price level)\
        #      as we want to measure absorption of price levels (how much taker a level can absorb)
        #      + we can aggregate them and prevent 0 pct_change price impact error
        same_price = arb_round(trade.price, instr.tick_size) == arb_round(
            prev_trade.price, instr.tick_size)

        if trade.time == prev_trade.time or same_price:
            prev_trade.time = trade.time
            prev_trade.qty += trade.qty
            prev_trade.trade_count += trade.trade_count
            # prev_trade.price = (trade.price * trade.qty + prev_trade.price *
            #                     prev_trade.qty) / (trade.qty + prev_trade.qty)
            # self.logger.info(f'Aggregating trades: {prev_trade}')
            return

        # here we have a new price level trader on the same side, we can calculate price impact
        # meaning we will calculate how much qty was needed for this new price level to be traded
        # we will add the prev_trade.qty to the current trade qty then compute the price impact
        pct_change = (trade.price -
                      prev_trade.price) / prev_trade.price * 10000  # in bps
        price_impact = abs(prev_trade.amount + trade.amount) / pct_change
        self.logger.info(
            f'New price level trade: {trade.price}, prev: {prev_trade.price}, pct_change: {pct_change}, price_impact: {price_impact} (prev: {prev_trade.amount}, new: {trade.amount})'
        )

        data = {
            'ts': trade.time.timestamp(),
            'instr_id': trade.instr_id,
            'qty': prev_trade.qty + trade.qty,
            'pct_change': pct_change,
            'side': trade.side,
            'price': trade.price,
            'price_impact': price_impact,
        }
        self.logger.warning(f'Sending data: {data}')
        self.send_update(list(data.values()))
        self._add_to_db(data)

        self.last_trade[instr][trade.side] = trade

    def clean_stream(self):
        redis = self.redis_manager.redis_instance
        # min id is ts in ms of now less 1 week
        min_id = int((datetime.now() - 60 * 60 * 24 * 7) * 1000)
        redis.xtrim(f'price_impact:{self.instr.id}', minid=min_id)

    def _add_to_db(self, data):
        redis = self.redis_manager.redis_instance
        redis.xadd(f'price_impact:{self.instr.id}', data)


def main():
    # group instr so that 1 sentinel is created for all instrs
    sentinel_main(PriceImpactSentinel,
                  grp_instr=PriceImpactSentinel.grp_instr,
                  logger=LOGGER)


if __name__ == '__main__':
    main()

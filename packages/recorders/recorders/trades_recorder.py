import logging

from typing import Optional
from datetime import datetime

from cryptofeed.defines import *

from arb_defines.defines import *
from arb_logger.logger import get_logger
from redis_manager.redis_events import LiquidationEvent, TradeEvent
from recorders.base_recorder import BaseRecorder, main as base_main

process_name = 'trades_recorder'
LOGGER = get_logger(process_name, short=True)


class TradeSmall:
    time: datetime = None
    qty: float = None
    price: float = None
    instr_id: Optional[int] = None
    is_liquidation: bool = False
    trade_count: int = 1

    columns = ['instr_id', 'qty', 'price', 'is_liquidation', 'trade_count']

    def to_list(self):
        return [
            self.time.timestamp(),
            self.instr_id,
            self.qty,
            self.price,
            self.is_liquidation,
            self.trade_count,
        ]


class TradesRecorder(BaseRecorder):
    class_small = TradeSmall
    recorder_type = 'trades'
    notify_new_values = False

    def subscribe_to_events(self):
        # self.logger.setLevel(logging.INFO)
        self.redis_manager.psubscribe_event(TradeEvent, self.on_any_event)
        self.redis_manager.psubscribe_event(LiquidationEvent,
                                            self.on_any_event)


def main():
    base_main(TradesRecorder, LOGGER)

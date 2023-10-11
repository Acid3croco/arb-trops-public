import logging

import pandas as pd

from arb_logger.logger import get_logger
from arb_defines.arb_dataclasses import OrderBook
from redis_manager.redis_events import OrderBookEvent
from recorders.base_recorder import BaseRecorder, main as base_main

process_name = 'l2_book_recorder'
LOGGER = get_logger(process_name, short=True)


class OrderBookSmall(OrderBook):

    def to_list(self):
        bids = [x for xs in self.bids for x in xs]
        asks = [x for xs in self.asks for x in xs]
        return [self.timestamp, self.instr_id,
                len(self.bids),
                len(self.asks)] + bids + asks


class L2BookRecorder(BaseRecorder):
    recorder_type = 'l2_book'
    class_small = OrderBookSmall
    notify_new_values = False

    def subscribe_to_events(self):
        self.logger.setLevel(logging.INFO)
        self.redis_manager.psubscribe_event(OrderBookEvent, self.on_any_event)


def main():
    base_main(L2BookRecorder, LOGGER)


if __name__ == '__main__':
    main()

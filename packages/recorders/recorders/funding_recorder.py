from cryptofeed.defines import *

from arb_defines.defines import *
from arb_logger.logger import get_logger
from arb_defines.arb_dataclasses import FundingRate
from redis_manager.redis_events import FundingRateEvent
from recorders.base_recorder import BaseRecorder, main as base_main

process_name = 'funding_recorder'
LOGGER = get_logger(process_name, short=True)


class FundingRateSmall(FundingRate):
    columns = ['instrument', 'rate', 'predicted_rate', 'next_funding_time']

    def to_list(self):
        return [
            self.time.timestamp(),
            self.instr_id,
            self.rate,
            self.predicted_rate,
            self.next_funding_time,
        ]


class FundingRateRecorder(BaseRecorder):
    class_small = FundingRateSmall
    recorder_type = 'funding'

    def subscribe_to_events(self):
        self.redis_manager.psubscribe_event(FundingRateEvent,
                                            self.on_any_event)


def main():
    base_main(FundingRateRecorder, LOGGER)
from arb_logger.logger import get_logger
from recorders.funding_recorder import FundingRateSmall
from recorders.base_reader import BaseReader, main as base_main

process_name = 'funding_reader'
LOGGER = get_logger(process_name, short=True)


class FundingReader(BaseReader):
    recorder_type = 'funding'
    class_small = FundingRateSmall


def main():
    base_main(FundingReader, LOGGER)
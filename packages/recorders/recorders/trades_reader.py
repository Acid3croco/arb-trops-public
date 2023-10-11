from arb_logger.logger import get_logger
from recorders.base_reader import BaseReader, main as base_main
from recorders.trades_recorder import TradeSmall

process_name = 'trades_reader'
LOGGER = get_logger(process_name, short=True)


class TradesReader(BaseReader):
    recorder_type = 'trades'
    class_small = TradeSmall


def main():
    base_main(TradesReader, LOGGER)
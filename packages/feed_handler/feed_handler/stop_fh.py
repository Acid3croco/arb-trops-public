from arb_logger.logger import get_logger
from feed_handler.start_fh import main as start_fh_main

LOGGER = get_logger('stop_fh', short=True)


def main():
    start_fh_main(stop=True)

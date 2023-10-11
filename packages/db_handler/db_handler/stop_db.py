import os

from arb_logger.logger import get_logger

LOGGER = get_logger('stop_db', short=True)


def stop_db_invoke():
    kill_cmd = f'pkill -f db_handler'
    LOGGER.info(kill_cmd)
    os.system(kill_cmd)


def main():
    stop_db_invoke()

import os

from arb_logger.logger import get_logger

LOGGER = get_logger('start_db', short=True)


def start_db_invoke():
    kill_cmd = f'pkill -f db_handler'
    LOGGER.info(kill_cmd)
    os.system(kill_cmd)

    cmd = f'db_handler'
    run_cmd = f'nohup {cmd} </dev/null >/dev/null 2>&1 &'
    LOGGER.info(run_cmd)
    os.system(run_cmd)


def main():
    start_db_invoke()

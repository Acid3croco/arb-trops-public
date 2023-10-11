import os
import time

from datetime import datetime, time as dt_time

from arb_logger.logger import get_logger

LOGGER = get_logger(__name__, short=True)

commands = [
    (dt_time(00, 00), 'load_codes'),
    (dt_time(00, 00), 'start_fh -C funding -t perpetual'),
]

LOGGER.info('Kill any script_reloader processes')
os.system('pkill -f script_reloader.py')
LOGGER.info('Starting script reloader')
LOGGER.info(commands)

while True:
    now = datetime.now()
    for dt, cmd in commands:
        if now.time() == dt:
            LOGGER.info(f'Running command: {cmd}')
            os.system(cmd)
    time.sleep(60)

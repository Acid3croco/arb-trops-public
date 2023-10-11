import os
import re

from argparse import ArgumentParser

from arb_logger.logger import get_logger

LOGGER = get_logger('arb_daemon', short=True)


def to_snake_case(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('__([A-Z])', r'_\1', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return name.lower()


def start_process(args, process_name, process_regex=None):
    if not process_regex:
        process_regex = process_name
    kill_cmd = f'pkill -f "{process_regex}"'
    LOGGER.info(kill_cmd)
    os.system(kill_cmd)

    if args.kill:
        return
    cmd = f'{process_name} --daemon'
    run_cmd = f'nohup {cmd} </dev/null >/dev/null 2>&1 &'
    LOGGER.info(run_cmd)
    os.system(run_cmd)


def main(process_class,
         process_name=None,
         process_regex=None,
         parser=None,
         logger=None,
         single_instr=False):
    if logger:
        global LOGGER
        LOGGER = logger

    if not parser:
        parser = ArgumentParser()

    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--no-kill',
                        action='store_true',
                        help="Don't kill existing processes")
    parser.add_argument(
        '--kill',
        action='store_true',
        help="Only kill existing processes without starting new ones")

    args = parser.parse_args()

    if args.daemon:
        process = process_class()
        return process.run()
    if not process_name:
        process_name = to_snake_case(process_class.__name__)
    start_process(args, process_name, process_regex)

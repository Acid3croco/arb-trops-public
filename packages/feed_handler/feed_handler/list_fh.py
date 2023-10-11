import subprocess

from argparse import ArgumentParser

from arb_logger.logger import get_logger
from feed_handler.feed_handler import PRIVATE_CHANNELS, PUBLIC_CHANNELS

LOGGER = get_logger('list_fh', short=True)


def list_fh_invoke(args):
    #TODO: Add args filters to list_fh

    LOGGER.info('List feed_handlers')
    ps = subprocess.run(['ps', 'aux'], check=True, capture_output=True)

    process_names = subprocess.run(['grep', f'feed_handler'],
                                   input=ps.stdout,
                                   capture_output=True)
    res = process_names.stdout.decode('utf-8')
    if res:
        print(res.strip())
    else:
        LOGGER.info('No feed_handlers')


def main():
    parser = ArgumentParser(description='list feed_handlers')

    parser.add_argument('-e', '--exchanges', metavar='EXCHANGE', nargs='*')
    parser.add_argument('-c',
                        '--channels',
                        nargs='*',
                        choices=PUBLIC_CHANNELS + PRIVATE_CHANNELS)
    args = parser.parse_args()

    list_fh_invoke(args)

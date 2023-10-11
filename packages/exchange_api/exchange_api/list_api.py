import subprocess

from argparse import ArgumentParser

from arb_logger.logger import get_logger

LOGGER = get_logger('list_api', short=True)


def list_api_invoke(args):
    LOGGER.info('List exchange_api')
    ps = subprocess.run(['ps', 'aux'], check=True, capture_output=True)

    process_names = subprocess.run(['grep', f'exchange_api'],
                                   input=ps.stdout,
                                   capture_output=True)
    res = process_names.stdout.decode('utf-8')
    if res:
        print(res.strip())
    else:
        LOGGER.info('No exchange_api')


def main():
    parser = ArgumentParser(description='list exchange_api')

    parser.add_argument('-e', '--exchanges', metavar='EXCHANGE', nargs='*')
    args = parser.parse_args()

    list_api_invoke(args)

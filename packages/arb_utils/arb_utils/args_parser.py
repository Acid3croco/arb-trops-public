from argparse import ArgumentParser

from cryptofeed.defines import *

from arb_defines.defines import *


def instruments_args_parser(description='', allow_all=False):
    # TODO: add support for allow_all flag
    parser = ArgumentParser(description=description)

    default_types = [SPOT, PERPETUAL, FUTURES]
    parser.add_argument('-b', '--bases', metavar='BASE', nargs='*')
    parser.add_argument('-q', '--quotes', metavar='QUOTE', nargs='*')
    parser.add_argument('-t',
                        '--instr-types',
                        metavar='TYPE',
                        nargs='*',
                        default=default_types)
    parser.add_argument('-c',
                        '--contract-types',
                        metavar='CONTRACT',
                        nargs='*',
                        default=[LINEAR])
    parser.add_argument('-e', '--exchanges', metavar='EXCHANGE', nargs='*')
    parser.add_argument('-i',
                        '--instr-ids',
                        metavar='INSTR_ID',
                        nargs='*',
                        type=int)

    return parser


def simple_args_parser(description=''):
    parser = ArgumentParser(description=description)

    parser.add_argument('-e', '--exchange', metavar='EXCHANGE', required=True)
    parser.add_argument('-i',
                        '--instr-ids',
                        metavar='INSTR_ID',
                        nargs='+',
                        type=int,
                        required=True)

    return parser

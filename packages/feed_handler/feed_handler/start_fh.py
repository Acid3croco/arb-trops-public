import os
import sys

from argparse import ArgumentParser

import numpy as np

from cryptofeed.defines import TRADES, LIQUIDATIONS

from arb_logger.logger import get_logger
from db_handler.wrapper import DBWrapper
from arb_defines.defines import PRIVATE, PUBLIC
from arb_defines.arb_dataclasses import Instrument
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser
from feed_handler.feed_handler import PUBLIC_CHANNELS, PRIVATE_CHANNELS

LOGGER = get_logger('start_fh', short=True)


def build_channels_groups(channels, stop=False):
    grps = []
    for chan in channels:
        if chan in PRIVATE_CHANNELS:
            grps.append(PRIVATE_CHANNELS)
        elif chan == TRADES:
            grps.append((TRADES, LIQUIDATIONS))
        else:
            grps.append((chan, ))
    if TRADES in channels and (LIQUIDATIONS, ) in grps and not stop:
        grps.remove((LIQUIDATIONS, ))
    return set(grps)


def get_channels_groups(args):
    channels = args.channels or []
    if args.stop is True and args.modes is None and args.channels is None:
        channels = PUBLIC_CHANNELS + PRIVATE_CHANNELS
    if args.modes:
        channels += ((PUBLIC_CHANNELS if PUBLIC in args.modes else tuple()) +
                     (PRIVATE_CHANNELS if PRIVATE in args.modes else tuple()))
    return build_channels_groups(channels, args.stop)


def get_instr_id_groups(chans, instr_ids):
    if not instr_ids:
        return ['dummy']
    nb_co = len(chans) * len(instr_ids)
    # maximum 150 channels per feed handler
    chuncks = nb_co // 150 + 1
    return np.array_split(instr_ids, chuncks)


def spawn_daemon(exchange, args, instruments):
    #TODO filter instruments by channels
    _instr_ids = [str(i.id) for i in instruments]

    chan_grps = get_channels_groups(args)

    for _chans in chan_grps:
        grp_ids = get_instr_id_groups(_chans, _instr_ids)
        chans = ' '.join(sorted(_chans))
        if not args.no_kill:
            kill_cmd = f'pkill -f "feed_handler.* {exchange} .*{chans}"'
            LOGGER.info(kill_cmd)
            if not args.cmd:
                os.system(kill_cmd)
        for instr_ids in grp_ids:
            instr_ids = ' '.join(instr_ids)

            cmd = f'feed_handler --exchange {exchange} --channels {chans} --instr-ids {instr_ids}'

            if not args.stop:
                run_cmd = f'nohup {cmd} </dev/null >/dev/null 2>&1 &'
                LOGGER.info(run_cmd)
                if not args.cmd:
                    os.system(run_cmd)


def start_fh_invoke(args):
    if args.stop is True:
        instruments = []
        if args.exchanges:
            exchanges = args.exchanges
        else:
            db_wrapper = DBWrapper(logger=LOGGER)
            exchanges = db_wrapper.get_exchanges()
    else:
        instruments: list[Instrument] = resolve_instruments(args)
        if not instruments:
            LOGGER.error('No instruments found')
        exchanges = set([i.exchange for i in instruments])

    if args.cmd:
        LOGGER.warning(f'Will only show commands, not run')
    for exchange in exchanges:
        LOGGER.info(f'Spawn daemon feed handler for exchange {exchange}')
        instrs = [i for i in instruments if i.exchange == exchange]
        spawn_daemon(exchange, args, instrs)


def main(stop=False):
    if stop is True:
        parser = ArgumentParser(description='Stop feed handler')
        parser.add_argument('-e', '--exchanges', metavar='EXCHANGE', nargs='*')
    else:
        parser = instruments_args_parser('Start feed handler')

    parser.add_argument('--cmd',
                        action='store_true',
                        help='Only show commands')
    parser.add_argument('--stop',
                        action='store_true',
                        default=stop,
                        help='Only stop existing feed handlers')
    parser.add_argument('-n',
                        '--no-kill',
                        action='store_true',
                        help='Do not kill existing feed handlers')

    parser.add_argument('-m', '--modes', nargs='*', choices=[PUBLIC, PRIVATE])
    parser.add_argument('-C',
                        '--channels',
                        nargs='*',
                        choices=PUBLIC_CHANNELS + PRIVATE_CHANNELS)
    # parser.add_argument('--interval', help='Candle interval (in minutes)')

    args = parser.parse_args()

    if not stop and not len(sys.argv) > 1:
        parser.print_help()
        LOGGER.error(
            'Need at least one arg to prevent loading all instr exisiting in the universe'
        )
        exit(0)

    start_fh_invoke(args)

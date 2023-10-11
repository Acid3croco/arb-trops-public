import os
import time
import threading
import subprocess

from argparse import ArgumentParser
from collections import defaultdict

from redis.client import Redis
from playsound import playsound

from arb_logger.logger import get_logger
from db_handler.wrapper import DBWrapper
from arb_defines.defines import ORDER_EXCHANGE, TRADE_EXEC
from redis_manager.redis_events import OrderDBEvent, TradeExecEvent
from arb_defines.arb_dataclasses import Instrument, Order, Trade

LOGGER = get_logger('notif_server', short=True)


def notif_server(args):
    sound_file_buy = '/System/Library/Sounds/Submarine.aiff'
    sound_file_sell = '/System/Library/Sounds/Blow.aiff'
    # sound_file = 'bonjour_jack.m4a'

    db_wrapper = DBWrapper(logger=LOGGER)

    r = Redis(decode_responses=True)
    p = r.pubsub()

    name = 'arb_notification_server'
    logger = get_logger(name)

    subprocess.call(['pkill', '-f', name])

    channels = f'{TRADE_EXEC}:*'
    p.psubscribe(channels)
    logger.info(channels)

    instruments = defaultdict(Instrument)

    def get_instrument(order):
        if order.instr_id not in instruments:
            instrument = db_wrapper.get_instrument_from_id(order.instr_id)
            instruments[order.instr_id] = instrument

        order.instr = instruments[order.instr_id]

    def alert(trade):
        if trade.side == 'buy':
            sound = sound_file_buy
        if trade.side == 'sell':
            sound = sound_file_sell
        if sound:
            threading.Thread(target=playsound, args=(sound, ),
                             daemon=True).start()

    def display_notification(payload):
        message = 'new trade'
        try:
            order: Trade = TradeExecEvent.deserialize(payload)
            get_instrument(order)
            message = order.desc()
        except Exception as e:
            logger.error(e)

        cmd = f'tell application "System Events" to display notification "{message}" with title "New Trade"'
        if args.sound:
            alert(order)
        LOGGER.info(cmd)
        subprocess.call(['osascript', '-e', cmd, '&'])

    for m in p.listen():
        if m.get('type') == 'pmessage':
            display_notification(m.get('data', 'NO DATA'))
            time.sleep(0.1)


def start_notif_server(args):
    kill_cmd = f'pkill -f "arb_notification_server"'
    LOGGER.info(kill_cmd)
    os.system(kill_cmd)

    cmd = 'arb_notification_server --daemon'
    if args.sound:
        cmd += ' --sound'
    run_cmd = f'nohup {cmd} </dev/null >/dev/null 2>&1 &'
    LOGGER.info(run_cmd)
    os.system(run_cmd)


def main():
    parser = ArgumentParser('Notification server')
    parser.add_argument('-s', '--sound', action='store_true')
    parser.add_argument('--daemon', action='store_true')

    args = parser.parse_args()
    if args.daemon:
        return notif_server(args)
    start_notif_server(args)
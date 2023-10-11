import logging
import threading

from playsound import playsound
from cryptofeed.defines import BUY, SELL

from watchers.watcher_base import WatcherBase
from arb_defines.arb_dataclasses import Trade
from redis_manager.redis_events import TradeEvent
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser

import pygame

pygame.init()
pygame.mixer.init()


class TickWatcher(WatcherBase):
    log_level = logging.INFO
    log_redis_handler = False

    def __init__(self, instruments):
        super().__init__(instruments)

        self.nb_trades = {BUY: 0, SELL: 0}
        self.total_size = {BUY: 0, SELL: 0}
        self.tick_change = {BUY: 0, SELL: 0}
        self.last_trade = {BUY: None, SELL: None}

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(TradeEvent(self.instruments),
                                           self.on_trade_event)

    def on_trade_event(self, trade: Trade):
        instr = self.instruments[trade.instr_id]

        last_trade: Trade = self.last_trade[trade.side]

        if last_trade:
            tick_change = (trade.price - last_trade.price) // instr.tick_size
            same_trade = trade.time == last_trade.time

            if same_trade:
                self.nb_trades[trade.side] += 1
                self.total_size[trade.side] += trade.qty
                self.tick_change[trade.side] += tick_change

                nb_trades = self.nb_trades[trade.side]
                tick_change = self.tick_change[trade.side]
            else:
                self.nb_trades[trade.side] = 1
                self.total_size[trade.side] = trade.qty
                self.tick_change[trade.side] = tick_change

            if same_trade and tick_change:
                marg = ' ' * 3 if not trade.side == SELL else ''
                letime = trade.time.strftime('%H:%M:%S.%f')
                size = f'{self.total_size[trade.side]:.0f}'.rjust(10)
                price = f'{trade.price:.8f}'.ljust(7)
                side = trade.side.upper()

                full_str = f'{marg}{letime}   {size} @ {price}  {str(int(tick_change)).rjust(4)}  {str(int(nb_trades)).rjust(4)}'

                log = self.logger.warning if trade.side == SELL else self.logger.info
                log(full_str)
                self.alert(trade)

        self.last_trade[trade.side] = trade

    def _get_sound(self, trade: Trade):
        small_size = 100
        big_size = 2000
        if trade.notional > 0:
            return '/Users/jack/Downloads/atm.wav'
        if trade.notional < 0:
            return '/Users/jack/Downloads/elevator.wav'

    def alert(self, trade):
        sound = self._get_sound(trade)
        volume = max(trade.notional / 100000, 100) / 100
        if sound:
            threading.Thread(target=self.playsound,
                             args=(sound, volume),
                             daemon=True).start()

    def playsound(self, sound, volume):
        sound = pygame.mixer.Sound(sound)
        sound.set_volume(volume / 3)
        sound.play()


def main():
    parser = instruments_args_parser('TickWatcher')
    args = parser.parse_args()

    instruments = resolve_instruments(args)

    TickWatcher(instruments).run()


if __name__ == '__main__':
    main()

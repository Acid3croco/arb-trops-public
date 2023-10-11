import logging
import threading

from playsound import playsound

from watchers.watcher_base import WatcherBase
from arb_utils.resolver import resolve_instruments
from arb_defines.arb_dataclasses import Instrument, Trade
from arb_utils.args_parser import instruments_args_parser
from redis_manager.redis_events import LiquidationEvent, TradeEvent


class ShowTrades(WatcherBase):
    short_logger = True

    def __init__(self, instruments: list[Instrument], args) -> None:
        super().__init__(instruments)
        self.logger.setLevel(logging.INFO)

        self.args = args

        if args.trades:
            self.redis_manager.subscribe_event(TradeEvent(self.instruments),
                                               self.on_trade_event)
        if args.liquidations:
            self.redis_manager.subscribe_event(
                LiquidationEvent(self.instruments), self.on_liquidation_event)

    def on_trade_event(self, trade: Trade):
        self._leprint(trade, 'TRADE')

    def on_liquidation_event(self, trade: Trade):
        self._leprint(trade, 'LIQUIDATION')

    def _leprint(self, trade: Trade, prefix: str):
        self.logger.info(
            f'{prefix}\t{str(trade.instr).ljust(45)} {str(round(trade.qty, 6)).rjust(10)} @ {str(trade.price).ljust(10)} {str(int(trade.notional)).rjust(10)} $'
        )
        if self.args.sound:
            self.alert(trade)

    def _get_sound(self, trade):
        small_size = self.args.small_size
        big_size = self.args.big_size
        if trade.notional > big_size:
            return '/Users/jack/Trading/arb-trops-phoenix/packages/standalone_tools/standalone_tools/MDR.mp3'
        if trade.notional < -big_size:
            return '/Users/jack/Trading/arb-trops-phoenix/packages/standalone_tools/standalone_tools/MONPOTE.mp3'
        if trade.notional > small_size:
            return '/Users/jack/Trading/arb-trops-phoenix/packages/standalone_tools/standalone_tools/wa_slp.mp3'
        if trade.notional < -small_size:
            return '/Users/jack/Trading/arb-trops-phoenix/packages/standalone_tools/standalone_tools/bonjour_jack.m4a'

    def alert(self, trade):
        sound = self._get_sound(trade)
        if sound:
            threading.Thread(target=playsound, args=(sound, ),
                             daemon=True).start()


def main():
    parser = instruments_args_parser(description='Show trades.')
    parser.add_argument('--trades', action='store_true')
    parser.add_argument('--liquidations', action='store_true')
    parser.add_argument('-s', '--sound', action='store_true')
    parser.add_argument('--small-size', type=float, default=50)
    parser.add_argument('--big-size', type=float, default=1000)
    args = parser.parse_args()

    instruments = resolve_instruments(args)
    liq = ShowTrades(instruments, args)
    liq.run()

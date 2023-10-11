import time
import logging

from tabulate import tabulate
from cryptofeed.defines import *
from curses import curs_set, wrapper

from arb_defines.defines import *
from arb_logger.logger import get_logger
from arb_defines.arb_dataclasses import Instrument
from arb_utils.resolver import resolve_instruments
from redis_manager.redis_manager import RedisManager
from redis_manager.redis_wrappers import InstrumentRedis
from arb_utils.args_parser import instruments_args_parser
from redis_manager.redis_events import FundingRateEvent, OrderBookEvent, PositionEvent

LOGGER = get_logger('show_positions', short=True, level=logging.WARNING)


class ShowPositions:

    def __init__(self, instruments: list[Instrument], args) -> None:
        self.args = args
        self.redis_manager: RedisManager = RedisManager(instruments,
                                                        logger=LOGGER)

        self.last_snap = 0
        self.can_show = False

    @property
    def instruments(self) -> list[InstrumentRedis]:
        return self.redis_manager.instruments.values()

    def show(self):
        if self.args.live:
            wrapper(self._show_live)
        else:
            self._show_snap()

    def _show_snap(self):
        tot_pos = 0
        notional = 0
        _notional = 0
        tot_pnl = 0
        delta = 0

        positions = []
        header = [
            '#', 'ID', 'Instrument', 'Qty', 'Price', '$', 'Mid', '$', 'Pnl',
            'FR %'
        ]
        for instr_redis in self.instruments:
            if (instr_redis and instr_redis.position and
                (round(instr_redis.position.qty, 10) != 0 or self.args.zero)):
                notional += abs(instr_redis.position.notional)
                tot_pos += 1
                pnl = None
                mid = None
                fr = None
                if instr_redis.orderbook is not None:
                    mid = instr_redis.orderbook.mid()
                    pnl = (mid - instr_redis.position.price
                           ) * instr_redis.position.qty
                    tot_pnl += pnl
                if instr_redis.funding_rate is not None:
                    fr = instr_redis.funding_rate.predicted_rate * 100
                qty = instr_redis.position.qty
                price = instr_redis.position.price
                notio = abs(instr_redis.position.notional)
                _notio = qty * mid if mid else qty * price
                if mid and qty < 0:
                    _notio = (price * qty) + ((price - mid) * -qty)
                delta += _notio
                _notional += abs(_notio)

                positions.append([
                    instr_redis.id,
                    instr_redis,
                    round(qty, 8) if qty else qty,
                    round(price, 8) if price else price,
                    round(notio, 3) if notio else notio,
                    round(mid, 8) if mid else mid,
                    round(_notio, 3) if _notio else _notio,
                    round(pnl, 3) if pnl else 0,
                    round(fr, 3) if fr else fr,
                ])

        table = [
            ['TOT POS', tot_pos],
            ['TOT PNL', round(tot_pnl, 3)],
            ['NOTIONAL', round(notional, 9)],
            ['CURR NOT', round(_notional, 9)],
            ['DELTA', round(delta, 9)],
        ]

        if positions:
            positions.sort(key=lambda x: x[1].instr_code.split(':')[1],
                           reverse=True)
            positions.sort(key=lambda x: x[7], reverse=True)
            positions = [[i] + p for i, p in enumerate(positions, 1)]

            if self.args.live is False:
                print(tabulate(positions, headers=header), end='\n\n')
                print(tabulate(table))
            else:
                rows, cols = self.stdout.getmaxyx()
                max_len = min(70, rows - 15)
                mid_len = int(max_len / 2)
                if len(positions) > max_len:
                    positions = positions[:mid_len] + [['...'] * len(positions[0])
                                                    ] + positions[-mid_len:]
                self.stdout.clear()
                self.stdout.addstr(0, 0, tabulate(positions, headers=header))
                self.stdout.addstr(len(positions) + 4, 0, tabulate(table))
                # print(tabulate(table))
                self.stdout.refresh()
        else:
            if self.args.live is False:
                LOGGER.warning('No positions found')
            else:
                self.stdout.clear()
                self.stdout.addstr(0, 0, 'No positions found')
                self.stdout.refresh()

    def _subscribe_to_exchanges(self):
        instruments = self.redis_manager.instruments.values()
        self.redis_manager.subscribe_event(PositionEvent(instruments),
                                           self._on_position_event)
        self.redis_manager.subscribe_event(OrderBookEvent(instruments),
                                           self._on_orderbook_event)
        self.redis_manager.subscribe_event(FundingRateEvent(instruments),
                                           self._on_funding_rate_event)

        if self.args.live:
            self.redis_manager.heartbeat_event(1, self._show_snap)

    def _on_position_event(self, position):
        self._refresh_live()

    def _on_funding_rate_event(self, funding_rate):
        self._refresh_live()

    def _on_orderbook_event(self, position):
        self._refresh_live()

    def _show_live(self, stdout):
        curs_set(0)
        stdout.nodelay(True)
        self.stdout = stdout

        self._subscribe_to_exchanges()
        self._refresh_live()
        self.redis_manager.run()

    def _heartbeat_show(self):
        if self.can_show:
            self._show_snap()

    def _refresh_live(self):
        self.can_show = True
        return


def main():
    parser = instruments_args_parser('Show positions on instruments')
    parser.add_argument('-s',
                        '--sort',
                        type=str,
                        choices=['instr', 'rate', 'predicted'],
                        default='predicted')
    parser.add_argument('-z',
                        '--zero',
                        action='store_true',
                        help='show null positions')
    parser.add_argument('-l', '--live', action='store_true')

    args = parser.parse_args()

    instruments = resolve_instruments(args)
    show_positions = ShowPositions(instruments, args)
    show_positions.show()


if __name__ == '__main__':
    main()

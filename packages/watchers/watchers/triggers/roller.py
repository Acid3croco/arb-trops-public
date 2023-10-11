import time

from threading import Thread
from datetime import datetime
from argparse import ArgumentParser
from datetime import datetime, timezone

from cryptofeed.defines import MARKET

from arb_defines.arb_dataclasses import Order
from arb_defines.event_types import EventTypes
from redis_manager.redis_events import OrderBookEvent, PositionEvent
from watchers.executor_base import ExecutorBase
from redis_manager.redis_wrappers import InstrumentRedis
from arb_utils.resolver import resolve_instruments_from_ids


class Roller(ExecutorBase):

    def __init__(self, instrument, qty) -> None:
        self.qty = qty or None
        self._instrument = instrument
        super().__init__([instrument])
        self.ping = False
        self.pong = False
        self.hour = None

    @property
    def instrument(self) -> InstrumentRedis:
        return self.redis_manager.get_instrument(self._instrument)

    def _run_thread(self):
        self.redis_manager.subscribe_event(PositionEvent(self.instrument))
        self.redis_manager.subscribe_event(OrderBookEvent(self.instrument))
        th = Thread(target=self.redis_manager.run, daemon=True)
        th.start()

    def run(self):
        self._run_thread()
        self.logger.info(f'Roller started for {self.instrument}')

        while self.ping is False or self.pong is False:
            if (datetime.now(tz=timezone.utc).hour in [7, 15, 23]
                    or self.ping is True):
                self.try_roll()
            time.sleep(0.05)

        self.logger.info(f'Roller done, hope it went well')
        exit(0)

    def try_roll(self):
        now = datetime.now()

        order = None
        if self.ping is False and now.minute >= 59 and now.second >= 58:
            self.logger.info(f'PING {self.qty} {self.instrument}')
            self.ping = True
            self.pong = False
            self.hour = now.hour
            order = self.build_order('ping')
        elif self.ping is True and self.pong is False and now.hour != self.hour:
            time.sleep(1)
            self.logger.info(f'PONG {-self.qty} {self.instrument}')
            self.pong = True
            self.ping = False
            order = self.build_order('pong')

        if order is not None:
            self.send_order(order, checked=True)

    def build_order(self, side):
        qty = self.qty if side == 'ping' else -self.qty
        price = self.instrument.orderbook.mid()

        return Order(instr=self.instrument,
                     price=price,
                     qty=qty,
                     order_type=MARKET,
                     event_type=EventTypes.ROLLER)


def main():
    parser = ArgumentParser(
        description='roll a position at the end of the hour')
    parser.add_argument('-q', '--qty', type=float, required=True)
    parser.add_argument('-i', '--instr-id', type=int, required=True)

    args = parser.parse_args()
    instrument = resolve_instruments_from_ids([args.instr_id])[0]

    roller = Roller(instrument, args.qty)
    roller.run()


if __name__ == '__main__':
    main()
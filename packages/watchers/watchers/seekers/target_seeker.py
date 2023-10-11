import os
import json
import time

from pathlib import Path
from datetime import datetime, timedelta

from watchdog.observers import Observer
from cryptofeed.defines import LIMIT, MARKET, PERPETUAL
from watchdog.events import FileSystemEventHandler

from db_handler.wrapper import DBWrapper
from watchers.seeker_base import SeekerBase
from arb_defines.event_types import EventTypes
from arb_defines.arb_dataclasses import Order, Position, Trade
from redis_manager.redis_wrappers import InstrumentRedis

TARGET_FILENAME = os.path.expandvars('$ARB_MODELS_PATH/targets.json')

from typing import TypedDict


class TargetData(TypedDict):
    timestamp: float
    targets: dict[str, int]


class TargetSeekerConfig:
    size = 10.0


class TargetFileHandler(FileSystemEventHandler):

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self.callback()


class TargetSeeker(SeekerBase):
    short_logger = True

    def __init__(self) -> None:
        self.period_min = 60

        target_data = self.get_targets()
        if not target_data:
            raise ValueError("No targets found")

        instruments = self.get_instrs_from_target_data(target_data)

        super().__init__(instruments)

        _target_instr = list(target_data['targets'].keys())

        # Find mismatches in instruments
        mismatched_instruments = [
            instrument for instrument in instruments
            if instrument.base not in _target_instr
        ]
        if mismatched_instruments:
            self.logger.error(
                f"Mismatched Instruments: {mismatched_instruments}")
            raise ValueError(
                f"Mismatched Instruments: {mismatched_instruments}")

        # Find mismatches in bases
        mismatched_bases = [
            base for base in _target_instr
            if base not in [instrument.base for instrument in instruments]
        ]
        if mismatched_bases:
            self.logger.error("Mismatched Bases:", mismatched_bases)
            raise ValueError("Mismatched Bases")

        self.config = TargetSeekerConfig()
        self.last_timestamp = 0

        self.logger.info(f'found {len(instruments)} instruments')
        self._instruments = {
            instr.base: instr
            for instr in self.instruments.values()
        }
        self.ob_ready = False

    def _wait_all_orderbooks(self):
        while True:
            ob = [(instr.base, instr.orderbook)
                  for instr in self.instruments.values()]
            if all([o for _, o in ob]):
                break
            self.logger.info(
                f'Waiting for orderbooks - {[i for i, o in ob if not o]}')
            time.sleep(1)

    def _reset_positions(self):
        self.logger.info('RESET POSITIONS')
        for instr in self.instruments.values():
            self.logger.info(f'reset {instr.base}')
            instr.set_position(Position(instr.id))
            self.logger.info(f'position: {instr.position}')

    @staticmethod
    def get_instrs_from_target_data(target_data):
        exchange = 'BYBIT'
        quote = 'USDT'
        bases = [k for k in target_data['targets'].keys()]
        instr_type = PERPETUAL

        return DBWrapper().get_instruments(bases,
                                           quote,
                                           instr_type=instr_type,
                                           exchange_name=exchange)

    @staticmethod
    def get_targets() -> TargetData:
        for _ in range(5):
            try:
                return json.load(open(TARGET_FILENAME, 'r'))
            except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
                print(f'Error: {e}')
                time.sleep(1)

    def subscribe_to_events(self):
        # self.redis_manager.heartbeat_event(1, self.flush_positions)
        # self.redis_manager.heartbeat_event(60, self.update_positions)
        # use this to create blocking file watcher
        self.redis_manager.heartbeat_event(1, self.watch_target)
        super().subscribe_to_events()

    def flush_positions(self):
        self._reset_positions()
        exit()

    def _wait_all_orderbooks(self):
        while True:
            ob = [(instr.base, instr.orderbook)
                  for instr in self.instruments.values()]
            if all([o for _, o in ob]):
                break

            missing_ob = [i for i, o in ob if not o]
            self.logger.info(
                f'Waiting for {len(missing_ob)} orderbooks - {missing_ob}')

            time.sleep(1)

    def update_positions(self):
        # wait for target file to be full written - maybe useless
        time.sleep(0.1)

        if not self.ob_ready:
            self._wait_all_orderbooks()
            self.ob_ready = True
            return

        target_data = self.get_targets()

        curr_timestamp = (datetime.now().replace(second=0, microsecond=0) -
                          timedelta(minutes=self.period_min)).timestamp()

        if target_data['timestamp'] < curr_timestamp:
            self.logger.warning(f"Target data is out of date")
            return
        if target_data['timestamp'] == self.last_timestamp:
            # self.logger.debug(f"Target data is the same, skipping")
            return

        self.logger.debug(f"targets: {target_data}")

        orders: list[Order] = []
        for instr_name, target in target_data['targets'].items():
            instr = self._instruments.get(instr_name)
            if not instr:
                self.logger.warning(f'No instrument for {instr_name}')
                continue

            curr_pos_qty = instr.position.qty
            curr_pos_notio = round(instr.position.notional)

            qty = 0
            price = instr.orderbook.mid()
            if target == 0 and curr_pos_notio != 0:
                # flat pos
                qty = -curr_pos_qty
            elif target != 0 and curr_pos_notio == 0:
                # enter pos
                qty = target * self.config.size / price
            elif ((target > 0 and curr_pos_notio < 0)
                  or (target < 0 and curr_pos_notio > 0)):
                # reverse pos
                qty = target * self.config.size / price - curr_pos_qty

            if qty > 0:
                price, _ = instr.orderbook.ask()
            elif qty < 0:
                price, _ = instr.orderbook.bid()

            if qty != 0:
                order = Order(instr=instr,
                              price=price,
                              qty=qty,
                              order_type=MARKET,
                              event_type=EventTypes.TARGET_SEEKER)
                orders.append(order)

        tot_cost = 0
        tot_cost_abs = 0
        for order in orders:
            self.logger.info(f'{order}, {order.r_cost:.2f}$')
            tot_cost += order.r_cost
            tot_cost_abs += abs(order.r_cost)

        self.logger.info(
            f'nb orders: {len(orders)}, delta cost: {tot_cost:.2f}$, total: {tot_cost_abs:.2f}$'
        )

        _orders = orders.copy()
        #! ATTENTION - USE TO SIMULATE ORDER EXECUTION
        for order in _orders:
            instr = order.instr
            trade = Trade(id='0',
                          time=datetime.now(),
                          instr=instr,
                          price=order.r_price,
                          qty=order.r_qty,
                          fee=0,
                          order_type=order.order_type,
                          exchange_order_id='0')

            instr_pos = instr.position or Position(instr_id=instr.id)
            trade_pos = Position.from_trade(trade)
            new_position = instr_pos + trade_pos
            instr.set_position(new_position)

            self.logger.info(
                f'POSITION - {instr.instr_code} {instr.position.qty}@{instr.position.price}'
            )

        self.send_orders(orders, checked=True)

        self.last_timestamp = target_data['timestamp']

        self.redis_manager.orders_manager.delete_all_redis_orders()
        self.redis_manager.orders_manager.reload_all_orders()

    def watch_target(self):
        self._observer = Observer()
        event_handler = TargetFileHandler(self.update_positions)
        self._observer.schedule(event_handler,
                                str(Path(TARGET_FILENAME).parent),
                                recursive=False)
        self._observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self._observer.stop()

        self._observer.join()


def main():
    TargetSeeker().run()

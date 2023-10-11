import math

from dataclasses import dataclass

from cryptofeed.defines import LIMIT

from arb_defines.arb_dataclasses import Order
from arb_defines.event_types import EventTypes
from redis_manager.redis_wrappers import InstrumentRedis
from watchers.seeker_base import SeekerBase, SeekerClientBase, seeker_main
from watchers.sentinels.pair_zscore_sentinel import PairZscoreSentinelClient


@dataclass
class PairSeekerConfig:
    size: float = 100.0


class PairSeeker(SeekerBase):
    short_logger = True

    def __init__(self, instruments) -> None:
        if len(instruments) != 2:
            raise ValueError("PairSeeker only works with 2 instruments")

        super().__init__(instruments)
        self.config = PairSeekerConfig()

        self.pair_zscore_sentinel = PairZscoreSentinelClient(
            self.redis_manager, instruments)

    def subscribe_to_events(self):
        self.redis_manager.heartbeat_event(60 * 60,
                                           self.update,
                                           is_pile=True,
                                           offset=2)
        super().subscribe_to_events()

    def _pre_checks(self):
        self.logger.debug(f"{self.__class__.__name__} pre checks")
        if not self.pair_zscore_sentinel.values:
            self.logger.warning('Not enough data to update')
            return False

    def update(self):
        if self._pre_checks() is False:
            self.logger.debug(f"{self.__class__.__name__} pre checks failed")
            return
        self.build_orders()

    def _get_qties(self, zscore, beta, instr1, instr2):
        coef = -math.atan(zscore**3)
        self.logger.debug(f'coef: {coef}')

        qty1 = self.config.size / instr1.orderbook.mid() * coef
        qty2 = self.config.size / instr2.orderbook.mid() * -coef

        return qty1, qty2

    def _adjust_orders(self, orders):
        self.logger.info(f"{self.__class__.__name__} adjust orders")
        return orders

    def _build_order(self, instr: InstrumentRedis, qty: float):
        price, _ = instr.orderbook.bid() if qty > 0 else instr.orderbook.ask()
        return Order(instr=instr,
                     price=price,
                     qty=qty,
                     order_type=LIMIT,
                     event_type=EventTypes.PAIR_SEEKER)

    def build_orders(self):
        self.logger.info(f"{self.__class__.__name__} build orders")
        beta, zscore = self.pair_zscore_sentinel.values[-1]
        self.logger.debug(f'zscore: {zscore}, beta: {beta}')
        if abs(zscore) < 0.1:
            self.logger.warning(f'zscore is {zscore}, not enough to trade')
            return

        instr1, instr2 = list(self.instruments.values())
        self.logger.debug(f'instr1: {instr1}, instr2: {instr2}')

        qty1, qty2 = self._get_qties(zscore, beta, instr1, instr2)
        self.logger.debug(f'qty1: {qty1}, qty2: {qty2}')
        if qty1 == 0 or qty2 == 0:
            self.logger.warning(
                f'qty1: {qty1} or qty2: {qty2} is 0, not enough to trade')
            return

        order_buy = self._build_order(instr1, qty1)
        order_sell = self._build_order(instr2, qty2)
        self.logger.info(order_buy)
        self.logger.info(order_sell)
        self.logger.info(f'{order_buy.cost} {order_sell.cost}')
        self.send_orders([order_buy, order_sell], checked=True)


class PairSeekerClient(SeekerClientBase):
    linked_class = PairSeeker


def main():
    seeker_main(PairSeekerClient)

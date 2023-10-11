import re
import logging

from arb_logger.logger import get_logger
from redis_manager.redis_manager import RedisManager
from redis_manager.redis_wrappers import ExchangeRedis, InstrumentRedis


class WatcherBase:
    """Base class for watchers."""
    has_orders = False
    has_status = False
    short_logger = False
    sorted_hash = True
    log_redis_handler = True
    log_level = logging.DEBUG
    log_name = None

    def __init__(self, instruments=[]) -> None:
        self.logger = get_logger(self.log_name or self.__class__.__name__,
                                 short=self.short_logger,
                                 level=self.log_level,
                                 redis_handler=self.log_redis_handler)

        if not instruments:
            # a watcher could psubscribe? -> yes you can
            self.logger.warning(f'Not instrument given, just fyi')

        self.id = self._build_name(self.__class__.__name__, instruments)

        self.redis_manager: RedisManager = RedisManager(
            instruments,
            has_orders=self.has_orders,
            has_status=self.has_status,
            logger=self.logger)

        if hasattr(self, 'client_class'):
            self.client_id = self._build_name(self.client_class,
                                              self.instruments)

    @property
    def exchanges(self) -> dict[int, ExchangeRedis]:
        return self.redis_manager.exchanges

    @property
    def instruments(self) -> dict[int, InstrumentRedis]:
        return self.redis_manager.instruments

    @staticmethod
    def _build_name(class_name, instruments) -> str:
        # care here if we sort instruments we may have conflict
        # with 2 differents running with inversed instruments
        hashes = sorted([str(hash(i)) for i in instruments])
        hashes = '_'.join(hashes)
        base_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        return f'{base_name}:{hashes}'

    def subscribe_to_events(self):
        pass

    def run(self):
        self.subscribe_to_events()
        self.redis_manager.run()

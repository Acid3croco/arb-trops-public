import simplejson as json

from datetime import datetime, timezone

from logging import Logger
from dataclasses import dataclass
from collections import defaultdict, ChainMap

from arb_defines.defines import CANCEL
from redis_manager.redis_wrappers import ObjectRedis
from arb_defines.arb_dataclasses import Exchange, Instrument, Order
from redis_manager.redis_events import CancelAllOrdersEvent, CancelAllOrdersExchangeEvent, CancelAllOrdersInstrEvent, CancelOrderEvent, OrderEvent, OrderExchangeEvent


@dataclass(kw_only=True)
class InstrOrdersManager(ObjectRedis):
    """DONT INSTANCIATE THIS CLASS DIRECTLY, USE ORDERS_MANAGER"""
    instrument: Instrument
    logger: Logger

    def __post_init__(self):
        self.logger.info(f'Load instr orders managers for {self.instrument}')
        self._orders: dict[str, Order] = defaultdict(Order)
        self.load_orders()

    @property
    def orders(self):
        return self._orders

    def load_orders(self):
        orders = self.redis_instance.hgetall(self.instrument.orders_hash)
        self._orders: dict[str, Order] = {
            k: Order(**json.loads(v))
            for k, v in orders.items()
        }

    def get_order(self, order_id) -> Order:
        return self._orders.get(order_id)

    def _store_local(self, order: Order) -> Order:
        if order.id in self._orders:
            # get latest valid order
            self.logger.debug(
                f'Order {order} already exists, matching with known order {self._orders[str(order.id)]}'
            )
            order = order | self._orders[str(order.id)]

        if order.is_final:
            self.logger.debug(f'Order {order} is final, deleting from local')
            self._delete_order(order)
        else:
            self.logger.debug(f'Order {order} is not final, storing in local')
            self._orders[str(order.id)] = order

        return order

    def _delete_order(self, order: str | Order):
        order_id = order
        if isinstance(order, Order):
            order_id = order.id
        self.logger.debug(f'Deleting order {order_id} from local')
        if order_id in self._orders:
            self.logger.debug(f'Order {order_id} found, deleting')
            del self._orders[str(order_id)]
        else:
            self.logger.warning(f'Order {order} not found')
            self.logger.debug(self._orders)

    def _store_redis(self, order: Order):
        if not order:
            return
        if order.is_final:
            self.logger.debug(f'Order {order} is final, deleting from redis')
            return self._delete_redis(order)

        self.logger.debug(f'Order {order} is not final, storing in redis')
        self.redis_instance.hset(self.instrument.orders_hash, str(order.id),
                                 OrderEvent.serialize(order))

    def _delete_redis(self, order: str | Order):
        order_id = order
        if isinstance(order, Order):
            order_id = order.id

        self.logger.debug(f'Deleting order {order_id} from redis')
        try:
            self.redis_instance.hdel(self.instrument.orders_hash,
                                     str(order_id))
            self.logger.debug(f'Order {order_id} deleted from redis')
        except Exception as e:
            self.logger.error(
                f'Error deleting order {order_id} from redis: {e}')

    def delete_all_redis_orders(self):
        self.redis_instance.delete(self.instrument.orders_hash)


@dataclass(kw_only=True)
class ExchangeOrdersManager(ObjectRedis):
    """DONT INSTANCIATE THIS CLASS DIRECTLY, USE ORDERS_MANAGER"""
    exchange: Exchange
    instruments: list[Instrument]
    logger: Logger

    def __post_init__(self):
        self.logger.info(f'Load exchange orders managers for {self.exchange}')

        self.instr_orders_managers: dict[
            int, InstrOrdersManager] = defaultdict(InstrOrdersManager)
        self.load_managers()

    @property
    def orders(self):
        return ChainMap(*[
            manager.orders for manager in self.instr_orders_managers.values()
        ])

    def load_managers(self):
        for instr in self.instruments:
            self.add_instrument_manager(instr)

    def add_instrument_manager(self, instr: Instrument):
        manager = InstrOrdersManager(redis_handler=self.redis_handler,
                                     instrument=instr,
                                     logger=self.logger)
        self.instr_orders_managers[instr.id] = manager

    def _store_local(self, order: Order):
        return self.instr_orders_managers[order.instr_id]._store_local(order)

    def _store_redis(self, order: Order):
        return self.instr_orders_managers[order.instr_id]._store_redis(order)

    def _delete_order(self, order: int | Order):
        return self.instr_orders_managers[order.instr_id]._delete_order(order)

    def delete_all_redis_orders(self):
        for manager in self.instr_orders_managers.values():
            manager.delete_all_redis_orders()


@dataclass(kw_only=True)
class OrdersManager(ObjectRedis):
    #! Order class now have an instrument
    #! so we can update this class to take advantage of this

    instruments: list[Instrument]
    logger: Logger

    def __post_init__(self):
        self.exchange_orders_managers: dict[
            int, ExchangeOrdersManager] = defaultdict(ExchangeOrdersManager)
        self.load_managers()
        # self._orders: dict[str, Order] = self.all_orders

    @property
    def orders(self) -> dict[str, Order]:
        """ Return all orders managed by this manager """
        return self.all_orders
        # it should be usable but not tested after fix
        return self._orders

    @property
    def all_orders(self) -> dict[str, Order]:
        """
        Return all orders from the sub managers
        This looks costly hence it is cached using _orders
        Only use it when you need to refresh the cache
        """
        return ChainMap(*[
            manager.orders
            for manager in self.exchange_orders_managers.values()
        ])
        return self._orders

    def reload_all_orders(self, exchange_id=None):
        self.logger.info(
            f'Reloading all orders for {exchange_id if exchange_id else "all exchanges"}'
        )
        for manager in self.exchange_orders_managers.values():
            if exchange_id is None or manager.exchange.id == exchange_id:
                for mana in manager.instr_orders_managers.values():
                    mana.load_orders()
        # self.all_orders

    def get_order(self, order_id):
        return self._orders.get(order_id)

    def get_orders(self, key):
        if isinstance(key, Instrument):
            return self.exchange_orders_managers[
                key.exchange.id].instr_orders_managers[key.id].orders

    def cancel_order(self, order: Order):
        order.order_status = CANCEL
        order.time_cancel = datetime.now(tz=timezone.utc)
        self._publish_order(CancelOrderEvent, order)

    def cancel_all_orders_instr(self, instr: Instrument):
        self.redis_handler.publish_event(CancelAllOrdersInstrEvent, instr)

    def cancel_all_orders_exchange(self, exchange: Exchange):
        self.redis_handler.publish_event(CancelAllOrdersExchangeEvent,
                                         exchange)

    def cancel_all_orders(self):
        self.redis_handler.publish_event(CancelAllOrdersEvent)

    def delete_all_redis_orders(self):
        for manager in self.exchange_orders_managers.values():
            manager.delete_all_redis_orders()

    def load_managers(self):
        for exchange in set([i.exchange for i in self.instruments]):
            self.add_exchange_manager(exchange)

    def add_exchange_manager(self, exchange: Exchange):
        exch_instr = [i for i in self.instruments if i.exchange == exchange]
        manager = ExchangeOrdersManager(redis_handler=self.redis_handler,
                                        exchange=exchange,
                                        instruments=exch_instr,
                                        logger=self.logger)
        self.exchange_orders_managers[exchange.id] = manager

    def add_instrument_manager(self, instr: Instrument):
        self.instruments.append(instr)
        exch_manager = self.exchange_orders_managers.get(instr.exchange.id)
        if exch_manager is None:
            self.add_exchange_manager(instr.exchange)
        else:
            exch_manager.add_instrument_manager(instr)

    def received_order(self, order: Order):
        self.logger.info(f'Received order {order}')
        self.handler_order(order, OrderEvent)

    def fire_order(self, order: Order):
        self.logger.info(f'Fire order {order}')
        self.handler_order(order, OrderExchangeEvent)

    def handler_order(self, order: Order, event=None):
        self.logger.debug(f'Handler order: {order}, event: {event}')
        order = self._store_local(order)
        self.logger.debug(f'Kepts order: {order}')

        if event and order:
            self._publish_order(event, order)
            self._store_redis(order)

    def _store_local(self, order: Order):
        return self.exchange_orders_managers[order.exchange_id]._store_local(
            order)
        # if order.is_final:
        #     del self._orders[str(order.id)]
        # else:
        #     self._orders[str(order.id)] = order
        return order

    def _publish_order(self, event, order: Order):
        self.logger.debug(f'Publish order: {order}, event: {event}')
        self.redis_handler.publish_event(event, order)

    def _store_redis(self, order: Order):
        self.logger.debug(f'Store order: {order}')
        self.exchange_orders_managers[order.exchange_id]._store_redis(order)

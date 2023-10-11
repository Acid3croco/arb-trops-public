import os
import yaml
import atexit
import asyncio
import pathlib
import traceback

from datetime import datetime, timezone

from unsync import unsync
from cryptofeed.defines import *
from db_handler.wrapper import DBWrapper
# from ccxt.base.exchange import Exchange as ExchangeCcxt
from ccxt.async_support.base.exchange import Exchange as ExchangeCcxt

from arb_defines.defines import *
from arb_logger.logger import get_logger
from arb_defines.status import StatusEnum
from exchange_api.base_fetcher import BaseFetcher
from redis_manager.redis_manager import RedisManager
from redis_manager.redis_wrappers import ExchangeRedis
from arb_defines.arb_dataclasses import Balance, ExchangeApiPayload, Instrument, Order, Position, StrategyInfo
from redis_manager.redis_events import BalanceEvent, CancelAllOrdersEvent, CancelAllOrdersExchangeEvent, CancelAllOrdersInstrEvent, CancelOrderEvent, ExchangeApiEvent, OrderDBEvent, OrderExchangeEvent, PositionEvent, StrategyInfoDBEvent


class ExchangeAPI:
    """
    WHEN INIT
        GET BALANCES = PUT IN REDIS + DB - NOTIFY IF DISCREPENCY?
        GET POSITIONS = PUT IN REDIS + DB - NOTIFY IF DISCREPENCY?
        GET ORDERS = PUT IN REDIS + DB - NOTIFY IF DISCREPENCY? dont put orders in exchange struct, favorize Hash order_id

        THEN STATUS -> UP
    """

    feed_name = None
    fetcher = BaseFetcher

    def __init__(self,
                 instruments: list[Instrument],
                 exchange_ccxt: ExchangeCcxt,
                 fetch_only: bool = False):
        self.logger = get_logger(self.__class__.__name__, short=True)
        if not self.feed_name:
            self.logger.error('feed_name not set')

        self._exchange = DBWrapper(logger=self.logger).get_exchange(
            feed_name=self.feed_name)

        self.redis_manager: RedisManager = RedisManager(instruments,
                                                        has_orders=True,
                                                        logger=self.logger)

        self._instruments: list[Instrument] = instruments
        self.exchange_api: ExchangeCcxt = exchange_ccxt(self._load_config())

        self.activate_trading = os.getenv(ACTIVATE_TRADING, '0') == '1'
        self.logger.info(f'{ACTIVATE_TRADING}: {self.activate_trading}')

        self.code_mapping: dict[str, int] = {}
        self.instr_id_mapping: dict[int, Instrument] = {}
        for instr in instruments:
            self.code_mapping[instr.exchange_code] = instr.id
            self.instr_id_mapping[instr.id] = instr

        self.fetcher = self.fetcher(self._exchange, self.exchange_api,
                                    self.code_mapping, self.instr_id_mapping,
                                    self.logger)

        self.fetch_only = fetch_only
        if not fetch_only:
            self._load_exchange_data()
        else:
            self.logger.info('Fetch only mode')

    def disconnect(self):
        self.logger.info(f'Stopping exchange api {self.exchange}')
        for exchange in self.redis_manager.exchanges.values():
            exchange.set_status(api=StatusEnum.UNAVAILABLE)
        for instrument in self.redis_manager.instruments.values():
            instrument.set_status(api=StatusEnum.UNAVAILABLE)
        # binance requires to release all resources with an explicit call to the .close() coroutine.
        # If you are using the exchange instance with async coroutines, add exchange.close() to your code
        # into a place when you're done with the exchange and don't need the exchange instance anymore
        # (at the end of your async coroutine).
        # await self.exchange_api.close()
        # this is not working and doesnt send the status
        self.logger.info(f'Stopped exchange api {self.exchange}')

    @property
    def exchange(self) -> ExchangeRedis:
        return self.redis_manager.get_exchange(self._exchange.id)

    def _get_exchange_yaml(self, full_yaml):
        return full_yaml.get(self.exchange.feed_name.lower())

    def _overload_exchange_config(self, exchange_config):
        exchange_config['options'] = {}

    def _load_config(self, ):
        dirname = os.environ.get('ARB_TROPS_CONFIG_KEYS')
        config = pathlib.Path(dirname, 'config_exchanges.yaml')
        with open(config, "r") as stream:
            try:
                full_yaml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.logger.error(exc)

        exchange_yaml = self._get_exchange_yaml(full_yaml)
        if not exchange_yaml:
            self.logger.error(
                f'Exchange {self.exchange.feed_name} not found in config, exiting'
            )
            self.exchange.set_status(EXCHANGE_STATUS_UNAVAILABLE)
            exit(0)

        exchange_config = {
            'enableRateLimit': True,
            'apiKey': exchange_yaml.get('key_id'),
            'secret': exchange_yaml.get('key_secret'),
        }

        self._overload_exchange_config(exchange_config)
        exchange_config['options'][
            'warnOnFetchOpenOrdersWithoutSymbol'] = False
        return exchange_config

    @unsync
    async def _load_exchange_data(self):
        self.logger.info('Loading exchange data')
        await self.exchange_api.load_markets()
        await asyncio.gather(self._load_exchange_balances(),
                             self._load_exchange_positions(),
                             self._load_exchange_orders())
        payload = ExchangeApiPayload(self.exchange.id, 'reload_all_orders')
        self.redis_manager.publish_event(ExchangeApiEvent, payload)
        self.logger.info('Exchange data loaded')

    @unsync
    async def _load_exchange_balances(self):
        self.logger.debug('load balances')
        balances: list[Balance] = await self.fetcher.fetch_balance()

        for balance in balances:
            self.logger.info(balance)
            self.exchange.set_balance(balance)

        self.logger.debug('flush others redis balances')
        self.exchange.delete_all_redis_balances(excludes=balances)

    @unsync
    async def _load_exchange_positions(self):
        self.logger.debug('load positions')
        positions: list[Position] = await self.fetcher.fetch_positions()

        for position in positions:
            # if position.instr_id in self.instr_id_mapping:
            self.logger.info(position)
            # self.set_position(position)
            self.redis_manager.get_instrument(
                position.instr_id).set_position(position)

        #! not usefull bc exchange positions are not used
        #! need to work on how to flush positions without akward code
        # self.logger.debug('flush all redis positions')
        # self.exchange.delete_all_redis_positions(excludes=positions)
        # for instrument in self.redis_manager.instruments.values():
        #     instrument.delete_position(excludes=positions)

    @unsync
    async def _load_exchange_orders(self):
        self.logger.debug('flush all redis orders')
        self.redis_manager.orders_manager.delete_all_redis_orders()

        self.logger.debug('load orders')
        orders: list[Order] = await self.fetcher.fetch_orders()

        self.logger.info(f'Loaded {len(orders)} orders')
        for order in orders:
            self.redis_manager.orders_manager.received_order(order)

    def run(self):
        if self.fetch_only:
            raise Exception('Fetch only mode, cannot run')

        self.logger.info(
            f'{self.exchange} API READY, trading {self.activate_trading}')

        self.redis_manager.subscribe_event(ExchangeApiEvent(self._exchange),
                                           self.on_exchange_api_event)
        self.redis_manager.subscribe_event(BalanceEvent(self._exchange))
        self.redis_manager.subscribe_event(PositionEvent(self._instruments))
        self.redis_manager.subscribe_event(OrderExchangeEvent(self._exchange),
                                           self.on_order_exchange_event)

        self.redis_manager.subscribe_event(CancelAllOrdersEvent(),
                                           self.on_cancel_all_orders_event)
        self.redis_manager.subscribe_event(
            CancelAllOrdersExchangeEvent(self._exchange),
            self.on_cancel_all_orders_event)
        self.redis_manager.subscribe_event(
            CancelAllOrdersInstrEvent(self._exchange),
            self.on_cancel_all_orders_instr_event)
        self.redis_manager.subscribe_event(CancelOrderEvent(self._exchange),
                                           self.on_cancel_order_event)

        for instr in self.redis_manager.instruments.values():
            instr.set_status(api=StatusEnum.UP)
        self.exchange.set_status(api=StatusEnum.UP)
        self.redis_manager.run()

    def on_exchange_api_event(self, payload: ExchangeApiPayload):
        self.logger.debug(f'on_exchange_api_event {payload}')
        if payload.action == 'reload_data':
            self._load_exchange_data()

    # TODO: @unsync async def xx() - removed to see exceptions - need to find a way to catch then even in async
    @unsync
    async def on_order_exchange_event(self, order: Order):
        order.instr = self.redis_manager.get_instrument(order)

        try:
            self.logger.info(order)

            res_from_exchange = None
            if self.activate_trading:
                res_from_exchange = await self._send_order_to_exchange(order)
        except Exception as e:
            order.order_status = REJECTED
            order.time_rejected_mkt = datetime.now(tz=timezone.utc)
            self.logger.error(f'cannot send {order}')
            self.logger.error(e)
            self.logger.error(traceback.format_exc())
            self.redis_manager.orders_manager.handler_order(order)

        try:
            if self.activate_trading:
                self._populate_order_fields_from_exchange(
                    order, res_from_exchange)
            else:
                self._populate_order_fields_from_exchange_simulate(order)
        except Exception as e:
            order.order_status = UNKNOWN
            self.logger.error(f'cannot parse {order}')
            self.logger.error(e)
            self.logger.error(traceback.format_exc())
            self.redis_manager.orders_manager.handler_order(order)

        # if exception, order can be corrupted to insert in DB?
        # no i dont think so - maybe if the order didnt passed correctly throught the redis but highly doubt
        self._save_order_db(order)

    def on_cancel_all_orders_event(self, payload: dict = None):
        if payload:
            self.logger.info(f'cancel all orders for exchange {self.exchange}')
        else:
            self.logger.info('cancel all orders')

        for instr in self.redis_manager.instruments.values():
            self.on_cancel_all_orders_instr_event(instr)

    @unsync
    async def on_cancel_all_orders_instr_event(self, payload: dict):
        instr = self.redis_manager.get_instrument(payload['instr_id'])

        self.logger.info(f'cancel all orders for {instr}')
        try:
            res: list = await self.exchange_api.cancel_all_orders(
                instr.exchange_code)
        except Exception as e:
            res = e
            self.logger.error(e)
        self.logger.debug(f'cancel all orders for {instr} result: {res}')

    @unsync
    async def on_cancel_order_event(self, order: Order):
        self.logger.info(f'cancel order {order}')
        try:
            eoi = self._get_exchange_order_id(order)
            instr = self.instr_id_mapping.get(order.instr_id)
            res = await self.exchange_api.cancel_order(eoi,
                                                       instr.exchange_code)
            # res = 'Order queued for cancellation' or Exception
        except Exception as e:
            res = e
            self.logger.error(e)
            order.order_status = CANCEL_REJECTED
            order.time_rejected_mkt = datetime.now(tz=timezone.utc)
            self.redis_manager.orders_manager.handler_order(order)
        self.logger.debug(f'cancel order {order} result: {res}')

    def _snap_strategy_info(self, order: Order):
        orderbook = order.instr.get_orderbook()
        strategy_info = StrategyInfo(order_id=order.id,
                                     event_key=order.event_key,
                                     payload=orderbook)
        self.redis_manager.publish_event(StrategyInfoDBEvent, strategy_info)

    async def _send_order_to_exchange(self, order: Order):
        params = {
            'clientId': str(order.id),
            'clientOrderId': str(order.id),
        }
        self._add_params_to_order(order, params)

        order.time_open = datetime.now(tz=timezone.utc)
        price = self._order_price(order)
        return await self.exchange_api.create_order(order.instr.exchange_code,
                                                    order.order_type,
                                                    order.side,
                                                    self._order_amount(order),
                                                    price,
                                                    params=params)

    def _add_params_to_order(self, order, params):
        pass

    def _order_amount(self, order: Order) -> float:
        return order.amount

    def _order_price(self, order: Order):
        return None if order.order_type == MARKET else order.price

    @staticmethod
    def _get_exchange_order_id(order: Order):
        return order.exchange_order_id

    @staticmethod
    def _get_order_res_timestamp(res):
        return (datetime.fromtimestamp(float(res.get('timestamp')) / 1000,
                                       tz=timezone.utc))

    def _populate_order_fields_from_exchange(self, order: Order, res):
        if not res:
            self.logger.error(f'no res from {order}')
            return

        self.logger.info(f'ORDER RESULT {res}')
        try:
            timestamp = self._get_order_res_timestamp(res)

            order.exchange_order_id = res.get('id')
            order.price = self.fetcher._get_price(res)
            #? what returns the exchange here? do i need to x contract_size?
            order.qty = self.fetcher._get_qty(res)
            order.order_status = self.fetcher._get_order_status(res)
            order.total_filled = (float(res.get('filled'))
                                  if res.get('filled') else None)

            if order.order_status == FILLED:
                order.time_filled_mkt = timestamp
            else:
                order.time_ack_mkt = timestamp
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc())

    def _populate_order_fields_from_exchange_simulate(self, order: Order):
        timestamp = datetime.now(tz=timezone.utc)

        order.exchange_order_id = f'simulated:{order.id}'
        order.order_status = self.fetcher._get_order_status_simulate(order)
        order.total_filled = order.r_qty

        # order status should always be filled
        if order.order_status == FILLED:
            order.time_filled_mkt = timestamp
        else:
            order.time_ack_mkt = timestamp

    def _save_order_db(self, order: Order):
        self.redis_manager.publish_event(OrderDBEvent, order)


def exchange_api_run(exchange: ExchangeAPI,
                     instruments,
                     actiave_trading=False):
    if actiave_trading:
        os.environ[ACTIVATE_TRADING] = '1'
    else:
        os.environ[ACTIVATE_TRADING] = '0'

    exchange = exchange(instruments)

    def clean_exit(sig=None, frame=None):
        nonlocal exchange
        exchange.disconnect()
        del exchange

    atexit.register(clean_exit)

    exchange.run()

from dataclasses import asdict

from arb_logger.logger import get_logger
from db_handler.wrapper import DBWrapper
from redis_manager.redis_handler import RedisHandler
from arb_defines.arb_dataclasses import Balance, Order, Position, StrategyInfo, Trade
from redis_manager.redis_events import BalanceEvent, OrderDBEvent, OrderEvent, OrderExchangeEvent, PositionEvent, StrategyInfoDBEvent, TradeExecEvent


class DBHandler:

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__, short=True)
        self.db_wrapper = DBWrapper(logger=self.logger)
        self.redis_handler: RedisHandler = RedisHandler(logger=self.logger)

        self._trades = []
        self._trades_len_limit = 300

    def run(self):
        # we will not record these two in db because it will be too much data
        # keeping it in case we need to cherry save some later?
        # self.redis_handler.psubscribe_event(TradeEvent, self._on_trade_event)

        self.redis_handler.psubscribe_event(OrderExchangeEvent,
                                            self._on_order_exchange_event)
        self.redis_handler.psubscribe_event(TradeExecEvent,
                                            self._on_trade_exec_event)
        self.redis_handler.psubscribe_event(PositionEvent,
                                            self._on_position_event)
        self.redis_handler.psubscribe_event(BalanceEvent,
                                            self._on_balance_event)
        self.redis_handler.subscribe_event(OrderDBEvent,
                                           self._on_order_db_event)
        self.redis_handler.psubscribe_event(OrderEvent,
                                            self._on_order_db_event)
        self.redis_handler.subscribe_event(StrategyInfoDBEvent,
                                           self._on_strategy_info_db_event)

        self.redis_handler.run()

    def kill(self):
        self.logger.info('kill, cleaning up, inserting missing data')
        self._insert_trades()

    def _on_order_exchange_event(self, order: Order):
        order = asdict(order)
        self.db_wrapper.create_order(order)

    def _on_order_db_event(self, order: Order):
        self.logger.info(f'{type(order)}')
        self.logger.info(f'order: {order}')
        order = asdict(order)
        self.db_wrapper.create_or_update_order(order)

    def _on_trade_exec_event(self, trade: Trade):
        trade = asdict(trade)
        self.db_wrapper.create_trade_exec(trade)

    def _on_trade_event(self, trade: Trade):
        trade = asdict(trade)
        if 'instr' in trade:
            del trade['instr']
        if 'exchange_id' in trade:
            del trade['exchange_id']
        if 'fee' in trade:
            del trade['fee']
        self._trades.append(trade)

        if len(self._trades) > self._trades_len_limit:
            self._insert_trades()

    def _on_strategy_info_db_event(self, strategy_info: StrategyInfo):
        strategy_info = asdict(strategy_info)
        self.db_wrapper.create_strategy_info(strategy_info)

    def _on_position_event(self, position: Position):
        position = asdict(position)
        self.db_wrapper.create_or_update_position(position)

    def _on_balance_event(self, balance: Balance):
        balance = asdict(balance)
        self.db_wrapper.create_or_update_balance(balance)

    def _insert_trades(self):
        self.logger.debug(f'bulk inserting {len(self._trades)} trades')
        self.db_wrapper.bulk_create_trades(self._trades)
        self._trades = []
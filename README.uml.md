# UML Diagram

```mermaid
classDiagram
	class DBWrapper {
		-__init__(self, logger=None)
		+bulk_create_trades(self, trades)
		+create_exchange(self, exchange_name, feed_name)
		+create_fee(self, exchange_id, fee_type, percent_value, fixed_value=0)
		+create_instrument(self, instrument)
		+create_latency(self, latency)
		+create_or_update_balance(self, balance) -> int
		+create_or_update_instrument(self, instrument) -> int
		+create_or_update_order(self, order: dict)
		+create_or_update_position(self, position) -> int
		+create_order(self, order: dict)
		+create_strategy_info(self, strategy_info)
		+create_trade(self, trade)
		+create_trade_exec(self, trade)
		+disable_instruments(self, base, quote, instr_type, exchange) -> list[arb_defines.arb_dataclasses.Instrument]
		+execute_sql(self, query, params=None)
		+get_all_instruments
		+get_currencies
		+get_exchange(self, feed_name)
		+get_exchanges(self, exchange_names=None)
		+get_fees(self)
		+get_instrument_from_feed_code(self, feed_code, exchange_id)
		+get_instrument_from_id(self, id)
		+get_instruments
		+get_instruments_like
		+get_instruments_with_ids
		+get_instruments_with_instr_code_like
		+get_or_create_exchange(self, exchange_name, feed_name)
		+get_or_create_fee(self, exchange_id, fee_type, percent_value, fixed_value=0)
		+get_or_create_instrument(self, instrument: dict)
	}
	class DBHandler {
		-__init__(self)
		-_insert_trades(self)
		-_on_balance_event(self, balance: arb_defines.arb_dataclasses.Balance)
		-_on_order_db_event(self, order: arb_defines.arb_dataclasses.Order)
		-_on_order_exchange_event(self, order: arb_defines.arb_dataclasses.Order)
		-_on_position_event(self, position: arb_defines.arb_dataclasses.Position)
		-_on_strategy_info_db_event(self, strategy_info: arb_defines.arb_dataclasses.StrategyInfo)
		-_on_trade_event(self, trade: arb_defines.arb_dataclasses.Trade)
		-_on_trade_exec_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+kill(self)
		+run(self)
	}
	BaseModel <|-- BalanceModel
	Model <|-- BaseModel
	BaseModel <|-- ExchangeModel
	BaseModel <|-- FeeModel
	BaseModel <|-- InstrumentModel
	BaseModel <|-- LatencyModel
	BaseModel <|-- OrderModel
	BaseModel <|-- PositionModel
	BaseModel <|-- StrategyInfoModel
	BaseModel <|-- TradeExecModel
	BaseModel <|-- TradeModel
	class UnknownField {
		-__init__(self, *_, **__)
	}
	class InstrInfos {
		+list[str] | None bases
		+list[str] | None quotes
		+list[str] | None exchanges
		+list[str] | None instr_types
		+list[str] | None contract_types
	}
	class ExchangeAPI {
		-__init__
		-_add_params_to_order(self, order, params)
		-_get_exchange_order_id(order: arb_defines.arb_dataclasses.Order)
		-_get_exchange_yaml(self, full_yaml)
		-_get_order_res_timestamp(res)
		-_load_config(self)
		-_load_exchange_balances(self)
		-_load_exchange_data(self)
		-_load_exchange_orders(self)
		-_load_exchange_positions(self)
		-_order_amount(self, order: arb_defines.arb_dataclasses.Order) -> float
		-_order_price(self, order: arb_defines.arb_dataclasses.Order)
		-_overload_exchange_config(self, exchange_config)
		-_populate_order_fields_from_exchange(self, order: arb_defines.arb_dataclasses.Order, res)
		-_save_order_db(self, order: arb_defines.arb_dataclasses.Order)
		-_send_order_to_exchange(self, order: arb_defines.arb_dataclasses.Order)
		-_snap_strategy_info(self, order: arb_defines.arb_dataclasses.Order)
		+disconnect(self)
		+exchange
		+feed_name
		+fetcher
		+on_cancel_all_orders_event(self, payload: dict = None)
		+on_cancel_all_orders_instr_event(self, payload: dict)
		+on_cancel_order_event(self, order: arb_defines.arb_dataclasses.Order)
		+on_exchange_api_event(self, payload: arb_defines.arb_dataclasses.ExchangeApiPayload)
		+on_order_exchange_event(self, order: arb_defines.arb_dataclasses.Order)
		+run(self)
	}
	class BaseFetcher {
		+Exchange exchange
		+Exchange exchange_api
		+object code_mapping
		+object instr_id_mapping
		+Logger logger
	}
	ExchangeAPI <|-- OKXApi
	class OKXApi {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		+exchange
		+feed_name
		+fetcher
	}
	ExchangeAPI <|-- BittrexApi
	class BittrexApi {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		+exchange
		+feed_name
		+fetcher
	}
	ExchangeAPI <|-- BinanceDeliveryApi
	class BinanceDeliveryApi {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		-_overload_exchange_config(self, exchange_config)
		+exchange
		+feed_name
		+fetcher
	}
	BaseFetcher <|-- BitmexFetcher
	class BitmexFetcher {
		+fetch_balance(self) -> list[arb_defines.arb_dataclasses.Balance]
	}
	ExchangeAPI <|-- BitmexApi
	class BitmexApi {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		-_order_amount(self, order: arb_defines.arb_dataclasses.Order)
		+exchange
		+feed_name
		+fetcher
	}
	bitmex <|-- bitmex
	ExchangeAPI <|-- PoloniexApi
	class PoloniexApi {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		+exchange
		+feed_name
		+fetcher
	}
	BaseFetcher <|-- HuobiFetcher
	class HuobiFetcher {
		+fetch_positions(self) -> list[arb_defines.arb_dataclasses.Position]
	}
	ExchangeAPI <|-- HuobiApi
	class HuobiApi {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		-_get_order_res_timestamp(res)
		-_order_price(self, order: arb_defines.arb_dataclasses.Order)
		-_overload_exchange_config(self, exchange_config)
		+exchange
		+feed_name
		+fetcher
	}
	huobi <|-- huobi
	ExchangeAPI <|-- BybitApi
	class BybitApi {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		-_add_params_to_order(self, order: arb_defines.arb_dataclasses.Order, params)
		-_get_order_res_timestamp(res)
		+exchange
		+feed_name
		+fetcher
	}
	bybit <|-- bybit
	BaseFetcher <|-- BybitFetcher
	class BybitFetcher {
		+fetch_orders(self) -> list[arb_defines.arb_dataclasses.Order]
		+fetch_positions(self) -> list[arb_defines.arb_dataclasses.Position]
	}
	ExchangeAPI <|-- BinanceFuturesApi
	class BinanceFuturesApi {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument], fetch_only: bool = False)
		-_get_order_res_timestamp(res)
		-_overload_exchange_config(self, exchange_config)
		+exchange
		+feed_name
		+fetcher
	}
	BaseFetcher <|-- BinanceFuturesFetcher
	class BinanceFuturesFetcher {
		+fetch_balance(self) -> list[arb_defines.arb_dataclasses.Balance]
		+fetch_orders(self) -> list[arb_defines.arb_dataclasses.Order]
	}
	ExchangeAPI <|-- BinanceApi
	class BinanceApi {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		-_overload_exchange_config(self, exchange_config)
		+exchange
		+feed_name
		+fetcher
	}
	binance <|-- binance
	BaseFetcher <|-- BinanceFetcher
	class BinanceFetcher {
		+fetch_positions(self) -> list[arb_defines.arb_dataclasses.Position]
	}
	BaseRecorder <|-- L2BookRecorder
	class L2BookRecorder {
		+class_small
		+exchanges
		+has_orders
		+has_status
		+instruments
		+recorder_type
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
	}
	OrderBook <|-- OrderBookSmall
	class OrderBookSmall {
		+timestamp
		+to_list(self)
	}
	BaseReader <|-- FundingReader
	class FundingReader {
		+class_small
		+recorder_type
		+short_logger
	}
	WatcherBase <|-- BaseRecorder
	class BaseRecorder {
		-__del__(self)
		-__init__(self)
		-_check_day_change(self, instr_id, timestamp)
		-_check_new_values(self, event)
		-_format_data(self, event)
		+class_small
		+close_fds(self)
		+exchanges
		+flush_fds(self)
		+get_fd(self, instr_id)
		+get_record_path(recorder_type, instr_id, date: datetime.datetime = None)
		+has_orders
		+has_status
		+instruments
		+on_any_event(self, event)
		+open_fd(self, instr_id)
		+recorder_type
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
	}
	class BaseReader {
		-__init__(self, instr_id, date=None, **kwargs)
		-_read(self)
		+class_small
		+get_columns(self)
		+get_reader(self)
		+parse_date(self, date)
		+read(self)
		+recorder_type
		+short_logger
	}
	BaseReader <|-- TradesReader
	class TradesReader {
		+class_small
		+recorder_type
		+short_logger
	}
	BaseReader <|-- L2BookReader
	class L2BookReader {
		+class_small
		+recorder_type
		+short_logger
	}
	BaseRecorder <|-- FundingRateRecorder
	class FundingRateRecorder {
		+class_small
		+exchanges
		+has_orders
		+has_status
		+instruments
		+recorder_type
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
	}
	FundingRate <|-- FundingRateSmall
	class FundingRateSmall {
		+apr
		+apy
		+columns
		+is_up_to_date
		+next_funding_time
		+predicted_rate
		+rate
		+time
		+timestamp
		+to_list(self)
	}
	class TradeSmall {
		+columns
		+instr_id
		+is_liquidation
		+price
		+qty
		+time
		+to_list(self)
		+trade_count
	}
	BaseRecorder <|-- TradesRecorder
	class TradesRecorder {
		+class_small
		+exchanges
		+has_orders
		+has_status
		+instruments
		+recorder_type
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
	}
	ObjectRedis <|-- ExchangeOrdersManager
	class ExchangeOrdersManager {
		+RedisHandler redis_handler
		+Exchange exchange
		+list instruments
		+Logger logger
	}
	ObjectRedis <|-- InstrOrdersManager
	class InstrOrdersManager {
		+RedisHandler redis_handler
		+Instrument instrument
		+Logger logger
	}
	ObjectRedis <|-- OrdersManager
	class OrdersManager {
		+RedisHandler redis_handler
		+list instruments
		+Logger logger
	}
	class RedisManager {
	}
	RedisEvent <|-- ArbDataclassDriverEvent
	class ArbDataclassDriverEvent {
		-__init__(self, objects: object | list[object] | dict[int, object] | None = None)
		-_filter_objects(objects)
		+arb_dataclass
		+dacite_config
		+deserialize
		+get_channels(self)
	}
	ExchangeDrivenEvent <|-- BalanceEvent
	class BalanceEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	NoPayloadEvent <|-- CancelAllOrdersEvent
	RedisEvent <|-- CancelAllOrdersEvent
	class CancelAllOrdersEvent {
		+channel
		+dacite_config
		+deserialize
		+get_channels
		+payload_class
	}
	ReduceIdEvent <|-- CancelAllOrdersExchangeEvent
	ExchangeDrivenEvent <|-- CancelAllOrdersExchangeEvent
	class CancelAllOrdersExchangeEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	ReduceIdEvent <|-- CancelAllOrdersInstrEvent
	ExchangeDrivenEvent <|-- CancelAllOrdersInstrEvent
	class CancelAllOrdersInstrEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	ReduceInstrEvent <|-- CancelOrderEvent
	ExchangeDrivenEvent <|-- CancelOrderEvent
	class CancelOrderEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	ExchangeDrivenEvent <|-- ExchangeApiEvent
	class ExchangeApiEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	ArbDataclassDriverEvent <|-- ExchangeDrivenEvent
	class ExchangeDrivenEvent {
		+arb_dataclass
		+dacite_config
		+deserialize
	}
	ExchangeDrivenEvent <|-- ExchangeStatusEvent
	class ExchangeStatusEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	InstrumentDrivenEvent <|-- FundingRateEvent
	class FundingRateEvent {
		-_filter_objects(instruments: list[arb_defines.arb_dataclasses.Instrument])
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	InstrumentDrivenEvent <|-- InstrStatusEvent
	class InstrStatusEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	ArbDataclassDriverEvent <|-- InstrumentDrivenEvent
	class InstrumentDrivenEvent {
		+arb_dataclass
		+dacite_config
		+deserialize
	}
	RedisEvent <|-- LatencyDBEvent
	class LatencyDBEvent {
		+channel
		+dacite_config
		+deserialize
		+get_channels
		+payload_class
	}
	ReduceInstrEvent <|-- LiquidationEvent
	InstrumentDrivenEvent <|-- LiquidationEvent
	class LiquidationEvent {
		-_filter_objects(instruments: list[arb_defines.arb_dataclasses.Instrument])
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	class NoPayloadEvent {
		+payload_class
		+serialize(payload) -> str
	}
	InstrumentDrivenEvent <|-- OrderBookEvent
	class OrderBookEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	ReduceInstrEvent <|-- OrderDBEvent
	RedisEvent <|-- OrderDBEvent
	class OrderDBEvent {
		+channel
		+dacite_config
		+deserialize
		+get_channels
		+payload_class
	}
	ReduceInstrEvent <|-- OrderEvent
	InstrumentDrivenEvent <|-- OrderEvent
	class OrderEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	ReduceInstrEvent <|-- OrderExchangeEvent
	ExchangeDrivenEvent <|-- OrderExchangeEvent
	class OrderExchangeEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	InstrumentDrivenEvent <|-- PositionEvent
	class PositionEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	ABC <|-- RedisEvent
	class RedisEvent {
		-__init__(self)
		-__repr__(self) -> str
		-__str__(self) -> str
		+dacite_config
		+deserialize
		+get_channels
		+serialize(payload) -> str
	}
	RedisEvent <|-- ReduceIdEvent
	class ReduceIdEvent {
		+dacite_config
		+deserialize
		+get_channels
		+serialize(payload) -> str
	}
	class ReduceInstrEvent {
		+serialize(payload) -> str
	}
	ArbDataclassDriverEvent <|-- SentinelEvent
	class SentinelEvent {
		-__init__(self, objects=None, sentinel_name=None, grp_instr=False)
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+get_channels(self)
		+payload_class
	}
	RedisEvent <|-- StrategyInfoDBEvent
	class StrategyInfoDBEvent {
		+channel
		+dacite_config
		+deserialize
		+get_channels
		+payload_class
	}
	ReduceInstrEvent <|-- TradeDBEvent
	RedisEvent <|-- TradeDBEvent
	class TradeDBEvent {
		+channel
		+dacite_config
		+deserialize
		+get_channels
		+payload_class
	}
	ReduceInstrEvent <|-- TradeEvent
	InstrumentDrivenEvent <|-- TradeEvent
	class TradeEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	ReduceInstrEvent <|-- TradeExecEvent
	InstrumentDrivenEvent <|-- TradeExecEvent
	class TradeExecEvent {
		+arb_dataclass
		+channel
		+dacite_config
		+deserialize
		+payload_class
	}
	RedisEvent <|-- TriggerEvent
	class TriggerEvent {
		-__init__(self, trigger_id: str = None)
		+channel
		+dacite_config
		+deserialize
		+get_channels(self) -> list[str]
		+payload_class
	}
	class EventHandler {
		+RedisEvent event
		+list callbacks
		+bool deserialize
	}
	ABC <|-- RedisHandler
	class RedisHandler {
		-__handle_message(self, message)
		-__publish_payload(self, redis_event: redis_manager.redis_events.RedisEvent, payload, channel=None)
		-__init__(self, host='localhost', port=6379, logger=None)
		+psubscribe_event(self, redis_event: redis_manager.redis_events.RedisEvent, callbacks=None, deserialize=True)
		+publish_event(self, redis_event: redis_manager.redis_events.RedisEvent, payload=None)
		+run(self)
		+subscribe_event(self, redis_event: redis_manager.redis_events.RedisEvent, callbacks=None, deserialize=True)
	}
	Exchange <|-- ExchangeRedis
	StatusRedis <|-- ExchangeRedis
	class ExchangeRedis {
		+RedisHandler redis_handler
		+int id
		+str feed_name
		+str exchange_name
		+str exchange_status
		+Optional status
		+dict balances
		+dict positions
	}
	Instrument <|-- InstrumentRedis
	StatusRedis <|-- InstrumentRedis
	class InstrumentRedis {
		+RedisHandler redis_handler
		+Optional id
		+Optional exchange
		+Optional instr_code
		+Optional symbol
		+Optional base
		+Optional quote
		+Optional instr_type
		+Optional contract_type
		+Optional expiry
		+Optional settle_currency
		+Optional tick_size
		+Optional min_order_size
		+Optional min_size_incr
		+Optional contract_size
		+Optional lot_size
		+int leverage
		+float funding_multiplier
		+Optional maker_fee
		+Optional taker_fee
		+Optional instr_status
		+Optional exchange_code
		+Optional feed_code
		+Optional status
		+Optional timestamp
		+Optional orderbook
		+Optional funding_rate
		+Optional position
		+Optional last_trade
	}
	class ObjectRedis {
		+RedisHandler redis_handler
	}
	ObjectRedis <|-- StatusRedis
	class StatusRedis {
		+is_instr
		+redis_instance
		+refresh_status(self, redis_dict)
		+set_status
		+status_event
	}
	Cmd <|-- ArbCmd
	class ArbCmd {
		-__init__(self, process_manager)
		+do_exit(self, args)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+lastcmd
		+misc_header
		+nohelp
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class ProcessManager {
		-__del__(self)
		-__init__(self, name='')
		-_spawn_process(self, target, args=())
		+kill_all_processes(self)
		+spawn_process(self, process)
		+spawn_processes(self, processes)
	}
	class AggrBook {
		+dict currencies
		+float timestamp
	}
	class AggrFundingRate {
		+defaultdict funding_rates
	}
	class Balance {
		+int exchange_id
		+str currency
		+float qty
		+float total_qty
	}
	class BasePayload {
		+int target_id
		+str action
		+dict data
		+dict config
		+int client_id
	}
	class Candle {
		+datetime time
		+float open
		+float high
		+float low
		+float close
		+float volume
	}
	class ConnectionStatus {
		+Union api
		+Union trades
		+Union l2_book
		+Union funding
		+Union private
		+Union liquidations
		+Optional timestamp
	}
	class Exchange {
		+int id
		+str feed_name
		+str exchange_name
		+str exchange_status
	}
	class ExchangeApiPayload {
		+int exchange_id
		+str action
	}
	ConnectionStatus <|-- ExchangeStatus
	class ExchangeStatus {
		+Union api
		+Union trades
		+Union l2_book
		+Union funding
		+Union private
		+Union liquidations
		+Optional timestamp
		+int exchange_id
	}
	class Fee {
		+int id
		+Exchange exchange
		+float percent_value
		+float fixed_value
	}
	class FundingRate {
		+int instr_id
		+Optional rate
		+Optional predicted_rate
		+Optional next_funding_time
		+Optional timestamp
	}
	ConnectionStatus <|-- InstrStatus
	class InstrStatus {
		+Union api
		+Union trades
		+Union l2_book
		+Union funding
		+Union private
		+Union liquidations
		+Optional timestamp
		+int instr_id
	}
	class Instrument {
		+Optional id
		+Optional exchange
		+Optional instr_code
		+Optional symbol
		+Optional base
		+Optional quote
		+Optional instr_type
		+Optional contract_type
		+Optional expiry
		+Optional settle_currency
		+Optional tick_size
		+Optional min_order_size
		+Optional min_size_incr
		+Optional contract_size
		+Optional lot_size
		+int leverage
		+float funding_multiplier
		+Optional maker_fee
		+Optional taker_fee
		+Optional instr_status
		+Optional exchange_code
		+Optional feed_code
	}
	class Latency {
		+Optional id
		+Optional time
		+Optional event_id
		+Optional event_type
	}
	class Order {
		+Union id
		+Optional time
		+Optional instr
		+Optional exchange_order_id
		+Optional order_type
		+Optional price
		+Optional qty
		+str order_status
		+Optional instr_id
		+Optional exchange_id
		+Optional strat_id
		+Optional event_type
		+Optional event_key
		+Optional time_open
		+Optional time_ack_mkt
		+Optional time_filled_mkt
		+Optional time_cancel
		+Optional time_canceled_mkt
		+Optional time_rejected_mkt
		+Optional total_filled
	}
	class OrderBook {
		+int instr_id
		+list bids
		+list asks
		+Optional timestamp
	}
	class Position {
		+int instr_id
		+float qty
		+float price
		+Optional liquidation_price
	}
	class SentinelPayload {
		+str sentinel_id
		+str action
		+dict data
		+dict config
	}
	class StrategyInfo {
		+dict payload
		+Optional order_id
		+Optional event_key
		+Optional time
	}
	class Trade {
		+Union id
		+datetime time
		+float qty
		+float price
		+str order_type
		+str exchange_order_id
		+Optional fee
		+Optional instr
		+Optional instr_id
		+Optional exchange_id
		+bool is_liquidation
		+int trade_count
	}
	class TriggerPayload {
		+str trigger_id
		+str action
		+dict data
		+dict config
	}
	class EventTypes {
		+HIT_HIT
		+HIT_HIT_FUNDING
		+MM_DUMB
		+MM_GRID
		+MM_TRIGGER
		+PAIR_SEEKER
		+ROLLER
		+SPREAD_TRIGGER
		+SPREAD_TRIGGER_LIQ
		+SPREAD_TRIGGER_LIQ_WAIT
		+TAKE_HIT
		+TRI_ARB_SPOT_PERP_FUNDING
	}
	Enum <|-- StatusEnum
	class StatusEnum {
		+DOWN
		+IGNORE
		+READY
		+START
		+STARTED
		+STARTING
		+STOP
		+STOPPED
		+STOPPING
		+UNAVAILABLE
		+UNDEFINED
		+UNKNOWN
		+UNREACHABLE
		+UP
	}
	class OrderType {
		+FILL_OR_KILL
		+GOOD_TIL_CANCELED
		+IMMEDIATE_OR_CANCEL
		+LIMIT
		+MAKER_OR_CANCEL
		+MARKET
		+STOP_LIMIT
		+STOP_MARKET
	}
	ExchangeBase <|-- ExchangeAuthenticatedWebsocket
	class ExchangeAuthenticatedWebsocket {
		-__init__
		-_extract_order_info(self, order_info, receipt_timestamp) -> arb_defines.arb_dataclasses.Order
		-_extract_trade_info(self, trade_info, receipt_timestamp) -> arb_defines.arb_dataclasses.Trade
		-_get_exchange_order_id(trade_info)
		-_get_fee(trade_info)
		-_get_order_id(self, order_info)
		-_get_order_status(order_info)
		-_get_order_type(order_info)
		-_get_price(order_info)
		-_get_qty(order_info)
		-_get_total_filled(order_info)
		-_get_trade_qty(trade_info)
		-_get_trade_type(trade_info)
		-_run_redis_manager(self)
		-_subscribe(self)
		-_update_balance_from_trade(self, trade: arb_defines.arb_dataclasses.Trade, balance_consumption: float)
		-_update_position_from_trade(self, trade: arb_defines.arb_dataclasses.Trade)
		+custom_callbacks
		+disconnect(self)
		+exchange
		+has_orders
		+on_balances_cb(self, balance, receipt_timestamp)
		+on_fills_cb(self, trade_info, receipt_timestamp)
		+on_order_info_cb(self, order_info, receipt_timestamp)
		+on_positions_cb(self, position, receipt_timestamp)
		+redis
		+run(self)
	}
	ExchangeBase <|-- ExchangeWebsocket
	class ExchangeWebsocket {
		-__init__
		-_get_next_funding_time(self, obj)
		-_get_predicted_rate(self, obj, instr)
		-_get_rate(sefl, obj, instr)
		-_get_trade_count(trade)
		-_handle_status(self, instr, channel)
		-_init_status(self)
		+custom_callbacks
		+disconnect(self)
		+exchange
		+has_orders
		+on_funding_cb(self, obj, timestamp: float)
		+on_l2_book_cb(self, book, timestamp: float)
		+on_liquidations_cb(self, liquidation, timestamp)
		+on_trades_cb(self, trade, timestamp: float)
		+redis
		+run(self)
	}
	ABC <|-- ExchangeBase
	class ExchangeBase {
		-__init__
		-_add_new_instr(self, feed_code: str) -> arb_defines.arb_dataclasses.Instrument
		-_build_mapping(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		-_get_callbacks(self)
		-_get_handler_config(self)
		+custom_callbacks
		+disconnect(self)
		+exchange
		+get_instr_from_code(self, code: str)
		+has_orders
		+on_fills_cb(self, *args)
		+on_funding_cb(self, *args)
		+on_l2_book_cb(self, *args)
		+on_liquidations_cb(self, *args)
		+on_order_info_cb(self, *args)
		+on_trades_cb(self, *args)
		+redis
		+run(self)
	}
	ExchangeWebsocket <|-- OKXWebsocket
	class OKXWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- BittrexWebsocket
	class BittrexWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeAuthenticatedWebsocket <|-- BinanceDeliveryAuthenticatedWebsocket
	class BinanceDeliveryAuthenticatedWebsocket {
		-__init__(self, *args)
		-_get_order_id(self, order_info)
		-_get_total_filled(order_info)
		-_order_info_cb(self, order_info, receipt_timestamp)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	BinanceWebsocket <|-- BinanceDeliveryWebsocket
	class BinanceDeliveryWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- FtxWebsocket
	class FtxWebsocket {
		-__init__(self, *args)
		-_get_rate(sefl, obj, instr)
		+custom_callbacks
		+exchange
		+has_orders
		+on_trades_cb(self, trade, timestamp: float)
		+redis
	}
	ExchangeAuthenticatedWebsocket <|-- FtxAuthenticatedWebsocket
	class FtxAuthenticatedWebsocket {
		-__init__(self, *args)
		-_get_order_id(self, order_info)
		-_get_order_status(order_info)
		-_get_price(order_info)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeAuthenticatedWebsocket <|-- BitmexAuthenticatedWebsocket
	class BitmexAuthenticatedWebsocket {
		-__init__(self, *args)
		-_get_order_id(self, order_info)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- BitmexWebsocket
	class BitmexWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- BitfinexWebsocket
	class BitfinexWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- PoloniexFuturesWebsocket
	class PoloniexFuturesWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- PoloniexWebsocket
	class PoloniexWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- HuobiWebsocket
	class HuobiWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeAuthenticatedWebsocket <|-- HuobiAuthenticatedWebsocket
	class HuobiAuthenticatedWebsocket {
		-__init__(self, *args)
		-_get_order_id(self, order_info)
		-_get_order_status(order_info)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- HitbtcWebsocket
	class HitbtcWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeAuthenticatedWebsocket <|-- HitbtcAuthenticatedWebsocket
	class HitbtcAuthenticatedWebsocket {
		-__init__(self, *args)
		-_get_order_id(self, order_info)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeAuthenticatedWebsocket <|-- BybitAuthenticatedWebsocket
	class BybitAuthenticatedWebsocket {
		-__init__(self, *args)
		-_get_order_id(self, order_info)
		-_get_qty(order_info)
		-_get_total_filled(order_info)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- BybitWebsocket
	class BybitWebsocket {
		-__init__(self, *args)
		-_get_rate(self, obj, instr)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- BitgetWebsocket
	class BitgetWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- HuobiSwapWebsocket
	class HuobiSwapWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- GateioFuturesWebsocket
	class GateioFuturesWebsocket {
		-__init__(self, *args)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeAuthenticatedWebsocket <|-- BinanceFuturesAuthenticatedWebsocket
	class BinanceFuturesAuthenticatedWebsocket {
		-__init__(self, *args)
		-_get_exchange_order_id(trade_info)
		-_get_fee(trade_info)
		-_get_order_id(self, order_info)
		-_get_order_status(order_info)
		-_get_price(order_info)
		-_get_qty(order_info)
		-_get_total_filled(order_info)
		-_get_trade_qty(trade_info)
		-_get_trade_type(trade_info)
		+custom_callbacks
		+exchange
		+has_orders
		+on_order_info_cb(self, order_info, receipt_timestamp)
		+redis
	}
	BinanceWebsocket <|-- BinanceFuturesWebsocket
	class BinanceFuturesWebsocket {
		-__init__(self, *args)
		-_get_predicted_rate(self, obj, instr)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeWebsocket <|-- BinanceWebsocket
	class BinanceWebsocket {
		-__init__(self, *args)
		-_get_trade_count(trade)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExchangeAuthenticatedWebsocket <|-- BinanceAuthenticatedWebsocket
	class BinanceAuthenticatedWebsocket {
		-__init__(self, *args)
		-_get_order_id(self, order_info)
		-_get_total_filled(order_info)
		-_order_info_cb(self, order_info, receipt_timestamp)
		+custom_callbacks
		+exchange
		+has_orders
		+redis
	}
	ExecutorBase <|-- SingleOrder
	class SingleOrder {
		-__init__
		+exchanges
		+has_orders
		+has_status
		+instruments
		+on_order_book_event(self, orderbook: arb_defines.arb_dataclasses.OrderBook)
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
	}
	ExecutorBase <|-- SeekerBase
	class SeekerBase {
		+exchanges
		+has_orders
		+has_status
		+instruments
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
	}
	Cmd <|-- SeekerClientBase
	class SeekerClientBase {
		-__init__(self, instruments)
		-_set_macos(self)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+prompt
		+ruler
		+run(self)
		+undoc_header
		+use_rawinput
	}
	ExecutorBase <|-- TriggerBase
	class TriggerBase {
		-__init__(self, instruments) -> None
		-_register_trigger(self)
		+cancel_all_pendings(self)
		+config_class
		+disconnect(self)
		+exchanges
		+has_orders
		+has_status
		+instruments
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+send_orders_to_client(self)
		+send_trigger_client(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
	}
	Cmd <|-- TriggerClient
	class TriggerClient {
		-__init__(self, instruments)
		-_set_macos(self)
		+complete_set(self, text, line, begidx, endidx)
		+config
		+do_cancel_all(self, args)
		+do_config(self, args)
		+do_debug(self, args)
		+do_exit(self, args)
		+do_instruments(self, args)
		+do_name(self, args)
		+do_push_config(self, _)
		+do_set(self, args)
		+do_show_orders(self, args)
		+do_start(self, args)
		+do_stop(self, args)
		+do_stop_server(self, args)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+lastcmd
		+linked_class
		+listen_server(self)
		+misc_header
		+nohelp
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+precmd(self, line) -> None
		+preloop(self) -> None
		+prompt
		+ruler
		+run(self)
		+send_trigger(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+show_config(self)
		+show_instr(self)
		+undoc_header
		+use_rawinput
	}
	WatcherBase <|-- ExecutorBase
	class ExecutorBase {
		-__init__(self, instruments) -> None
		-_check_balance_for_order(self, order: arb_defines.arb_dataclasses.Order) -> bool
		-_check_status(self, order: arb_defines.arb_dataclasses.Order) -> bool
		-_fix_order_qty
		-_fix_order_size(self, size, order1: arb_defines.arb_dataclasses.Order, order2: arb_defines.arb_dataclasses.Order)
		-_fix_orders_size
		+cancel_all_pendings(self)
		+cancel_order(self, order)
		+cancel_pending_instr(self, instr)
		+check_order(self, order: arb_defines.arb_dataclasses.Order) -> bool
		+exchanges
		+has_orders
		+has_status
		+instruments
		+send_order(self, order: arb_defines.arb_dataclasses.Order, checked=False)
		+send_orders(self, orders: list[arb_defines.arb_dataclasses.Order], checked=False, eq_size=False)
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
	}
	WatcherBase <|-- SentinelBase
	class SentinelBase {
		-__init__(self, instruments) -> None
		-_send_event(self, action, data, payload: arb_defines.arb_dataclasses.SentinelPayload = None)
		+exchanges
		+grp_instr
		+has_orders
		+has_status
		+instruments
		+on_sentinel_server_event(self, payload: arb_defines.arb_dataclasses.SentinelPayload)
		+send_snapshot(self, data=None, payload=None)
		+send_update(self, data=None, payload=None)
		+sentinel_client_id(sentinel_name, client_id, instruments=None)
		+sentinel_id
		+sentinel_name
		+sentinel_server_id(sentinel_id, instruments=None)
		+short_logger
		+sort_instr
		+sorted_hash
		+subscribe_to_events(self)
	}
	class SentinelClientBase {
		-__init__
		-_format_values(self, values)
		+ask_snapshot(self)
		+on_sentinel_event(self, payload: arb_defines.arb_dataclasses.SentinelPayload)
		+on_snapshot_event(self, payload: arb_defines.arb_dataclasses.SentinelPayload)
		+on_update_event(self, payload: arb_defines.arb_dataclasses.SentinelPayload)
		+sentinel_class
		+subscribe_to_events(self)
		+values_max_len
	}
	class WatcherBase {
		-__init__(self, instruments=[]) -> None
		-_build_name(class_name, instruments) -> str
		+exchanges
		+has_orders
		+has_status
		+instruments
		+run(self)
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
	}
	ExecutorBase <|-- CancelOrder
	class CancelOrder {
		-__init__(self, instrument: arb_defines.arb_dataclasses.Instrument, order_id: str)
		+exchanges
		+has_orders
		+has_status
		+instruments
		+short_logger
		+sorted_hash
	}
	TriggerBase <|-- MMGrid
	class MMGrid {
		-__init__(self, instruments) -> None
		-_compute_volat(self)
		-_get_order_price(self, mult, side)
		-_get_order_qty(self, mult, side)
		-_send_pong(self)
		+atr_len
		+buy_orders
		+calc_atr(ohlc, length)
		+client_class
		+compute_orders(self)
		+config_class
		+create_orders(self)
		+exchanges
		+get_step(self, space, a)
		+has_orders
		+has_status
		+instrument
		+instruments
		+on_atr_update(self, payload: arb_defines.arb_dataclasses.SentinelPayload)
		+on_trade_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+on_trade_exec_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+sell_orders
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
		+update_state(self)
	}
	TriggerClient <|-- MMGridClient
	class MMGridClient {
		-__init__(self, instruments)
		+config
		+do_ping(self, _)
		+do_update(self, _)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class MMGridConfig {
		+Instrument instr
		+float order_qty
		+int order_interval
		+int nb_orders
		+float p_method
		+float p_mult
		+float q_mult
		+float _p_shift
		+int volat_len
		+bool use_atr
		+float atr_mult
		+float atr_val
		+float buy_price_skew
		+float sell_price_skew
	}
	TriggerBase <|-- MMGrid
	class MMGrid {
		-__init__(self, instruments) -> None
		-_compute_volat(self)
		-_get_order_price(self, mult, side)
		-_get_order_qty(self, mult, side)
		-_send_pong(self)
		+atr_len
		+buy_orders
		+calc_atr(ohlc, length)
		+client_class
		+compute_orders(self)
		+config_class
		+create_orders(self)
		+exchanges
		+has_orders
		+has_status
		+instrument
		+instruments
		+on_trade_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+on_trade_exec_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+sell_orders
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
		+update_state(self)
	}
	TriggerClient <|-- MMGridClient
	class MMGridClient {
		-__init__(self, instruments)
		+config
		+do_ping(self, _)
		+do_update(self, _)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class MMGridConfig {
		+Instrument instr
		+float order_qty
		+int order_interval
		+int nb_orders
		+float q_mult
		+float p_mult
		+float _p_shift
		+int volat_len
		+bool use_atr
		+float atr_mult
		+float atr_val
		+float buy_price_skew
		+float sell_price_skew
	}
	TriggerBase <|-- MMTrigger
	class MMTrigger {
		-__init__(self, instruments) -> None
		-_seeker_checks(self)
		+cancel_all_pendings(self)
		+cancel_pending_orders(self, orders: list[arb_defines.arb_dataclasses.Order])
		+config_class
		+exchanges
		+has_orders
		+has_status
		+instruments
		+maker_buy(self)
		+maker_sell(self)
		+on_order_book_event(self, orderbook: arb_defines.arb_dataclasses.OrderBook)
		+on_order_event(self, order: arb_defines.arb_dataclasses.Order)
		+on_trade_exec_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+short_logger
		+sorted_hash
		+spread
		+subscribe_to_events(self)
		+update_orders(self)
	}
	TriggerClient <|-- MMTriggerClient
	class MMTriggerClient {
		-__init__(self, instruments)
		+config
		+do_cancel(self, arg)
		+do_reset(self, arg)
		+do_revert(self, arg)
		+do_s(self, arg)
		+do_start(self, arg)
		+do_stop(self, arg)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+is_ready
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class MMTriggerConfig {
		+Instrument left_leg
		+Instrument right_leg
		+float order_qty
		+float update_treshold
	}
	TriggerBase <|-- MMTrigger
	class MMTrigger {
		-__init__(self, instruments) -> None
		-_seeker_checks(self)
		+cancel_pending_orders(self, orders: list[arb_defines.arb_dataclasses.Order])
		+config_class
		+exchange
		+exchanges
		+has_orders
		+has_status
		+instruments
		+maker_buy(self)
		+maker_sell(self)
		+on_order_book_event(self, orderbook: arb_defines.arb_dataclasses.OrderBook)
		+on_order_event(self, order: arb_defines.arb_dataclasses.Order)
		+on_trade_exec_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+short_logger
		+sorted_hash
		+spread
		+subscribe_to_events(self)
		+update_orders(self)
	}
	TriggerClient <|-- MMTriggerClient
	class MMTriggerClient {
		-__init__(self, instruments)
		-_order_percent(self, arg, side)
		-_set_conf(self, key, value, v_type=<class 'float'>, restart=False)
		+config
		+do_b(self, arg)
		+do_cancel(self, arg)
		+do_d(self, arg)
		+do_f(self, arg)
		+do_qt(self, arg)
		+do_reset(self, arg=None)
		+do_revert(self, arg)
		+do_s(self, arg)
		+do_sp(self, arg)
		+do_sq(self, arg)
		+do_start(self, arg=None)
		+do_stop(self, arg=None)
		+do_u(self, arg)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+is_ready
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class MMTriggerConfig {
		+Instrument left_leg
		+Instrument right_leg
		+float order_qty
		+int depth
		+float q_mult
		+float p_mult
		+float update_treshold
		+float sp
		+float bp
	}
	TriggerBase <|-- SpreadTriggerLiq
	class SpreadTriggerLiq {
		-__init__(self, instruments) -> None
		-_build_orders(self, side: str)
		-_check_spreads(self)
		-_fix_order_qty(self, order1: arb_defines.arb_dataclasses.Order, order2: arb_defines.arb_dataclasses.Order)
		-_stop_retry(self)
		-_trigger_checks(self)
		+config_class
		+exchanges
		+has_orders
		+has_status
		+instruments
		+maker_buy(self)
		+maker_sell(self)
		+on_order_book_event(self, orderbook: arb_defines.arb_dataclasses.OrderBook)
		+on_order_event(self, order: arb_defines.arb_dataclasses.Order)
		+on_trade_exec_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+short_logger
		+sorted_hash
		+spread
		+subscribe_to_events(self)
		+taker_buy(self)
		+taker_sell(self)
	}
	TriggerClient <|-- SpreadTriggerLiqClient
	class SpreadTriggerLiqClient {
		-__init__(self, instruments)
		+config
		+do_c(self, arg)
		+do_cancel(self, arg)
		+do_long(self, arg)
		+do_short(self, arg)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+is_ready
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class SpreadTriggerLiqConfig {
		+Instrument left_leg
		+Instrument right_leg
		+bool need_pos_spread
		+float min_spread
		+float order_qty
		+float retry_seconds
		+float bp
		+float sp
	}
	TriggerBase <|-- SpreadTrigger
	class SpreadTrigger {
		-__init__(self, instruments) -> None
		-_build_orders(self, side: str)
		-_check_spreads(self)
		-_fix_order_qty(self, order1: arb_defines.arb_dataclasses.Order, order2: arb_defines.arb_dataclasses.Order)
		-_stop_retry(self)
		-_trigger_checks(self)
		+config_class
		+exchanges
		+has_orders
		+has_status
		+instruments
		+on_order_book_event(self, orderbook: arb_defines.arb_dataclasses.OrderBook)
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+short_logger
		+sorted_hash
		+spread
		+subscribe_to_events(self)
		+taker_buy(self)
		+taker_sell(self)
	}
	TriggerClient <|-- SpreadTriggerClient
	class SpreadTriggerClient {
		-__init__(self, instruments)
		+config
		+do_c(self, arg)
		+do_cancel(self, arg)
		+do_long(self, arg)
		+do_short(self, arg)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+is_ready
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class SpreadTriggerConfig {
		+Instrument left_leg
		+Instrument right_leg
		+bool need_pos_spread
		+float min_spread
		+float order_qty
		+float retry_seconds
	}
	TriggerBase <|-- SpreadTriggerLiqWait
	class SpreadTriggerLiqWait {
		-__init__(self, instruments) -> None
		-_check_spreads(self)
		-_stop_retry(self)
		-_trigger_checks(self)
		+config_class
		+curr_delta(self)
		+exchanges
		+has_orders
		+has_status
		+instruments
		+maker_buy(self)
		+maker_sell(self)
		+on_order_book_event(self, orderbook: arb_defines.arb_dataclasses.OrderBook)
		+on_order_event(self, order: arb_defines.arb_dataclasses.Order)
		+on_position_event(self, position: arb_defines.arb_dataclasses.Position)
		+on_trade_exec_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+on_trigger_event(self, payload: arb_defines.arb_dataclasses.TriggerPayload)
		+send_first_order(self, side: str)
		+send_hedge_order(self, trade: arb_defines.arb_dataclasses.Trade, delta)
		+short_logger
		+sorted_hash
		+spread
		+subscribe_to_events(self)
		+update_order(self, old_order)
	}
	TriggerClient <|-- SpreadTriggerLiqWaitClient
	class SpreadTriggerLiqWaitClient {
		-__init__(self, instruments)
		+config
		+do_c(self, arg)
		+do_cancel(self, arg)
		+do_long(self, arg)
		+do_revert(self, arg)
		+do_short(self, arg)
		+doc_header
		+doc_leader
		+identchars
		+intro
		+is_ready
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class SpreadTriggerLiqWaitConfig {
		+Instrument left_leg
		+Instrument right_leg
		+bool need_pos_spread
		+str first_exch
		+float min_spread
		+float order_qty
		+float update_sec
		+float retry_seconds
		+float fp
	}
	TriggerBase <|-- MMDumb
	class MMDumb {
		-__init__(self, instruments) -> None
		-_get_orders_grid(self)
		-_get_price_grid(self)
		+build_orders(self)
		+clean_orders(self)
		+client_class
		+config_class
		+exchanges
		+has_orders
		+has_status
		+instrument
		+instruments
		+on_orderbook_event(self, orderbook: arb_defines.arb_dataclasses.OrderBook)
		+on_trade_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+on_trade_exec_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
		+update_state(self)
	}
	TriggerClient <|-- MMDumbClient
	class MMDumbClient {
		-__init__(self, instruments)
		+config
		+doc_header
		+doc_leader
		+identchars
		+intro
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class MMDumbConfig {
		+Instrument instr
		+int nb_orders
		+float order_qty
		+float buy_price_skew
		+float sell_price_skew
		+int update_freq
	}
	ExecutorBase <|-- Roller
	class Roller {
		-__init__(self, instrument, qty) -> None
		-_run_thread(self)
		+build_order(self, side)
		+exchanges
		+has_orders
		+has_status
		+instrument
		+instruments
		+run(self)
		+short_logger
		+sorted_hash
		+try_roll(self)
	}
	WatcherBase <|-- Hedger
	class Hedger {
		-__init__(self, product)
		-_execute_hedge(self, hedge)
		-_find_highest_bid(self)
		-_find_lowest_ask(self)
		-_handle_message(self, obj)
		+exchanges
		+has_orders
		+has_status
		+instruments
		+run(self)
		+short_logger
		+sorted_hash
	}
	SeekerBase <|-- PairSeeker
	class PairSeeker {
		-__init__(self, instruments) -> None
		-_adjust_orders(self, orders)
		-_build_order(self, instr: redis_manager.redis_wrappers.InstrumentRedis, qty: float)
		-_get_qties(self, zscore, beta, instr1, instr2)
		-_pre_checks(self)
		+build_orders(self)
		+exchanges
		+has_orders
		+has_status
		+instruments
		+short_logger
		+sorted_hash
		+subscribe_to_events(self)
		+update(self)
	}
	SeekerClientBase <|-- PairSeekerClient
	class PairSeekerClient {
		+doc_header
		+doc_leader
		+identchars
		+intro
		+lastcmd
		+linked_class
		+misc_header
		+nohelp
		+prompt
		+ruler
		+undoc_header
		+use_rawinput
	}
	class PairSeekerConfig {
		+float size
	}
	class SeekerSpread {
	}
	class Config {
		+float last_order_threshold
	}
	class SeekerSpread {
		-__init__(self, instruments: list[arb_defines.arb_dataclasses.Instrument])
		-__str__(self) -> str
		-_check_book_depth
		-_check_order_size(self, orders: list[arb_defines.arb_dataclasses.Order]) -> bool
		-_fix_order_size(self, order1: arb_defines.arb_dataclasses.Order, order2: arb_defines.arb_dataclasses.Order)
		-_snap_strategy_info(self, order)
		+fire_orders(self, orders: list[arb_defines.arb_dataclasses.Order])
		+load_exchanges_from_redis(self)
		+load_instruments_from_redis(self)
		+on_balance_event(self, balance: arb_defines.arb_dataclasses.Balance)
		+on_exchange_status_event(self, es: arb_defines.arb_dataclasses.ExchangeStatus)
		+on_instr_status_event(self, i_s: arb_defines.arb_dataclasses.InstrStatus)
		+on_order_book_event(self, orderbook: arb_defines.arb_dataclasses.OrderBook)
		+on_position_event(self, position: arb_defines.arb_dataclasses.Position)
		+pre_routine_checks(self, instr)
		+run(self)
		+strat_routine(self, instr)
	}
	class Config {
		+float last_order_threshold
	}
	class SeekerSpreadFunding {
		-__init__
		-__str__(self) -> str
		-_check_order_size(self, orders: list[arb_defines.arb_dataclasses.Order]) -> bool
		-_compute_spread(self, spread, excl_buy, excl_sell, secret_word='')
		-_snap_strategy_info(self, order)
		-_update_excl_buys(self)
		-_update_excl_sells(self)
		+entry_spread(self)
		+exit_spread(self)
		+fire_orders(self, orders: list[arb_defines.arb_dataclasses.Order], bypass_timeout=False)
		+load_currencies_from_redis(self)
		+load_exchanges_from_redis(self)
		+load_instruments_from_redis(self)
		+on_balance_event(self, balance: arb_defines.arb_dataclasses.Balance)
		+on_exchange_status_event(self, es: arb_defines.arb_dataclasses.ExchangeStatus)
		+on_funding_rate_event(self, funding_rate: arb_defines.arb_dataclasses.FundingRate)
		+on_instr_status_event(self, i_s: arb_defines.arb_dataclasses.InstrStatus)
		+on_order_book_event(self, orderbook: arb_defines.arb_dataclasses.OrderBook)
		+on_position_event(self, position: arb_defines.arb_dataclasses.Position)
		+on_trade_exec_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+pre_routine_checks(self, instr)
		+run(self)
		+strat_routine(self, instr)
		+update_excl(self)
	}
	SentinelBase <|-- AtrSentinel
	class AtrSentinel {
		-__init__(self, instruments, atr_len, tf) -> None
		+calc_atr(ohlc, length)
		+exchanges
		+grp_instr
		+has_orders
		+has_status
		+instrument
		+instruments
		+on_trade_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+send_atr_update(self)
		+sentinel_id
		+sentinel_name
		+short_logger
		+sort_instr
		+sorted_hash
		+subscribe_to_events(self)
		+update_atr(self)
	}
	SentinelClientBase <|-- AtrSentinelClient
	class AtrSentinelClient {
		+sentinel_class
		+values_max_len
	}
	SentinelBase <|-- CandleSentinel
	class CandleSentinel {
		-__init__(self, instruments) -> None
		+exchanges
		+grp_instr
		+has_orders
		+has_status
		+instruments
		+load_candles(self)
		+max_nb_candles
		+on_trade_event(self, trade: arb_defines.arb_dataclasses.Trade)
		+send_last_candle(self)
		+sentinel_id
		+sentinel_name
		+short_logger
		+sort_instr
		+sorted_hash
		+subscribe_to_events(self)
		+update_candles(self)
	}
	SentinelClientBase <|-- CandleSentinelClient
	class CandleSentinelClient {
		-_format_values(self, values)
		+sentinel_class
		+values_max_len
	}
	SentinelBase <|-- PairZscoreSentinel
	class PairZscoreSentinel {
		-__init__(self, instruments, tf=60, window=1440, refresh_period=60) -> None
		+exchanges
		+grp_instr
		+has_orders
		+has_status
		+instruments
		+sentinel_id
		+sentinel_name
		+short_logger
		+sort_instr
		+sorted_hash
		+subscribe_to_events(self)
		+update(self)
	}
	SentinelClientBase <|-- PairZscoreSentinelClient
	class PairZscoreSentinelClient {
		+sentinel_class
		+values_max_len
	}
```

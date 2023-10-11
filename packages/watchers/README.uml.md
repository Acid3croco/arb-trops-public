# UML Diagram

```mermaid
classDiagram
	direction LR
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
	}
	class TriangularArbSpotPerpFundingSeeker {
		-__init__
		-__str__(self) -> str
		-_check_order_size(self, orders: list[arb_defines.arb_dataclasses.Order]) -> bool
		-_exchanges_status_check(self)
		-_instruments_status_check(self)
		-_show_spread(self, spread, buy_instr, sell_instr, secret_word='')
		-_snap_strategy_info(self, order)
		+currency
		+entry_spread(self)
		+entry_spread_orders(self)
		+exit_spread(self)
		+exit_spread_orders(self)
		+fire_orders(self, orders: list[arb_defines.arb_dataclasses.Order])
		+instr_perp
		+instr_spot
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

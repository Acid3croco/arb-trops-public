CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ███████╗██╗  ██╗ ██████╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗ ███████╗███████╗
-- ██╔════╝╚██╗██╔╝██╔════╝██║  ██║██╔══██╗████╗  ██║██╔════╝ ██╔════╝██╔════╝
-- █████╗   ╚███╔╝ ██║     ███████║███████║██╔██╗ ██║██║  ███╗█████╗  ███████╗
-- ██╔══╝   ██╔██╗ ██║     ██╔══██║██╔══██║██║╚██╗██║██║   ██║██╔══╝  ╚════██║
-- ███████╗██╔╝ ██╗╚██████╗██║  ██║██║  ██║██║ ╚████║╚██████╔╝███████╗███████║
-- ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚══════╝

CREATE TABLE IF NOT EXISTS exchanges (
    id SERIAL PRIMARY KEY,
    exchange_name VARCHAR(255) NOT NULL,
    feed_name VARCHAR(255) NOT NULL,
    exchange_status VARCHAR(255)
);

CREATE UNIQUE INDEX IF NOT EXISTS exchanges_idx ON exchanges(feed_name);



-- ██╗███╗   ██╗███████╗████████╗██████╗ ██╗   ██╗███╗   ███╗███████╗███╗   ██╗████████╗███████╗
-- ██║████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██║   ██║████╗ ████║██╔════╝████╗  ██║╚══██╔══╝██╔════╝
-- ██║██╔██╗ ██║███████╗   ██║   ██████╔╝██║   ██║██╔████╔██║█████╗  ██╔██╗ ██║   ██║   ███████╗
-- ██║██║╚██╗██║╚════██║   ██║   ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║   ██║   ╚════██║
-- ██║██║ ╚████║███████║   ██║   ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║   ██║   ███████║
-- ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝

CREATE TABLE IF NOT EXISTS instruments (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER NOT NULL,
    instr_code VARCHAR(255) NOT NULL,
    symbol VARCHAR(255) NOT NULL,
    base VARCHAR(255) NOT NULL,
    quote VARCHAR(255) NOT NULL,
    instr_type VARCHAR(255) NOT NULL,
    contract_type VARCHAR(255),
    expiry TIMESTAMPTZ,
    settle_currency VARCHAR(255),
    tick_size DOUBLE PRECISION NOT NULL,
    min_order_size DOUBLE PRECISION NOT NULL,
    min_size_incr DOUBLE PRECISION NOT NULL,
    contract_size DOUBLE PRECISION NOT NULL,
    lot_size DOUBLE PRECISION NOT NULL,
    leverage INTEGER NOT NULL DEFAULT 1,
    funding_multiplier DOUBLE PRECISION DEFAULT 1 NOT NULL,
    maker_fee_id INTEGER,
    taker_fee_id INTEGER,
    instr_status VARCHAR(255) NOT NULL,
    exchange_code VARCHAR(255) NOT NULL,
    feed_code VARCHAR(255) NOT NULL,
    FOREIGN KEY(exchange_id) REFERENCES exchanges(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS instruments_unique_idx ON instruments(exchange_id, base, quote, instr_type, contract_type, expiry);
CREATE UNIQUE INDEX IF NOT EXISTS instruments_unique_name_idx ON instruments(instr_code);



-- ███████╗███████╗███████╗███████╗
-- ██╔════╝██╔════╝██╔════╝██╔════╝
-- █████╗  █████╗  █████╗  ███████╗
-- ██╔══╝  ██╔══╝  ██╔══╝  ╚════██║
-- ██║     ███████╗███████╗███████║
-- ╚═╝     ╚══════╝╚══════╝╚══════╝

CREATE TABLE IF NOT EXISTS fees (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER NOT NULL,
    fee_type VARCHAR(255) NOT NULL,
    percent_value DOUBLE PRECISION NOT NULL,
    fixed_value DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(exchange_id) REFERENCES exchanges(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS fees_unique_idx ON fees(exchange_id, fee_type, percent_value, fixed_value);

ALTER TABLE instruments
    ADD FOREIGN KEY(maker_fee_id) REFERENCES
    fees(id),
    ADD FOREIGN KEY(taker_fee_id) REFERENCES fees(id);



-- ██████╗  █████╗ ██╗      █████╗ ███╗   ██╗ ██████╗███████╗███████╗
-- ██╔══██╗██╔══██╗██║     ██╔══██╗████╗  ██║██╔════╝██╔════╝██╔════╝
-- ██████╔╝███████║██║     ███████║██╔██╗ ██║██║     █████╗  ███████╗
-- ██╔══██╗██╔══██║██║     ██╔══██║██║╚██╗██║██║     ██╔══╝  ╚════██║
-- ██████╔╝██║  ██║███████╗██║  ██║██║ ╚████║╚██████╗███████╗███████║
-- ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝╚══════╝

CREATE TABLE IF NOT EXISTS balances (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER NOT NULL,
    currency VARCHAR(255) NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    total_qty DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(exchange_id) REFERENCES exchanges(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS balances_unique_idx ON balances(exchange_id, currency);



-- ██████╗  ██████╗ ███████╗██╗████████╗██╗ ██████╗ ███╗   ██╗███████╗
-- ██╔══██╗██╔═══██╗██╔════╝██║╚══██╔══╝██║██╔═══██╗████╗  ██║██╔════╝
-- ██████╔╝██║   ██║███████╗██║   ██║   ██║██║   ██║██╔██╗ ██║███████╗
-- ██╔═══╝ ██║   ██║╚════██║██║   ██║   ██║██║   ██║██║╚██╗██║╚════██║
-- ██║     ╚██████╔╝███████║██║   ██║   ██║╚██████╔╝██║ ╚████║███████║
-- ╚═╝      ╚═════╝ ╚══════╝╚═╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝

CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    instr_id INTEGER NOT NULL,
    qty DOUBLE PRECISION DEFAULT 0,
    price DOUBLE PRECISION DEFAULT 0,
    liquidation_price DOUBLE PRECISION DEFAULT 0,
    FOREIGN KEY(instr_id) REFERENCES instruments(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS positions_unique_idx ON positions(instr_id);



--  ██████╗ ██████╗ ██████╗ ███████╗██████╗ ███████╗
-- ██╔═══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔════╝
-- ██║   ██║██████╔╝██║  ██║█████╗  ██████╔╝███████╗
-- ██║   ██║██╔══██╗██║  ██║██╔══╝  ██╔══██╗╚════██║
-- ╚██████╔╝██║  ██║██████╔╝███████╗██║  ██║███████║
--  ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(255) NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    instr_id INTEGER,
    exchange_order_id VARCHAR(255),
    order_type VARCHAR(255),
    price DOUBLE PRECISION,
    qty DOUBLE PRECISION,
    order_status VARCHAR(255),
    strat_id INTEGER,
    event_type VARCHAR(255),
    event_key UUID,
    time_open TIMESTAMPTZ,
    time_ack_mkt TIMESTAMPTZ,
    time_filled_mkt TIMESTAMPTZ,
    time_cancel TIMESTAMPTZ,
    time_canceled_mkt TIMESTAMPTZ,
    time_rejected_mkt TIMESTAMPTZ,
    total_filled DOUBLE PRECISION DEFAULT 0,
    FOREIGN KEY(instr_id) REFERENCES instruments(id)
);

SELECT create_hypertable(
    'orders',
    'time',
    chunk_time_interval => INTERVAL '1 day'
);

CREATE INDEX IF NOT EXISTS orders_idx ON orders(id);
CREATE INDEX IF NOT EXISTS orders_instr_time_idx ON orders(instr_id, time DESC);



-- ████████╗██████╗  █████╗ ██████╗ ███████╗███████╗        ███████╗██╗  ██╗███████╗ ██████╗
-- ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝        ██╔════╝╚██╗██╔╝██╔════╝██╔════╝
--    ██║   ██████╔╝███████║██║  ██║█████╗  ███████╗        █████╗   ╚███╔╝ █████╗  ██║
--    ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ╚════██║        ██╔══╝   ██╔██╗ ██╔══╝  ██║
--    ██║   ██║  ██║██║  ██║██████╔╝███████╗███████║███████╗███████╗██╔╝ ██╗███████╗╚██████╗
--    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝


CREATE TABLE IF NOT EXISTS trades_exec (
    id VARCHAR(255) NOT NULL, -- same id as orders id
    time TIMESTAMPTZ NOT NULL,
    exchange_order_id VARCHAR(255) NOT NULL,
    instr_id INTEGER NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    fee DOUBLE PRECISION,
    order_type VARCHAR(255) NOT NULL,
    is_liquidation BOOL DEFAULT FALSE,
    FOREIGN KEY(instr_id) REFERENCES instruments(id)
);

SELECT create_hypertable(
    'trades_exec',
    'time',
    chunk_time_interval => INTERVAL '1 day'
);

CREATE INDEX IF NOT EXISTS trades_exec_idx ON trades_exec(id);
CREATE INDEX IF NOT EXISTS trades_exec_instr_time_idx ON trades_exec(instr_id, time DESC);



-- ████████╗██████╗  █████╗ ██████╗ ███████╗███████╗
-- ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝
--    ██║   ██████╔╝███████║██║  ██║█████╗  ███████╗
--    ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ╚════██║
--    ██║   ██║  ██║██║  ██║██████╔╝███████╗███████║
--    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝

CREATE TABLE IF NOT EXISTS trades (
    id VARCHAR(255) NOT NULL, -- same id as orders id
    time TIMESTAMPTZ NOT NULL,
    exchange_order_id VARCHAR(255) NOT NULL,
    instr_id INTEGER NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    order_type VARCHAR(255) NOT NULL,
    is_liquidation BOOL DEFAULT FALSE,
    trade_count INTEGER DEFAULT 1,
    FOREIGN KEY(instr_id) REFERENCES instruments(id)
);

SELECT create_hypertable(
    'trades',
    'time',
    chunk_time_interval => INTERVAL '1 day'
);

CREATE INDEX IF NOT EXISTS trades_idx ON trades(id);
CREATE INDEX IF NOT EXISTS trades_instr_time_idx ON trades(instr_id, time DESC);



-- ██╗      █████╗ ████████╗███████╗███╗   ██╗ ██████╗██╗███████╗███████╗
-- ██║     ██╔══██╗╚══██╔══╝██╔════╝████╗  ██║██╔════╝██║██╔════╝██╔════╝
-- ██║     ███████║   ██║   █████╗  ██╔██╗ ██║██║     ██║█████╗  ███████╗
-- ██║     ██╔══██║   ██║   ██╔══╝  ██║╚██╗██║██║     ██║██╔══╝  ╚════██║
-- ███████╗██║  ██║   ██║   ███████╗██║ ╚████║╚██████╗██║███████╗███████║
-- ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝╚══════╝╚══════╝

CREATE TABLE IF NOT EXISTS latencies (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    time TIMESTAMPTZ NOT NULL,
    event_id UUID NOT NULL,
    event_type VARCHAR(255) NOT NULL
);

SELECT create_hypertable(
    'latencies',
    'time',
    chunk_time_interval => INTERVAL '1 day'
);



-- ███████╗████████╗██████╗  █████╗ ████████╗███████╗ ██████╗██╗   ██╗     ██╗███╗   ██╗███████╗ ██████╗ ███████╗
-- ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚══██╔══╝██╔════╝██╔════╝╚██╗ ██╔╝     ██║████╗  ██║██╔════╝██╔═══██╗██╔════╝
-- ███████╗   ██║   ██████╔╝███████║   ██║   █████╗  ██║  ███╗╚████╔╝      ██║██╔██╗ ██║█████╗  ██║   ██║███████╗
-- ╚════██║   ██║   ██╔══██╗██╔══██║   ██║   ██╔══╝  ██║   ██║ ╚██╔╝       ██║██║╚██╗██║██╔══╝  ██║   ██║╚════██║
-- ███████║   ██║   ██║  ██║██║  ██║   ██║   ███████╗╚██████╔╝  ██║███████╗██║██║ ╚████║██║     ╚██████╔╝███████║
-- ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝ ╚═════╝   ╚═╝╚══════╝╚═╝╚═╝  ╚═══╝╚═╝      ╚═════╝ ╚══════╝

CREATE TABLE IF NOT EXISTS strategy_infos (
    time TIMESTAMPTZ NOT NULL,
    order_id UUID, -- same id as orders id
    event_key UUID,
    payload JSONB NOT NULL,
    CHECK (order_id IS NOT NULL or event_key IS NOT NULL)
);

SELECT create_hypertable(
    'strategy_infos',
    'time',
    chunk_time_interval => INTERVAL '1 day'
);

CREATE INDEX IF NOT EXISTS strategy_infos_order_idx ON strategy_infos(time, order_id);
CREATE INDEX IF NOT EXISTS strategy_infos_event_idx ON strategy_infos(time, event_key);

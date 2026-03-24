CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS market_candles (
    epic VARCHAR(50) NOT NULL,
    resolution VARCHAR(20) NOT NULL,
    time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    open_price DECIMAL(24, 8) NOT NULL,
    high_price DECIMAL(24, 8) NOT NULL,
    low_price DECIMAL(24, 8) NOT NULL,
    close_price DECIMAL(24, 8) NOT NULL,
    volume DECIMAL(24, 2) DEFAULT 0,
    is_final BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (epic, resolution, time)
);

SELECT create_hypertable (
        'market_candles', 'time', if_not_exists => TRUE, migrate_data => TRUE
    );

CREATE INDEX IF NOT EXISTS idx_candles_query ON market_candles (epic, resolution, time DESC);

ALTER TABLE market_candles
SET (
        timescaledb.compress,
        timescaledb.compress_segmentby = 'epic, resolution'
    );

SELECT add_compression_policy (
        'market_candles', INTERVAL '7 days', if_not_exists => TRUE
    );

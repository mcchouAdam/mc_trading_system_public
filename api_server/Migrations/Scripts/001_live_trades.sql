CREATE TABLE IF NOT EXISTS trades (
    deal_id          TEXT PRIMARY KEY,
    deal_reference   TEXT,
    strategy         TEXT,
    source           TEXT NOT NULL DEFAULT 'AUTO',
    epic             TEXT NOT NULL,
    direction        TEXT NOT NULL,
    size             DECIMAL(18, 8) NOT NULL,
    leverage         INTEGER,
    entry_time       TIMESTAMPTZ NOT NULL,
    entry_price      DECIMAL(24, 8) NOT NULL,
    exit_time        TIMESTAMPTZ,
    exit_price       DECIMAL(24, 8),
    realized_pnl     DECIMAL(18, 4),
    currency         TEXT DEFAULT 'USD',
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trades_strategy    ON trades (strategy, entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_epic        ON trades (epic, entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time  ON trades (entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_source      ON trades (source);

CREATE TABLE IF NOT EXISTS trade_costs (
    id              SERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    deal_id         TEXT REFERENCES trades(deal_id) ON DELETE SET NULL,
    cost_type       TEXT NOT NULL,               -- 'SWAP' | 'TRADE_COMMISSION' | 'TRADE_COMMISSION_GSL'
    amount          DECIMAL(18, 4) NOT NULL,     -- Negative = cost, Positive = rebate
    currency        TEXT DEFAULT 'USD',
    epic            TEXT,
    raw_reference   TEXT,                        -- Capital.com transaction reference
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (date, raw_reference, cost_type)
);

CREATE INDEX IF NOT EXISTS idx_trade_costs_date     ON trade_costs (date DESC);
CREATE INDEX IF NOT EXISTS idx_trade_costs_deal_id  ON trade_costs (deal_id);
CREATE INDEX IF NOT EXISTS idx_trade_costs_type     ON trade_costs (cost_type);

DROP VIEW IF EXISTS trades_with_costs CASCADE;
CREATE OR REPLACE VIEW trades_with_costs AS
SELECT
    t.*,
    COALESCE(SUM(tc.amount) FILTER (WHERE tc.cost_type = 'SWAP'),             0) AS total_swap,
    COALESCE(SUM(tc.amount) FILTER (WHERE tc.cost_type = 'TRADE_COMMISSION'), 0) AS total_commission,
    COALESCE(SUM(tc.amount), 0)                                                  AS total_costs,
    t.realized_pnl + COALESCE(SUM(tc.amount), 0)                                 AS net_pnl
FROM trades t
LEFT JOIN trade_costs tc ON tc.deal_id = t.deal_id
GROUP BY t.deal_id;

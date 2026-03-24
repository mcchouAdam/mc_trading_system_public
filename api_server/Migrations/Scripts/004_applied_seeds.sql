CREATE TABLE IF NOT EXISTS applied_seeds (
    file_name VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

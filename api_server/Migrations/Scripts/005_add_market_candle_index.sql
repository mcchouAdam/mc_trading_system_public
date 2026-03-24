CREATE INDEX IF NOT EXISTS "IX_MarketCandles_Epic_Resolution_Time_Desc" 
ON market_candles (epic, resolution, time DESC);

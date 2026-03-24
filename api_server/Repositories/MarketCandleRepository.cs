using ApiServer.Context;
using ApiServer.Models;
using Microsoft.EntityFrameworkCore;

namespace ApiServer.Repositories;

public class MarketCandleRepository
{
    private readonly TradingDbContext _dbContext;

    public MarketCandleRepository(TradingDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<List<MarketCandleEntity>> GetCandlesAsync(string epic, string resolution, int maxBars, DateTime? beforeTimeUtc = null)
    {
        var query = _dbContext.MarketCandles.Where(c => c.Epic == epic && c.Resolution == resolution);

        if (beforeTimeUtc.HasValue)
        {
            query = query.Where(c => c.Time < beforeTimeUtc.Value);
        }

        return await query
            .OrderByDescending(c => c.Time)
            .Take(maxBars)
            .ToListAsync();
    }

    public async Task<DateTime?> GetLatestCandleTimeAsync(string epic, string resolution)
    {
        var latestCandle = await _dbContext.MarketCandles
            .Where(c => c.Epic == epic && c.Resolution == resolution)
            .OrderByDescending(c => c.Time)
            .Select(c => c.Time)
            .FirstOrDefaultAsync();

        return latestCandle == default ? null : latestCandle;
    }

    public async Task UpsertCandlesAsync(List<MarketCandleEntity> candles)
    {
        if (!candles.Any()) return;

        // Due to the lack of native performant bulk upsert in EF Core, 
        // we use raw SQL to leverage PostgreSQL's ON CONFLICT DO UPDATE.
        var sql = @"INSERT INTO market_candles (epic, resolution, time, open_price, high_price, low_price, close_price, volume, is_final)
                    VALUES (@p0, @p1, @p2, @p3, @p4, @p5, @p6, @p7, @p8)
                    ON CONFLICT (epic, resolution, time) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        is_final = EXCLUDED.is_final";

        foreach (var c in candles)
        {
            await _dbContext.Database.ExecuteSqlRawAsync(sql,
                c.Epic,
                c.Resolution,
                DateTime.SpecifyKind(c.Time, DateTimeKind.Utc),
                c.OpenPrice,
                c.HighPrice,
                c.LowPrice,
                c.ClosePrice,
                c.Volume,
                c.IsFinal ?? true
            );
        }
    }
}

using ApiServer.Services.Interfaces;
using System.Text.Json;
using System.Linq;
using ApiServer.Core;
using ApiServer.Models;
using ApiServer.Context;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using StackExchange.Redis;

namespace ApiServer.Services;

public class MarketDataService : IMarketDataService
{
    private readonly IRedisClient _redisClient;
    private readonly ICapitalService _capitalService;
    private readonly IServiceProvider _serviceProvider;

    public MarketDataService(IRedisClient redisClient, ICapitalService capitalService, IServiceProvider serviceProvider)
    {
        _redisClient = redisClient;
        _capitalService = capitalService;
        _serviceProvider = serviceProvider;
    }

    public async Task<List<CandleModel>> GetKlinesAsync(string epic, string resolution, int maxBars, long? to = null)
    {
        var dbResults = new List<CandleModel>();
        long nowTs = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        bool isHistorical = to.HasValue;

        // 1. Initial Database Inquiry
        using (var scope = _serviceProvider.CreateScope())
        {
            var repo = scope.ServiceProvider.GetRequiredService<ApiServer.Repositories.MarketCandleRepository>();
            
            DateTime? targetTime = isHistorical ? DateTimeOffset.FromUnixTimeSeconds(to!.Value).UtcDateTime : null;
            var results = await repo.GetCandlesAsync(epic, resolution, maxBars, targetTime);

            foreach (var c in results)
            {
                var dt = DateTime.SpecifyKind(c.Time, DateTimeKind.Utc);
                var t = new DateTimeOffset(dt).ToUnixTimeSeconds();
                
                dbResults.Add(new CandleModel {
                    Time = t,
                    Open = (double)c.OpenPrice, High = (double)c.HighPrice,
                    Low = (double)c.LowPrice, Close = (double)c.ClosePrice,
                    Volume = (double)c.Volume
                });
            }
            Console.WriteLine($"[MarketDataService] DB Found {dbResults.Count} bars for {epic} {resolution}");
        }

        // 2. Determine Data Sufficiency
        long resSeconds = GetResolutionSeconds(resolution);
        bool needsSync = false;
        
        if (dbResults.Count == 0) 
        {
            needsSync = true;
        } 
        else 
        {
            long newestInDb = dbResults.First().Time;
            long expectedNewest = to ?? nowTs;
            long targetBase = expectedNewest - (expectedNewest % resSeconds);
            
            // Aggressive Tail Sync: If we don't have the current period's starting candle, sync.
            if (targetBase > newestInDb) 
            {
                needsSync = true;
            }
            
            // Historical volume check
            if (isHistorical && dbResults.Count < maxBars * 0.7) needsSync = true;

            // Internal gap check: Ensure we fill holes in history
            if (!needsSync && dbResults.Count > 1) {
                for (int i = 0; i < Math.Min(dbResults.Count - 1, 50); i++) {
                     if ((dbResults[i].Time - dbResults[i+1].Time) > (resSeconds * 2.5)) {
                        needsSync = true;
                        Console.WriteLine($"[MarketDataService] Internal GAP detected for {epic} {resolution}");
                        break;
                     }
                }
            }
        }

        // 3. Sync & Return Strategy
        if (needsSync)
        {
            // For MINUTE, allow a larger blocking threshold (5 hours = 300 bars) for better UX
            int blockingThreshold = resolution == "MINUTE" ? 300 : 15;

            bool isLatestTailGap = !isHistorical && (dbResults.Count > 0 && 
                (nowTs - dbResults.First().Time) > (resSeconds * 1.1) && 
                (nowTs - dbResults.First().Time) < (resSeconds * blockingThreshold));

            if (dbResults.Count == 0 || (!isHistorical && isLatestTailGap)) {
                int fetchCount = isLatestTailGap ? (blockingThreshold + 5) : maxBars;
                var apiTo = to.HasValue ? DateTimeOffset.FromUnixTimeSeconds(to.Value).UtcDateTime : DateTime.UtcNow;
                Console.WriteLine($"[MarketDataService] SYNC (BLOCK): Fetching {fetchCount} bars from API for {epic} {resolution}");
                
                var apiModels = await FetchMapAndSaveKlinesAsync(epic, resolution, fetchCount, apiTo);
                
                if (apiModels.Count > 0) {
                    var merged = apiModels.Concat(dbResults).GroupBy(x => x.Time).OrderByDescending(x => x.Key).Select(g => g.First()).ToList();
                    dbResults = merged;
                }
            } else if (isHistorical && dbResults.Count < maxBars) {
                var apiTo = to.HasValue ? DateTimeOffset.FromUnixTimeSeconds(to.Value).UtcDateTime : DateTime.UtcNow;
                _ = Task.Run(() => FetchMapAndSaveKlinesAsync(epic, resolution, maxBars, apiTo));
            } else {
                _ = Task.Run(() => SyncGapsAsync(epic, resolution));
            }
        }

        if (dbResults.Count > 0) {
            Console.WriteLine($"[MarketDataService] Returning {dbResults.Count} bars (Newest: {DateTimeOffset.FromUnixTimeSeconds(dbResults.First().Time).UtcDateTime:HH:mm:ss})");
        }

        return dbResults
            .OrderBy(x => x.Time)
            .TakeLast(maxBars)
            .ToList();
    }

    public async Task SyncGapsAsync(string epic, string resolution)
    {
        // Get latest from DB to determine gap
        long nowTs = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        int resSeconds = GetResolutionSeconds(resolution);
        long latestLocalTs = 0;

        // Check DB for latest and check for internal gaps
        using (var scope = _serviceProvider.CreateScope())
        {
            var repo = scope.ServiceProvider.GetRequiredService<ApiServer.Repositories.MarketCandleRepository>();
            var latestCandle = await repo.GetLatestCandleTimeAsync(epic, resolution);

            if (latestCandle.HasValue) {
                latestLocalTs = new DateTimeOffset(DateTime.SpecifyKind(latestCandle.Value, DateTimeKind.Utc)).ToUnixTimeSeconds();
            }

            // Internal Gap Detection for background sync
            if (latestLocalTs > 0) {
                var recentBars = await repo.GetCandlesAsync(epic, resolution, 100);
                if (recentBars.Count > 1) {
                    for (int i = 0; i < recentBars.Count - 1; i++) {
                        var t1 = new DateTimeOffset(DateTime.SpecifyKind(recentBars[i].Time, DateTimeKind.Utc)).ToUnixTimeSeconds();
                        var t2 = new DateTimeOffset(DateTime.SpecifyKind(recentBars[i+1].Time, DateTimeKind.Utc)).ToUnixTimeSeconds();
                        if ((t1 - t2) > (resSeconds * 2.5)) {
                            // Found an internal gap, trigger a larger sync
                            Console.WriteLine($"[MarketDataService] BG SYNC: Internal GAP detected for {epic} {resolution} at {recentBars[i].Time:HH:mm}. Filling...");
                            await FetchMapAndSaveKlinesAsync(epic, resolution, 300);
                            return; 
                        }
                    }
                }
            }
        }

        if (latestLocalTs > 0 && (nowTs - latestLocalTs) > (resSeconds * 1.5))
        {
            int fillCount = (int)((nowTs - latestLocalTs) / resSeconds) + 5;
            if (fillCount > 0) {
                Console.WriteLine($"[MarketDataService] BG SYNC: GAP Detected for {epic} {resolution}: {nowTs - latestLocalTs}s gap. Filling {fillCount} bars...");
                await FetchMapAndSaveKlinesAsync(epic, resolution, Math.Min(fillCount, 500));
            }
        }
    }

    private int GetResolutionSeconds(string res) => res switch {
        "MINUTE" => 60, "MINUTE_5" => 300, "MINUTE_15" => 900,
        "HOUR" => 3600, "HOUR_1" => 3600, "HOUR_4" => 14400, "DAY" => 86400,
        _ => 60
    };

    private List<CandleModel> MapApiResultsToModels(string resolution, IEnumerable<dynamic> apiBars)
    {
        var models = new List<CandleModel>();
        int resSeconds = GetResolutionSeconds(resolution);
        foreach (dynamic item in apiBars)
        {
            long t = (long)item.time;
            if (t > 1000000000000) t /= 1000;
            
            // Align to resolution bin boundary
            t = t - (t % resSeconds);

            models.Add(new CandleModel
            {
                Time = t,
                Open = (double)item.open,
                High = (double)item.high,
                Low = (double)item.low,
                Close = (double)item.close,
                Volume = 0
            });
        }
        return models;
    }

    private async Task<List<CandleModel>> FetchMapAndSaveKlinesAsync(string epic, string resolution, int count, DateTime? to = null)
    {
        var apiBars = await _capitalService.GetKlinesAsync(epic, resolution, count, to);
        var models = MapApiResultsToModels(resolution, apiBars);
        if (models.Count > 0)
        {
            await SaveMissingToDbAsync(epic, resolution, models);
        }
        return models;
    }

    private async Task SaveMissingToDbAsync(string epic, string resolution, List<CandleModel> bars)
    {
        using var scope = _serviceProvider.CreateScope();
        var repo = scope.ServiceProvider.GetRequiredService<ApiServer.Repositories.MarketCandleRepository>();
        
        var entities = bars.Select(b => new MarketCandleEntity {
            Epic = epic,
            Resolution = resolution,
            Time = DateTimeOffset.FromUnixTimeSeconds(b.Time).UtcDateTime,
            OpenPrice = (decimal)b.Open,
            HighPrice = (decimal)b.High,
            LowPrice = (decimal)b.Low,
            ClosePrice = (decimal)b.Close,
            Volume = (decimal)b.Volume,
            IsFinal = true
        }).ToList();

        await repo.UpsertCandlesAsync(entities);
    }
}

using ApiServer.Core;
using ApiServer.Services.Interfaces;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;

namespace ApiServer.BackgroundTasks;

public class MarketDataSyncTask : BaseBackgroundService
{
    private readonly IServiceProvider _serviceProvider;
    private readonly string[] _defaultEpics = { "BTCUSD", "US100" };
    private readonly string[] _resolutions = { "MINUTE", "MINUTE_5", "MINUTE_15", "HOUR", "HOUR_1", "HOUR_4", "DAY" };

    public MarketDataSyncTask(IServiceProvider serviceProvider, ILogger<MarketDataSyncTask> logger)
        : base(logger)
    {
        _serviceProvider = serviceProvider;
    }

    protected override async Task ExecuteWorkAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Starting Market Data Background Sync Task...");

        // Initial holdup to let system warm up
        await Task.Delay(10000, stoppingToken);

        while (!stoppingToken.IsCancellationRequested)
        {
            using (var scope = _serviceProvider.CreateScope())
            {
                var redisClient = scope.ServiceProvider.GetRequiredService<IRedisClient>();
                var marketDataService = scope.ServiceProvider.GetRequiredService<IMarketDataService>();

                string[] epicsToSync = await GetEpicsFromRedis(redisClient);

                _logger.LogInformation("Cycle Started: Synchronizing {EpicCount} epics across {ResCount} resolutions...", epicsToSync.Length, _resolutions.Length);

                foreach (var epic in epicsToSync)
                {
                    foreach (var res in _resolutions)
                    {
                        if (stoppingToken.IsCancellationRequested) break;

                        await marketDataService.SyncGapsAsync(epic, res);
                        await Task.Delay(2000, stoppingToken);
                    }
                }
            }

            _logger.LogInformation("Cycle Finished. Next sync in 30 minutes.");
            await Task.Delay(TimeSpan.FromMinutes(30), stoppingToken);
        }
    }

    private async Task<string[]> GetEpicsFromRedis(IRedisClient redis)
    {
        var db = redis.GetDatabase();
        var value = await db.StringGetAsync("MARKET_DATA_SUBSCRIBE");
        
        if (value.HasValue)
        {
            var epics = JsonSerializer.Deserialize<string[]>(value.ToString());
            if (epics != null && epics.Length > 0) return epics;
        }

        return _defaultEpics;
    }
}

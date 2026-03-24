using ApiServer.Services.Interfaces;
using ApiServer.Core;
using ApiServer.Models;
using StackExchange.Redis;
using System.Text.Json;

namespace ApiServer.Services;

public class SystemService : ISystemService
{
    private readonly IRedisClient _redisClient;

    public SystemService(IRedisClient redisClient)
    {
        _redisClient = redisClient;
    }

    public async Task<List<string>> GetWatchlistAsync()
    {
        var db = _redisClient.GetDatabase();
        var cached = await db.StringGetAsync("MARKET_DATA_SUBSCRIBE");
        if (cached.HasValue)
        {
            var epics = JsonSerializer.Deserialize<List<string>>((string)cached!);
            if (epics != null)
            {
                epics.Sort();
                return epics;
            }
        }
        return new List<string>();
    }

    public async Task<List<StrategyInstance>> GetActiveStrategiesAsync()
    {
        var db = _redisClient.GetDatabase();
        var cached = await db.StringGetAsync("ACTIVE_STRATEGIES");
        if (cached.HasValue)
        {
            return JsonSerializer.Deserialize<List<StrategyInstance>>((string)cached!) ?? new List<StrategyInstance>();
        }
        return new List<StrategyInstance>();
    }

    public async Task UpdateActiveStrategiesAsync(List<StrategyInstance> strategies)
    {
        var db = _redisClient.GetDatabase();
        var pubsub = _redisClient.GetSubscriber();
        await db.StringSetAsync("ACTIVE_STRATEGIES", JsonSerializer.Serialize(strategies));
        await pubsub.PublishAsync(RedisChannel.Literal("CHANNEL_STRATEGY_UPDATED"), "updated");
    }

    public async Task UpdateMarketDataSubAsync(List<string> epics)
    {
        var db = _redisClient.GetDatabase();
        var pubsub = _redisClient.GetSubscriber();
        await db.StringSetAsync("MARKET_DATA_SUBSCRIBE", JsonSerializer.Serialize(epics));
        await pubsub.PublishAsync(RedisChannel.Literal("CHANNEL_CONFIG_UPDATED"), "updated");
    }

    public async Task UpdateOhlcDataSubAsync(List<OhlcDataSubscription> subs)
    {
        var db = _redisClient.GetDatabase();
        var pubsub = _redisClient.GetSubscriber();
        await db.StringSetAsync("OHLC_DATA_SUBSCRIBE", JsonSerializer.Serialize(subs));
        await pubsub.PublishAsync(RedisChannel.Literal("CHANNEL_CONFIG_UPDATED"), "updated");
    }

    public async Task<TradingSettings> GetTradingSettingsAsync()
    {
        var db = _redisClient.GetDatabase();
        var cached = await db.StringGetAsync("TRADING_SETTINGS");
        if (cached.HasValue)
        {
            return JsonSerializer.Deserialize<TradingSettings>((string)cached!) ?? new TradingSettings();
        }
        return new TradingSettings();
    }

    public async Task UpdateTradingSettingsAsync(TradingSettings settings)
    {
        var db = _redisClient.GetDatabase();
        await db.StringSetAsync("TRADING_SETTINGS", JsonSerializer.Serialize(settings));
    }

    public Dictionary<string, bool> GetMlSupport()
    {
        var support = new Dictionary<string, bool>();
        string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "machine_learning", "model_registry.json");
        if (!System.IO.File.Exists(path))
        {
            path = "machine_learning/model_registry.json";
        }

        if (System.IO.File.Exists(path))
        {
            var json = System.IO.File.ReadAllText(path);
            using var doc = JsonDocument.Parse(json);
            foreach (var prop in doc.RootElement.EnumerateObject())
            {
                if (prop.Name.StartsWith("_")) continue;

                bool enabled = false;
                if (prop.Value.TryGetProperty("enabled", out var enabledProp))
                {
                    enabled = enabledProp.GetBoolean();
                }

                bool hasProduction = prop.Value.TryGetProperty("production", out var prodProp) &&
                                   prodProp.ValueKind != JsonValueKind.Null;

                support[prop.Name] = enabled && hasProduction;
            }
        }
        return support;
    }
}

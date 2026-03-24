using ApiServer.Services.Interfaces;
using System.Text.Json;
using System.Globalization;
using StackExchange.Redis;
using ApiServer.Core;

namespace ApiServer.Services;

public class RiskService : IRiskService
{
    private readonly IRedisClient _redisClient;

    public RiskService(IRedisClient redisClient)
    {
        _redisClient = redisClient;
    }

    public async Task<Models.RiskStatus> GetRiskStatusAsync()
    {
        var db = _redisClient.GetDatabase();
        var cached = await db.StringGetAsync("CACHED_RISK_STATUS");
        
        if (cached.HasValue)
        {
            return JsonSerializer.Deserialize<Models.RiskStatus>((string)cached!) ?? new Models.RiskStatus();
        }
        
        return new Models.RiskStatus();
    }

    public async Task ResumeAsync()
    {
        var db = _redisClient.GetDatabase();
        await db.HashSetAsync("RISK_STATE", new HashEntry[] {
            new HashEntry("resume_override", "true"),
            new HashEntry("engine_halt_status", "false"),
            new HashEntry("manual_halt_status", "false")
        });
    }

    public async Task UpdateLimitsAsync(Models.RiskLimitUpdate update)
    {
        var db = _redisClient.GetDatabase();
        await db.HashSetAsync("RISK_STATE", new HashEntry[] {
            new HashEntry("daily_limit", update.DailyLimitPct.ToString(CultureInfo.InvariantCulture)),
            new HashEntry("daily_enabled", update.DailyLimitEnabled.ToString().ToLower()),
            new HashEntry("monthly_limit", update.MonthlyLimitPct.ToString(CultureInfo.InvariantCulture)),
            new HashEntry("monthly_enabled", update.MonthlyLimitEnabled.ToString().ToLower())
        });
    }

    public async Task SetManualHaltAsync(bool isHalted)
    {
        var db = _redisClient.GetDatabase();
        await db.HashSetAsync("RISK_STATE", "manual_halt_status", isHalted.ToString().ToLower());
    }
}

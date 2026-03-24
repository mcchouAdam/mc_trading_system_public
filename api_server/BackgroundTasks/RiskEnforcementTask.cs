using System.Text.Json;
using System.Text.Json.Nodes;
using System.Globalization;
using ApiServer.Core;
using ApiServer.Services;
using ApiServer.Models;
using Microsoft.AspNetCore.SignalR;
using ApiServer.Hubs;
using ApiServer.Services.Interfaces;
using StackExchange.Redis;

namespace ApiServer.BackgroundTasks;

public class RiskEnforcementTask : BaseBackgroundService
{
    private readonly IRedisClient _redisClient;
    private readonly IHubContext<TradeHub> _hubContext;

    public RiskEnforcementTask(IRedisClient redisClient, IHubContext<TradeHub> hubContext, ILogger<RiskEnforcementTask> logger)
        : base(logger)
    {
        _redisClient = redisClient;
        _hubContext = hubContext;
    }

    protected override async Task ExecuteWorkAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Starting Risk Enforcement Task (Redis-based)...");

        while (!stoppingToken.IsCancellationRequested)
        {
            var startTime = DateTime.UtcNow;

            try
            {
                var db = _redisClient.GetDatabase();

                // 1. Read everything from Redis (atomic read for this state)
                var riskMap = (await db.HashGetAllAsync("RISK_STATE")).ToDictionary(x => x.Name.ToString(), x => x.Value.ToString());
                var accStateMap = (await db.HashGetAllAsync("ACCOUNT_STATE")).ToDictionary(x => x.Name.ToString(), x => x.Value.ToString());
                var accLatestMap = (await db.HashGetAllAsync("ACCOUNT_LATEST")).ToDictionary(x => x.Name.ToString(), x => x.Value.ToString());
                var tradesJson = await db.StringGetAsync("CACHED_OPEN_TRADES");

                // 2. Parse Current State
                double.TryParse(accLatestMap.GetValueOrDefault("balance"), NumberStyles.Any, CultureInfo.InvariantCulture, out var currentBalance);
                double.TryParse(accLatestMap.GetValueOrDefault("unrealized_pnl"), NumberStyles.Any, CultureInfo.InvariantCulture, out var currentPnL);
                var currentEquity = currentBalance + currentPnL;

                double.TryParse(accStateMap.GetValueOrDefault("start_day_balance"), NumberStyles.Any, CultureInfo.InvariantCulture, out var startOfDayBal);
                double.TryParse(accStateMap.GetValueOrDefault("start_month_balance"), NumberStyles.Any, CultureInfo.InvariantCulture, out var startOfMonthBal);

                // 3. Construct Risk Status Object
                var status = new RiskStatus
                {
                    AccountId = accLatestMap.GetValueOrDefault("account_id") ?? "",
                    Balance = currentBalance,
                    Equity = currentEquity,
                    DailyPnLPct = startOfDayBal > 0 ? Math.Round(((currentEquity - startOfDayBal) / startOfDayBal) * 100, 2) : 0,
                    MonthlyPnLPct = startOfMonthBal > 0 ? Math.Round(((currentEquity - startOfMonthBal) / startOfMonthBal) * 100, 2) : 0,
                    IsHalted = riskMap.GetValueOrDefault("engine_halt_status") == "true" || riskMap.GetValueOrDefault("manual_halt_status") == "true",
                    HaltReason = riskMap.GetValueOrDefault("engine_halt_reason") ?? "",
                    DailyLimitPct = double.TryParse(riskMap.GetValueOrDefault("daily_limit"), out var dl) ? dl : 5.0,
                    DailyLimitEnabled = riskMap.GetValueOrDefault("daily_enabled") != "false",
                    MonthlyLimitPct = double.TryParse(riskMap.GetValueOrDefault("monthly_limit"), out var ml) ? ml : 10.0,
                    MonthlyLimitEnabled = riskMap.GetValueOrDefault("monthly_enabled") != "false",
                    StartDayBalance = startOfDayBal,
                    StartMonthBalance = startOfMonthBal,
                    IsResumeOverride = riskMap.GetValueOrDefault("resume_override") == "true",
                    CanResume = (riskMap.GetValueOrDefault("engine_halt_status") == "true" || riskMap.GetValueOrDefault("manual_halt_status") == "true") && riskMap.GetValueOrDefault("resume_override") != "true"
                };

                // 4. Risk Enforcement (CRITICAL: Active Protection)
                if (!status.IsHalted && !status.IsResumeOverride && startOfDayBal > 0)
                {
                    string? haltReason = null;
                    if (status.DailyLimitEnabled && status.DailyPnLPct <= -Math.Abs(status.DailyLimitPct))
                        haltReason = $"Daily Drawdown Limit Exceeded: {status.DailyPnLPct}% (Limit: -{status.DailyLimitPct}%)";
                    else if (status.MonthlyLimitEnabled && status.MonthlyPnLPct <= -Math.Abs(status.MonthlyLimitPct))
                        haltReason = $"Monthly Drawdown Limit Exceeded: {status.MonthlyPnLPct}% (Limit: -{status.MonthlyLimitPct}%)";

                    if (haltReason != null)
                    {
                        _logger.LogWarning("RISK TRIGGER {Reason}", haltReason);
                        await db.HashSetAsync("RISK_STATE", new HashEntry[] {
                            new HashEntry("engine_halt_status", "true"),
                            new HashEntry("engine_halt_reason", haltReason)
                        });
                        status.IsHalted = true;
                        status.HaltReason = haltReason;
                    }
                }

                // 5. Broadcast to Frontend
                var trades = tradesJson.HasValue ? JsonSerializer.Deserialize<List<OpenTrade>>((string)tradesJson!) : new List<OpenTrade>();
                
                await db.StringSetAsync("CACHED_RISK_STATUS", JsonSerializer.Serialize(status));
                await _hubContext.Clients.All.SendAsync(HubEvents.ACCOUNT_INFO, new { risk = status, trades = trades }, stoppingToken);

            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in RiskEnforcementTask loop.");
            }

            // High frequency risk check: 500ms
            var elapsed = (DateTime.UtcNow - startTime).TotalMilliseconds;
            var waitTime = Math.Max(50, 500 - (int)elapsed);
            await Task.Delay(waitTime, stoppingToken);
        }
    }
}

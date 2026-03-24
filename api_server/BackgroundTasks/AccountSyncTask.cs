using System.Text.Json;
using System.Text.Json.Nodes;
using System.Globalization;
using ApiServer.Core;
using ApiServer.Services.Interfaces;
using ApiServer.Models;
using StackExchange.Redis;

namespace ApiServer.BackgroundTasks;

public class AccountSyncTask : BaseBackgroundService
{
    private readonly IServiceProvider _serviceProvider;
    private readonly IRedisClient _redisClient;

    public AccountSyncTask(IServiceProvider serviceProvider, IRedisClient redisClient, ILogger<AccountSyncTask> logger)
        : base(logger)
    {
        _serviceProvider = serviceProvider;
        _redisClient = redisClient;
    }

    protected override async Task ExecuteWorkAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Starting Account Sync Task (API/DB)...");

        while (!stoppingToken.IsCancellationRequested)
        {
            var startTime = DateTime.UtcNow;

            try
            {
                using (var scope = _serviceProvider.CreateScope())
                {
                    var capitalService = scope.ServiceProvider.GetRequiredService<ICapitalService>();
                    var tradeService = scope.ServiceProvider.GetRequiredService<ITradeService>();
                    var db = _redisClient.GetDatabase();

                    var nowLocal = DateTime.UtcNow.AddHours(8);
                    var todayLocal = nowLocal.ToString("yyyy-MM-dd");
                    var startOfTodayLocal = $"{todayLocal} 00:00:00+08";

                    // 1. Parallel Fetching (External API & DB)
                    var accountsTask = capitalService.GetAccountsAsync();
                    var positionsTask = capitalService.GetOpenPositionsAsync();
                    var dbStatsTask = tradeService.GetHistoricalTradesAsync(startOfTodayLocal, null, 1, 1);

                    await Task.WhenAll(accountsTask, positionsTask, dbStatsTask);

                    var accsResponse = await accountsTask;
                    var tradesResp = await positionsTask;
                    var (_, _, realizedToday) = await dbStatsTask;

                    // Update Realized PnL Cache
                    await db.StringSetAsync("STAT:DAILY_REALIZED_PNL", realizedToday.ToString(CultureInfo.InvariantCulture));

                    // 2. Process Account Data
                    if (accsResponse != null)
                    {
                        var accs = accsResponse["accounts"]?.AsArray();
                        if (accs != null && accs.Count > 0)
                        {
                            var acc = accs.FirstOrDefault(a => (string?)a?["preferred"]?.ToString()?.ToLower() == "true") ?? accs[0];
                            var balanceData = acc?["balance"];
                            if (balanceData != null)
                            {
                                double.TryParse(balanceData["balance"]?.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out var currentBalance);
                                double.TryParse(balanceData["profitLoss"]?.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out var currentPnL);

                                // Save latest balance to Redis for RiskEnforcement to use
                                await db.HashSetAsync("ACCOUNT_LATEST", new HashEntry[] {
                                    new HashEntry("balance", currentBalance.ToString(CultureInfo.InvariantCulture)),
                                    new HashEntry("unrealized_pnl", currentPnL.ToString(CultureInfo.InvariantCulture)),
                                    new HashEntry("account_id", (string?)acc?["accountId"] ?? ""),
                                    new HashEntry("updated_at", DateTime.UtcNow.ToString("O"))
                                });

                                // Day/Month Reset Logic
                                var accMap = (await db.HashGetAllAsync("ACCOUNT_STATE")).ToDictionary(x => x.Name.ToString(), x => x.Value.ToString());
                                var lastResetDay = accMap.GetValueOrDefault("last_reset_day") ?? "";

                                if (lastResetDay != todayLocal)
                                {
                                    _logger.LogInformation("New day detected ({Date}). Resetting start balances...", todayLocal);
                                    await db.HashSetAsync("RISK_STATE", new HashEntry[] {
                                        new HashEntry("engine_halt_status", "false"),
                                        new HashEntry("engine_halt_reason", ""),
                                        new HashEntry("resume_override", "false")
                                    });

                                    await db.HashSetAsync("ACCOUNT_STATE", new HashEntry[] {
                                        new HashEntry("start_day_balance", currentBalance.ToString(CultureInfo.InvariantCulture)),
                                        new HashEntry("last_reset_day", todayLocal)
                                    });

                                    var currentMonth = nowLocal.ToString("yyyy-MM");
                                    var lastResetMonth = accMap.GetValueOrDefault("last_reset_month") ?? "";
                                    if (lastResetMonth != currentMonth)
                                    {
                                        await db.HashSetAsync("ACCOUNT_STATE", new HashEntry[] {
                                            new HashEntry("start_month_balance", currentBalance.ToString(CultureInfo.InvariantCulture)),
                                            new HashEntry("last_reset_month", currentMonth)
                                        });
                                    }
                                }
                                else
                                {
                                    // Ensure values exist if not set yet
                                    if (!accMap.ContainsKey("start_day_balance"))
                                        await db.HashSetAsync("ACCOUNT_STATE", "start_day_balance", currentBalance.ToString(CultureInfo.InvariantCulture));
                                    if (!accMap.ContainsKey("start_month_balance"))
                                        await db.HashSetAsync("ACCOUNT_STATE", "start_month_balance", currentBalance.ToString(CultureInfo.InvariantCulture));
                                }
                            }
                        }
                    }

                    // 3. Process Positions & Active Sync
                    if (tradesResp != null)
                    {
                        var positions = tradesResp["positions"]?.AsArray();
                        if (positions != null)
                        {
                            var dealIds = positions.Select(p => (string?)p?["position"]?["dealId"]).Where(id => !string.IsNullOrEmpty(id)).Cast<string>().ToList();
                            var metadata = await tradeService.GetTradeMetadataAsync(dealIds);

                            // Active Sync (60s timer)
                            var lastSync = await db.StringGetAsync("LAST_TRADE_SYNC_TIME");
                            if (lastSync.IsNull || (DateTime.UtcNow - DateTime.Parse(lastSync!)).TotalSeconds > 60)
                            {
                                await ActiveSyncTradesAsync(capitalService, tradeService, dealIds);
                                await db.StringSetAsync("LAST_TRADE_SYNC_TIME", DateTime.UtcNow.ToString());
                            }

                            List<OpenTrade> trades = new();
                            foreach (var pos in positions)
                            {
                                var p = pos?["position"];
                                var m = pos?["market"];
                                if (p != null && m != null)
                                {
                                    var dealId = (string?)p["dealId"] ?? "";
                                    var (stra, res, slStored, tpStored) = metadata.GetValueOrDefault(dealId, ("MANUAL", "-", 0.0, 0.0));
                                    trades.Add(new OpenTrade
                                    {
                                        DealId = dealId,
                                        Epic = (string?)m["epic"] ?? "",
                                        Direction = (string?)p["direction"] ?? "BUY",
                                        UnrealizedPnL = double.TryParse(p["upl"]?.ToString(), out var u) ? u : 0,
                                        Size = double.TryParse(p["size"]?.ToString(), out var s) ? s : 0,
                                        Strategy = stra,
                                        Resolution = res,
                                        EntryPrice = double.TryParse(p["level"]?.ToString(), out var l) ? l : 0,
                                        EntryTime = ((string?)p["createdDateUTC"] ?? "").Split('.')[0].Replace("T", " "),
                                        StopLevel = (double.TryParse(p["stopLevel"]?.ToString(), out var slV) && slV != 0) ? (double?)slV : null,
                                        ProfitLevel = (double.TryParse(p["profitLevel"]?.ToString(), out var plV) && plV != 0) ? (double?)plV :
                                                      (double.TryParse(p["limitLevel"]?.ToString(), out var llV) && llV != 0) ? (double?)llV :
                                                      (double.TryParse(p["limit"]?.ToString(), out var lmtV) && lmtV != 0) ? (double?)lmtV : null
                                    });
                                }
                            }
                            await db.StringSetAsync("CACHED_OPEN_TRADES", JsonSerializer.Serialize(trades));
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in AccountSyncTask loop.");
            }

            // Target roughly 2 seconds frequency for API sync to stay within rate limits but keep data fresh
            var elapsed = (DateTime.UtcNow - startTime).TotalMilliseconds;
            var waitTime = Math.Max(500, 2000 - (int)elapsed);
            await Task.Delay(waitTime, stoppingToken);
        }
    }

    private async Task ActiveSyncTradesAsync(ICapitalService capitalService, ITradeService tradeService, List<string> openDealIdsFromBroker)
    {
        var txResp = await capitalService.GetTransactionsAsync(120);
        if (txResp == null) return;

        var transactions = txResp["transactions"]?.AsArray();
        if (transactions == null || transactions.Count == 0) return;

        var openDealIdsFromDb = await tradeService.GetOpenTradeDealIdsAsync();
        if (openDealIdsFromDb.Count == 0) return;

        var metadata = await tradeService.GetTradeMetadataAsync(openDealIdsFromDb);

        foreach (var tx in transactions)
        {
            var transactionType = (string?)tx?["transactionType"];
            var note = (string?)tx?["note"] ?? "";
            var dealId = (string?)tx?["dealId"];

            if (string.IsNullOrEmpty(dealId) || !openDealIdsFromDb.Contains(dealId)) continue;
            
            // If it's closed in broker transactions but we still have it as open in DB
            if (transactionType == "TRADE" && note.Contains("closed", StringComparison.OrdinalIgnoreCase))
            {
                double.TryParse(tx?["size"]?.ToString(), out var pnl);
                var dateUtcStr = (string?)tx?["dateUtc"] ?? (string?)tx?["date"] ?? "";
                if (!DateTime.TryParse(dateUtcStr, out var exitTime)) exitTime = DateTime.UtcNow;

                var (stra, res, slStored, tpStored) = metadata.GetValueOrDefault(dealId, ("MANUAL", "-", 0.0, 0.0));
                double exitPrice = pnl > 0 ? tpStored : slStored;
                string exitType = pnl > 0 ? "TP" : "SL";

                _logger.LogInformation("[SYNC] Auto-syncing broker-side close for {DealId}.", dealId);
                await tradeService.UpdateTradeClosingAsync(dealId, exitPrice, exitTime, pnl, exitType);
            }
        }
    }
}

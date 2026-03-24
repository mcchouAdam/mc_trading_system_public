using ApiServer.Services.Interfaces;
using ApiServer.Models;
using ApiServer.Repositories;
using ApiServer.Core;
using ApiServer.Hubs;
using StackExchange.Redis;
using System.Text.Json;
using Microsoft.AspNetCore.SignalR;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Nodes;

namespace ApiServer.Services;

public class TradeService : ITradeService
{
    private readonly TradeRepository _tradeRepository;
    private readonly IRedisClient _redisClient;
    private readonly IRiskService _riskService;
    private readonly ICapitalService _capitalService;
    private readonly IHubContext<TradeHub> _hubContext;

    public TradeService(TradeRepository tradeRepository, IRedisClient redisClient, IRiskService riskService, ICapitalService capitalService, IHubContext<TradeHub> hubContext)
    {
        _tradeRepository = tradeRepository;
        _redisClient = redisClient;
        _riskService = riskService;
        _capitalService = capitalService;
        _hubContext = hubContext;
    }

    public async Task<List<OpenTrade>> GetCachedOpenTradesAsync()
    {
        var db = _redisClient.GetDatabase();
        var cached = await db.StringGetAsync("CACHED_OPEN_TRADES");
        if (cached.HasValue)
        {
            return JsonSerializer.Deserialize<List<OpenTrade>>((string)cached!) ?? new List<OpenTrade>();
        }
        return new List<OpenTrade>();
    }

    public async Task<(List<ClosedTrade> Items, int TotalCount, double TotalPnL)> GetHistoricalTradesAsync(string? fromDate, string? toDate, int page = 1, int pageSize = 10)
    {
        var (dbTrades, totalCount, totalPnL) = await _tradeRepository.GetHistoricalTradesAsync(fromDate, toDate, page, pageSize);

        var trades = dbTrades.Select(t => new ClosedTrade
        {
            Id = t.DealId,
            Epic = t.Epic,
            Strategy = t.Strategy,
            Direction = t.Direction,
            Size = (double)t.Size,
            EntryTime = t.EntryTime.ToString("yyyy-MM-dd HH:mm:ss"),
            ExitTime = t.ExitTime?.ToString("yyyy-MM-dd HH:mm:ss") ?? "",
            EntryPrice = (double)t.EntryPrice,
            ExitPrice = (double)(t.ExitPrice ?? 0),
            PnL = (double)(t.RealizedPnl ?? 0),
            ExitType = t.ExitType,
            StopLoss = t.StopLoss,
            TakeProfit = t.TakeProfit
        }).ToList();

        return (trades, totalCount, totalPnL);
    }

    public async Task<Dictionary<string, (string Strategy, string Resolution, double StopLoss, double TakeProfit)>> GetTradeMetadataAsync(IEnumerable<string> dealIds)
    {
        var metadata = new Dictionary<string, (string Strategy, string Resolution, double StopLoss, double TakeProfit)>(StringComparer.OrdinalIgnoreCase);
        if (!dealIds.Any()) return metadata;

        var trades = await _tradeRepository.GetTradesByDealIdsAsync(dealIds);

        foreach (var t in trades)
        {
            var stra = string.IsNullOrEmpty(t.Strategy) ? "MANUAL" : t.Strategy;
            var res = string.IsNullOrEmpty(t.Resolution) ? "-" : t.Resolution;
            var sl = t.StopLoss ?? 0;
            var tp = t.TakeProfit ?? 0;
            
            metadata[t.DealId] = (stra, res, sl, tp);
        }
        return metadata;
    }

    public async Task<List<string>> GetOpenTradeDealIdsAsync()
    {
        return await _tradeRepository.GetOpenTradeDealIdsAsync();
    }

    public async Task UpdateTradeClosingAsync(string dealId, double exitPrice, DateTime exitTime, double realizedPnL, string exitType)
    {
        await _tradeRepository.UpdateTradeClosingAsync(dealId, exitPrice, exitTime, realizedPnL, exitType);
    }

    public async Task PlaceOrderAsync(string epic, string direction, double size, double? stopLoss, double? takeProfit)
    {
        var riskStatus = await _riskService.GetRiskStatusAsync();
        if (riskStatus.IsHalted)
        {
            throw new Core.Exceptions.ForbiddenException($"Order rejected. System is HALTED: {riskStatus.HaltReason}");
        }

        var pubsub = _redisClient.GetSubscriber();
        var signal = new
        {
            epic = epic,
            action = direction,
            size = size,
            stop_loss = stopLoss,
            take_profit = takeProfit,
            strategy = "MANUAL",
            source = "MANUAL",
            resolution = "TICK"
        };

        var json = JsonSerializer.Serialize(signal);
        await pubsub.PublishAsync(RedisChannel.Literal("TRADE_SIGNALS"), json);
        await _hubContext.Clients.All.SendAsync(HubEvents.TRADE_ACTION, new { action = "order_signal_sent", epic = epic });
    }

    public async Task CloseTradeAsync(string dealId, string? epic)
    {
        var pubsub = _redisClient.GetSubscriber();
        var signal = new
        {
            epic = epic,
            action = "CLOSE",
            deal_id = dealId,
            source = "MANUAL"
        };
        var json = JsonSerializer.Serialize(signal);
        await pubsub.PublishAsync(RedisChannel.Literal("TRADE_SIGNALS"), json);
        await _hubContext.Clients.All.SendAsync(HubEvents.TRADE_ACTION, new { action = "close_signal_sent", dealId = dealId });
    }

    public async Task UpdatePositionLimitsAsync(string dealId, double? stopLevel, double? profitLevel)
    {
        var db = _redisClient.GetDatabase();
        var cachedJson = await db.StringGetAsync("CACHED_OPEN_TRADES");
        if (!cachedJson.IsNull)
        {
            var tradesList = JsonSerializer.Deserialize<List<OpenTrade>>((string)cachedJson!);
            var trade = tradesList?.FirstOrDefault(t => t.DealId == dealId);
            if (trade != null)
            {
                if (!stopLevel.HasValue) stopLevel = trade.StopLevel;
                if (!profitLevel.HasValue) profitLevel = trade.ProfitLevel;
            }
        }

        var success = await _capitalService.UpdatePositionLimitsAsync(dealId, stopLevel, profitLevel);
        if (success)
        {
            await ForceUpdateOpenTradesCacheAsync();
        }
        else
        {
            throw new Core.Exceptions.BadRequestException("Failed to update limits at broker");
        }
    }

    public async Task ForceUpdateOpenTradesCacheAsync()
    {
        var positionsResp = await _capitalService.GetOpenPositionsAsync();
        var positions = positionsResp?["positions"]?.AsArray();

        if (positions != null)
        {
            var dealIds = positions.Select(p => (string?)p?["position"]?["dealId"]).Where(id => !string.IsNullOrEmpty(id)).Cast<string>();
            var metadata = await GetTradeMetadataAsync(dealIds);

            var tradesList = new List<OpenTrade>();
            foreach (var pos in positions)
            {
                var p = pos?["position"];
                var m = pos?["market"];

                if (p != null && m != null)
                {
                    var dealId = (string?)p["dealId"] ?? "";
                    double.TryParse(p["size"]?.ToString(), out var size);
                    double.TryParse(p["level"]?.ToString(), out var entryPrice);
                    double.TryParse(p["upl"]?.ToString(), out var upl);

                    double? stopLevel = (double.TryParse(p["stopLevel"]?.ToString(), out var slV) && slV != 0) ? slV : null;
                    double? profitLevel = (double.TryParse(p["profitLevel"]?.ToString(), out var plV) && plV != 0) ? plV :
                                          (double.TryParse(p["limitLevel"]?.ToString(), out var llV) && llV != 0) ? llV :
                                          (double.TryParse(p["limit"]?.ToString(), out var lV) && lV != 0) ? lV : null;

                    var direction = (string?)p["direction"] ?? "BUY";
                    double currentPrice = 0.0;
                    if (direction == "BUY")
                        double.TryParse(m["bid"]?.ToString(), out currentPrice);
                    else
                        double.TryParse(m["offer"]?.ToString(), out currentPrice);

                    var (stra, res, _, _) = metadata.GetValueOrDefault(dealId, ("MANUAL", "-", 0.0, 0.0));
                    tradesList.Add(new OpenTrade
                    {
                        DealId = dealId,
                        Epic = (string?)m["epic"] ?? "",
                        Direction = direction,
                        Strategy = stra,
                        Resolution = res,
                        EntryTime = ((string?)p["createdDateUTC"] ?? "").Split('.')[0].Replace("T", " "),
                        EntryPrice = entryPrice,
                        CurrentPrice = currentPrice,
                        UnrealizedPnL = upl,
                        Size = size,
                        StopLevel = stopLevel,
                        ProfitLevel = profitLevel
                    });
                }
            }
            var db = _redisClient.GetDatabase();
            await db.StringSetAsync("CACHED_OPEN_TRADES", JsonSerializer.Serialize(tradesList));
        }
    }
}

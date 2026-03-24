using ApiServer.Context;
using ApiServer.Models;
using Microsoft.EntityFrameworkCore;
using System.Collections.Generic;
using System.Linq;

namespace ApiServer.Services;

public class DbService
{
    private readonly TradingDbContext _dbContext;

    public DbService(TradingDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<(List<ClosedTrade> Items, int TotalCount, double TotalPnL)> GetHistoricalTradesAsync(string? fromDate, string? toDate, int page = 1, int pageSize = 10)
    {
        var query = _dbContext.Trades.Where(t => t.ExitTime != null);

        if (!string.IsNullOrEmpty(fromDate) && DateTime.TryParse(fromDate, out var fromDt))
        {
            var utcFromDt = DateTime.SpecifyKind(fromDt, DateTimeKind.Utc);
            query = query.Where(t => t.ExitTime >= utcFromDt);
        }

        if (!string.IsNullOrEmpty(toDate) && DateTime.TryParse(toDate, out var toDt))
        {
            var utcToDt = DateTime.SpecifyKind(toDt, DateTimeKind.Utc);
            query = query.Where(t => t.ExitTime <= utcToDt);
        }

        int totalCount = await query.CountAsync();
        double totalPnL = await query.SumAsync(t => (double)(t.RealizedPnl ?? 0));

        var dbTrades = await query
            .OrderByDescending(t => t.ExitTime)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

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

        try
        {
            var dealIdsList = dealIds.ToList();
            var trades = await _dbContext.Trades
                .Where(t => dealIdsList.Contains(t.DealId))
                .Select(t => new { t.DealId, t.Strategy, t.Resolution, t.StopLoss, t.TakeProfit })
                .ToListAsync();

            foreach (var t in trades)
            {
                var stra = string.IsNullOrEmpty(t.Strategy) ? "MANUAL" : t.Strategy;
                var res = string.IsNullOrEmpty(t.Resolution) ? "-" : t.Resolution;
                var sl = t.StopLoss ?? 0;
                var tp = t.TakeProfit ?? 0;
                
                metadata[t.DealId] = (stra, res, sl, tp);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[Error] GetTradeMetadataAsync: {ex.Message}");
        }
        return metadata;
    }

    public async Task<List<string>> GetOpenTradeDealIdsAsync()
    {
        try
        {
            return await _dbContext.Trades
                .Where(t => t.ExitTime == null)
                .Select(t => t.DealId)
                .ToListAsync();
        }
        catch (Exception ex) 
        { 
            Console.WriteLine($"[Error] GetOpenTradeDealIdsAsync: {ex.Message}"); 
            return new List<string>();
        }
    }

    public async Task UpdateTradeClosingAsync(string dealId, double exitPrice, DateTime exitTime, double realizedPnL, string exitType)
    {
        try
        {
            var trade = await _dbContext.Trades.FirstOrDefaultAsync(t => t.DealId == dealId && t.ExitTime == null);
            if (trade != null)
            {
                trade.ExitPrice = (decimal)exitPrice;
                trade.ExitTime = DateTime.SpecifyKind(exitTime, DateTimeKind.Utc);
                trade.RealizedPnl = (decimal)realizedPnL;
                trade.ExitType = exitType;
                trade.UpdatedAt = DateTime.UtcNow;

                await _dbContext.SaveChangesAsync();
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[Error] UpdateTradeClosingAsync: {ex.Message}");
        }
    }
}

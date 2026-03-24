using ApiServer.Context;
using ApiServer.Models;
using Microsoft.EntityFrameworkCore;
using System.Collections.Generic;
using System.Linq;

namespace ApiServer.Repositories;

public class TradeRepository
{
    private readonly TradingDbContext _dbContext;

    public TradeRepository(TradingDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<(List<TradeEntity> Items, int TotalCount, double TotalPnL)> GetHistoricalTradesAsync(string? fromDate, string? toDate, int page = 1, int pageSize = 10)
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

        return (dbTrades, totalCount, totalPnL);
    }

    public async Task<List<TradeEntity>> GetTradesByDealIdsAsync(IEnumerable<string> dealIds)
    {
        var dealIdsList = dealIds.ToList();
        return await _dbContext.Trades
            .Where(t => dealIdsList.Contains(t.DealId))
            .ToListAsync();
    }

    public async Task<List<string>> GetOpenTradeDealIdsAsync()
    {
        return await _dbContext.Trades
            .Where(t => t.ExitTime == null)
            .Select(t => t.DealId)
            .ToListAsync();
    }

    public async Task UpdateTradeClosingAsync(string dealId, double exitPrice, DateTime exitTime, double realizedPnL, string exitType)
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
}

using ApiServer.Services.Interfaces;
using ApiServer.Models;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace ApiServer.Services.Interfaces;

public interface ITradeService
{
    Task<List<OpenTrade>> GetCachedOpenTradesAsync();
    Task<(List<ClosedTrade> Items, int TotalCount, double TotalPnL)> GetHistoricalTradesAsync(string? fromDate, string? toDate, int page = 1, int pageSize = 10);
    Task<Dictionary<string, (string Strategy, string Resolution, double StopLoss, double TakeProfit)>> GetTradeMetadataAsync(IEnumerable<string> dealIds);
    Task<List<string>> GetOpenTradeDealIdsAsync();
    Task UpdateTradeClosingAsync(string dealId, double exitPrice, DateTime exitTime, double realizedPnL, string exitType);
    Task PlaceOrderAsync(string epic, string direction, double size, double? stopLoss, double? takeProfit);
    Task CloseTradeAsync(string dealId, string? epic);
    Task UpdatePositionLimitsAsync(string dealId, double? stopLevel, double? profitLevel);
    Task ForceUpdateOpenTradesCacheAsync();
}

using ApiServer.Services.Interfaces;
using ApiServer.Models;
using System.Text.Json.Nodes;
using System.Collections.Generic;
using System.Threading.Tasks;
using System;

namespace ApiServer.Services.Interfaces;

public interface ICapitalService
{
    Task<List<object>> GetKlinesAsync(string epic, string resolution, int maxBars, DateTime? to = null);
    Task<List<object>?> GetClosedTradesAsync(string fromDate, string toDate, int limit = 100);
    Task<bool> ClosePositionAsync(string dealId);
    Task<List<object>?> SearchMarketsAsync(string searchTerm);
    Task<JsonNode?> GetAccountsAsync();
    Task<JsonNode?> GetOpenPositionsAsync();
    Task<bool> PlaceOrderAsync(string epic, string direction, double size);
    Task<bool> UpdatePositionLimitsAsync(string dealId, double? stopLevel, double? profitLevel);
    Task<JsonNode?> GetTransactionsAsync(int lastPeriodSeconds);
}

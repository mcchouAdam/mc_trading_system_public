using ApiServer.Services.Interfaces;
using ApiServer.Models;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace ApiServer.Services.Interfaces;

public interface ISystemService
{
    Task<List<string>> GetWatchlistAsync();
    Task<List<StrategyInstance>> GetActiveStrategiesAsync();
    Task UpdateActiveStrategiesAsync(List<StrategyInstance> strategies);
    Task UpdateMarketDataSubAsync(List<string> epics);
    Task UpdateOhlcDataSubAsync(List<OhlcDataSubscription> subs);
    Task<TradingSettings> GetTradingSettingsAsync();
    Task UpdateTradingSettingsAsync(TradingSettings settings);
    Dictionary<string, bool> GetMlSupport();
}

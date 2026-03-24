using ApiServer.Services.Interfaces;
using ApiServer.Models;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace ApiServer.Services.Interfaces;

public interface IMarketDataService
{
    Task<List<CandleModel>> GetKlinesAsync(string epic, string resolution, int maxBars, long? to = null);
    Task SyncGapsAsync(string epic, string resolution);
}

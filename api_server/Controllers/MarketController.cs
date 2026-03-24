using ApiServer.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using System.Text.Json;
using System.Text.Json.Nodes;
using ApiServer.Core;
using ApiServer.Services;

namespace ApiServer.Controllers;

[ApiController]
[Route("api/market")]
public class MarketController : ControllerBase
{
    private readonly IRedisClient _redisClient;
    private readonly IMarketDataService _marketDataService;
    private readonly ICapitalService _capitalService;

    public MarketController(IRedisClient redisClient, IMarketDataService marketDataService, ICapitalService capitalService)
    {
        _redisClient = redisClient;
        _marketDataService = marketDataService;
        _capitalService = capitalService;
    }

    [HttpGet("klines")]
    public async Task<IActionResult> GetKlines(
        [FromQuery] string epic = "US100", 
        [FromQuery] string resolution = "MINUTE", 
        [FromQuery] int max_bars = 200,
        [FromQuery] long? to = null)
    {
        var history = await _marketDataService.GetKlinesAsync(epic, resolution, max_bars, to);
        return Ok(history);
    }

    [HttpGet("search")]
    public async Task<IActionResult> Search([FromQuery] string q)
    {
        var results = await _capitalService.SearchMarketsAsync(q);
        return Ok(results);
    }
}

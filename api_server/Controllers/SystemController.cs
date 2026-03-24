using ApiServer.Services.Interfaces;
using ApiServer.Core;
using Microsoft.AspNetCore.Mvc;
using StackExchange.Redis;
using System.Text.Json;
using ApiServer.Models;
using ApiServer.Services;

namespace ApiServer.Controllers;

[ApiController]
[Route("api/system")]
public class SystemController : ControllerBase
{
    private readonly ISystemService _systemService;

    public SystemController(ISystemService systemService)
    {
        _systemService = systemService;
    }

    [HttpGet("watchlist")]
    public async Task<ActionResult<List<string>>> GetWatchlist()
    {
        return Ok(await _systemService.GetWatchlistAsync());
    }

    [HttpGet("strategies")]
    public async Task<ActionResult<List<StrategyInstance>>> GetStrategies()
    {
        return Ok(await _systemService.GetActiveStrategiesAsync());
    }

    [HttpPost("strategies")]
    public async Task<ActionResult> UpdateStrategies([FromBody] List<StrategyInstance> strategies)
    {
        await _systemService.UpdateActiveStrategiesAsync(strategies);
        return Ok(new { status = "success" });
    }

    [HttpGet("subscription/market-data")]
    public async Task<ActionResult<List<string>>> GetMarketDataSub()
    {
        return Ok(await _systemService.GetWatchlistAsync());
    }

    [HttpPost("subscription/market-data")]
    public async Task<ActionResult> UpdateMarketDataSub([FromBody] List<string> epics)
    {
        await _systemService.UpdateMarketDataSubAsync(epics);
        return Ok(new { status = "success" });
    }

    [HttpGet("subscription/ohlc-data")]
    public async Task<ActionResult<List<OhlcDataSubscription>>> GetOhlcDataSub()
    {
        var db = (await _systemService.GetTradingSettingsAsync());
        return Ok(new List<OhlcDataSubscription>()); 
    }

    [HttpPost("subscription/ohlc-data")]
    public async Task<ActionResult> UpdateOhlcDataSub([FromBody] List<OhlcDataSubscription> subs)
    {
        await _systemService.UpdateOhlcDataSubAsync(subs);
        return Ok(new { status = "success" });
    }

    [HttpGet("available-strategies")]
    public ActionResult<List<AvailableStrategy>> GetAvailableStrategies()
    {
        var mlSupport = _systemService.GetMlSupport();

        return Ok(new List<AvailableStrategy>
        {
            new AvailableStrategy { 
                Name = "MACD", 
                DefaultParameters = new Dictionary<string, double> { 
                    { "FAST", 12 }, { "SLOW", 26 }, { "SIGNAL", 9 },
                    { "STOP_LOSS_PERCENT", 2.0 }, { "TSTOP_LOSS_PERCENT", 0.0 }, { "RISK_REWARD", 2.0 }
                },
                SupportsMl = mlSupport.GetValueOrDefault("macd", false),
                DefaultPositionSize = 0.01,
                DefaultSizingType = "FIXED"
            },
            new AvailableStrategy { 
                Name = "YuBrokenBottom", 
                DefaultParameters = new Dictionary<string, double> { 
                    { "RISK_REWARD", 5 }, { "LOOKBACK_PERIOD", 20 }, { "RECOVERY_BARS", 3 }, 
                    { "SHADOW_RATIO", 0.6 }, { "TSTOP_LOSS_PERCENT", 0.0 }
                },
                SupportsMl = mlSupport.GetValueOrDefault("yu_broken_bottom", false),
                DefaultPositionSize = 0.01,
                DefaultSizingType = "FIXED"
            },
            new AvailableStrategy { 
                Name = "PineL4", 
                DefaultParameters = new Dictionary<string, double> { 
                    { "TSTOP_LOSS_PERCENT", 1.0 }, { "RISK_REWARD", 3.0 }, { "SHADOW_RATIO", 1.5 }
                },
                SupportsMl = mlSupport.GetValueOrDefault("pine_l4", false),
                DefaultPositionSize = 0.01,
                DefaultSizingType = "FIXED"
            }
        });
    }

    [HttpGet("supported-epics")]
    public async Task<ActionResult<List<string>>> GetSupportedEpics()
    {
        return Ok(await _systemService.GetWatchlistAsync());
    }

    [HttpGet("active_strategies")]
    public async Task<ActionResult<List<ActiveStrategyMetadata>>> GetActiveStrategies()
    {
        var strats = await _systemService.GetActiveStrategiesAsync();
        var active = strats.Select(s => new ActiveStrategyMetadata {
            Id = s.Id, Name = s.Name, Epic = s.Epic, Resolution = s.Resolution,
            Active = s.Active, UseMl = s.UseMl, PositionSize = s.PositionSize, SizingType = s.SizingType
        }).ToList();
        return Ok(active);
    }

    [HttpGet("trading-settings")]
    public async Task<ActionResult<TradingSettings>> GetTradingSettings()
    {
        return Ok(await _systemService.GetTradingSettingsAsync());
    }

    [HttpPost("trading-settings")]
    public async Task<ActionResult> UpdateTradingSettings([FromBody] TradingSettings settings)
    {
        await _systemService.UpdateTradingSettingsAsync(settings);
        return Ok(new { status = "success" });
    }
}

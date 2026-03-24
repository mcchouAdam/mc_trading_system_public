using ApiServer.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using ApiServer.Services;
using ApiServer.Models;
using System.Text.Json;

namespace ApiServer.Controllers;

[ApiController]
[Route("api/trade")]
public class TradeController : ControllerBase
{
    private readonly ITradeService _tradeService;

    public TradeController(ITradeService tradeService)
    {
        _tradeService = tradeService;
    }

    [HttpGet("ping")]
    public IActionResult Ping() => Ok(new { status = "alive", time = DateTime.UtcNow });

    [HttpGet("open")]
    public async Task<ActionResult<List<OpenTrade>>> GetOpenTrades()
    {
        return Ok(await _tradeService.GetCachedOpenTradesAsync());
    }

    [HttpGet("closed")]
    public async Task<IActionResult> GetClosedTrades([FromQuery] string? from_date, [FromQuery] string? to_date, [FromQuery] int page = 1, [FromQuery] int pageSize = 10)
    {
        var (items, totalCount, totalPnL) = await _tradeService.GetHistoricalTradesAsync(from_date, to_date, page, pageSize);
        return Ok(new { items, totalCount, totalPnL });
    }

    [HttpDelete("close/{deal_id}")]
    public async Task<IActionResult> CloseTrade(string deal_id, [FromQuery] string? epic = null)
    {
        await _tradeService.CloseTradeAsync(deal_id, epic);
        return Ok(new { status = "published", dealId = deal_id });
    }

    [HttpPost("order")]
    public async Task<IActionResult> PlaceOrder([FromBody] JsonElement body)
    {
        var epic = body.GetProperty("epic").GetString() ?? "";
        var direction = body.GetProperty("direction").GetString() ?? "BUY";
        double size = body.TryGetProperty("size", out var s) ? s.GetDouble() : 0.01;
        
        double? stopLoss = (body.TryGetProperty("stopLoss", out var sl) && sl.ValueKind != JsonValueKind.Null) ? sl.GetDouble() : null;
        double? takeProfit = (body.TryGetProperty("takeProfit", out var tp) && tp.ValueKind != JsonValueKind.Null) ? tp.GetDouble() : null;

        await _tradeService.PlaceOrderAsync(epic, direction, size, stopLoss, takeProfit);
        return Ok(new { status = "published", epic = epic });
    }

    [HttpPut("position/{dealId}/limits")]
    public async Task<IActionResult> UpdateLimits(string dealId, [FromBody] JsonElement body)
    {
        double? stopLevel = (body.TryGetProperty("stopLevel", out var sl) && sl.ValueKind != JsonValueKind.Null) ? sl.GetDouble() : null;
        double? profitLevel = (body.TryGetProperty("profitLevel", out var pl) && pl.ValueKind != JsonValueKind.Null) ? pl.GetDouble() : null;

        await _tradeService.UpdatePositionLimitsAsync(dealId, stopLevel, profitLevel);
        return Ok(new { status = "success" });
    }
}

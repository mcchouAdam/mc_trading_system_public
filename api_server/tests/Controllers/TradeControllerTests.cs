using ApiServer.Services.Interfaces;
using ApiServer.Controllers;
using ApiServer.Models;
using ApiServer.Services;
using FluentAssertions;
using Microsoft.AspNetCore.Mvc;
using NSubstitute;
using System.Text.Json;
using Xunit;

namespace ApiServer.Tests.Controllers;

public class TradeControllerTests
{
    private readonly ITradeService _tradeService;
    private readonly TradeController _controller;

    public TradeControllerTests()
    {
        _tradeService = Substitute.For<ITradeService>();
        _controller = new TradeController(_tradeService);
    }

    [Fact]
    public async Task GetOpenTrades_ReturnsFromService()
    {
        var mockTrades = new List<OpenTrade> { new OpenTrade { DealId = "123", Epic = "AAPL" } };
        _tradeService.GetCachedOpenTradesAsync().Returns(mockTrades);

        var result = await _controller.GetOpenTrades();

        var okResult = result.Result.Should().BeOfType<OkObjectResult>().Subject;
        okResult.Value.Should().BeEquivalentTo(mockTrades);
    }

    [Fact]
    public async Task PlaceOrder_CallsServiceCorrectly()
    {
        var body = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(new { 
            epic = "US100", 
            direction = "BUY", 
            size = 0.5 
        }));

        var result = await _controller.PlaceOrder(body);

        result.Should().BeOfType<OkObjectResult>();
        await _tradeService.Received(1).PlaceOrderAsync("US100", "BUY", 0.5, null, null);
    }

    [Fact]
    public async Task CloseTrade_CallsServiceCorrectly()
    {
        var result = await _controller.CloseTrade("deal_1", "US100");

        result.Should().BeOfType<OkObjectResult>();
        await _tradeService.Received(1).CloseTradeAsync("deal_1", "US100");
    }
}

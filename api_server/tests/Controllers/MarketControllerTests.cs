using ApiServer.Services.Interfaces;
using ApiServer.Controllers;
using ApiServer.Core;
using ApiServer.Services;
using FluentAssertions;
using Microsoft.AspNetCore.Mvc;
using NSubstitute;
using Xunit;

namespace ApiServer.Tests.Controllers;

public class MarketControllerTests
{
    private readonly IRedisClient _redisClient;
    private readonly IMarketDataService _marketDataService;
    private readonly ICapitalService _capitalService;
    private readonly MarketController _controller;

    public MarketControllerTests()
    {
        _redisClient = Substitute.For<IRedisClient>();
        _marketDataService = Substitute.For<IMarketDataService>();
        _capitalService = Substitute.For<ICapitalService>();
        _controller = new MarketController(_redisClient, _marketDataService, _capitalService);
    }

    [Fact]
    public async Task GetKlines_CallsServiceCorrectly()
    {
        var result = await _controller.GetKlines("BTCUSD", "MINUTE", 50, null);

        result.Should().BeOfType<OkObjectResult>();
        await _marketDataService.Received(1).GetKlinesAsync("BTCUSD", "MINUTE", 50, null);
    }

    [Fact]
    public async Task Search_CallsCapitalServiceCorrectly()
    {
        var result = await _controller.Search("USA500");

        result.Should().BeOfType<OkObjectResult>();
        await _capitalService.Received(1).SearchMarketsAsync("USA500");
    }
}

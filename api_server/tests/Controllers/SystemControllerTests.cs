using ApiServer.Services.Interfaces;
using ApiServer.Controllers;
using ApiServer.Core;
using ApiServer.Services;
using FluentAssertions;
using Microsoft.AspNetCore.Mvc;
using NSubstitute;
using StackExchange.Redis;
using System.Text.Json;
using Xunit;

namespace ApiServer.Tests.Controllers;

public class SystemControllerTests
{
    private readonly ISystemService _systemService;
    private readonly SystemController _controller;

    public SystemControllerTests()
    {
        _systemService = Substitute.For<ISystemService>();
        _controller = new SystemController(_systemService);
    }

    [Fact]
    public async Task GetWatchlist_WhenCached_ReturnsSortedEpics()
    {
        var epics = new List<string> { "AAPL", "BTCUSD", "EURUSD" };
        _systemService.GetWatchlistAsync().Returns(epics);

        var result = await _controller.GetWatchlist();

        var okResult = result.Result.Should().BeOfType<OkObjectResult>().Subject;
        var returnedEpics = okResult.Value.Should().BeOfType<List<string>>().Subject;
        returnedEpics.Should().HaveCount(3);
        returnedEpics[0].Should().Be("AAPL");
    }

    [Fact]
    public async Task GetWatchlist_WhenNotCached_ReturnsEmptyList()
    {
        _systemService.GetWatchlistAsync().Returns(new List<string>());

        var result = await _controller.GetWatchlist();

        var okResult = result.Result.Should().BeOfType<OkObjectResult>().Subject;
        var returnedEpics = okResult.Value.Should().BeOfType<List<string>>().Subject;
        returnedEpics.Should().BeEmpty();
    }
}

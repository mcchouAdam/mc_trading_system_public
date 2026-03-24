using ApiServer.Services.Interfaces;
using ApiServer.Controllers;
using ApiServer.Models;
using ApiServer.Services;
using FluentAssertions;
using Microsoft.AspNetCore.Mvc;
using NSubstitute;
using Xunit;

namespace ApiServer.Tests.Controllers;

public class RiskControllerTests
{
    private readonly IRiskService _riskService;
    private readonly RiskController _controller;

    public RiskControllerTests()
    {
        _riskService = Substitute.For<IRiskService>();
        _controller = new RiskController(_riskService);
    }

    [Fact]
    public async Task GetStatus_WhenCalled_ReturnsRiskStatus()
    {
        var mockStatus = new RiskStatus { IsHalted = false, HaltReason = "None" };
        _riskService.GetRiskStatusAsync().Returns(mockStatus);

        var result = await _controller.GetStatus();

        var okResult = result.Result.Should().BeOfType<OkObjectResult>().Subject;
        okResult.Value.Should().BeEquivalentTo(mockStatus);
    }

    [Fact]
    public async Task Halt_WhenCalled_ExecutesManualHalt()
    {
        var result = await _controller.Halt();

        result.Should().BeOfType<OkObjectResult>();
        await _riskService.Received(1).SetManualHaltAsync(true);
    }

    [Fact]
    public async Task Resume_WhenCalled_ExecutesResume()
    {
        var result = await _controller.Resume();

        result.Should().BeOfType<OkObjectResult>();
        await _riskService.Received(1).ResumeAsync();
    }
}

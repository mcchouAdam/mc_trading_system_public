using ApiServer.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using ApiServer.Services;
using ApiServer.Models;

namespace ApiServer.Controllers;

[ApiController]
[Route("api/risk")]
public class RiskController : ControllerBase
{
    private readonly IRiskService _riskService;

    public RiskController(IRiskService riskService)
    {
        _riskService = riskService;
    }

    [HttpGet("status")]
    public async Task<ActionResult<RiskStatus>> GetStatus()
    {
        var status = await _riskService.GetRiskStatusAsync();
        return Ok(status);
    }

    [HttpPost("resume")]
    public async Task<IActionResult> Resume()
    {
        await _riskService.ResumeAsync();
        return Ok(new { status = "resumed" });
    }

    [HttpPost("limits")]
    public async Task<IActionResult> UpdateLimits([FromBody] RiskLimitUpdate update)
    {
        await _riskService.UpdateLimitsAsync(update);
        return Ok(new { status = "updated" });
    }

    [HttpPost("halt")]
    public async Task<IActionResult> Halt()
    {
        await _riskService.SetManualHaltAsync(true);
        return Ok(new { status = "halted" });
    }
}

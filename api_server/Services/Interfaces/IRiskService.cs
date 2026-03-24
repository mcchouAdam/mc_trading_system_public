using ApiServer.Services.Interfaces;
using ApiServer.Models;
using System.Threading.Tasks;

namespace ApiServer.Services.Interfaces;

public interface IRiskService
{
    Task<RiskStatus> GetRiskStatusAsync();
    Task ResumeAsync();
    Task UpdateLimitsAsync(RiskLimitUpdate update);
    Task SetManualHaltAsync(bool isHalted);
}

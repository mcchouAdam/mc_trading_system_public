using System.Text.Json.Serialization;

namespace ApiServer.Models;

public class StrategyInstance
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString();

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("epic")]
    public string Epic { get; set; } = string.Empty;

    [JsonPropertyName("resolution")]
    public string Resolution { get; set; } = "MINUTE";

    [JsonPropertyName("active")]
    public bool Active { get; set; } = true;

    [JsonPropertyName("use_ml")]
    public bool UseMl { get; set; } = false;

    [JsonPropertyName("parameters")]
    public Dictionary<string, double> Parameters { get; set; } = new();

    [JsonPropertyName("position_size")]
    public double PositionSize { get; set; } = 0.01;

    [JsonPropertyName("sizing_type")]
    public string SizingType { get; set; } = "FIXED"; // "FIXED" or "RISK"
}

public class OhlcDataSubscription
{
    [JsonPropertyName("epic")]
    public string Epic { get; set; } = string.Empty;

    [JsonPropertyName("resolution")]
    public string Resolution { get; set; } = "MINUTE";
}

public class SystemConfigModel
{
    [JsonPropertyName("market_data")]
    public List<OhlcDataSubscription> MarketData { get; set; } = new();

    [JsonPropertyName("strategies")]
    public List<StrategyInstance> Strategies { get; set; } = new();
}

public class RiskLimitUpdate
{
    [JsonPropertyName("daily_limit_pct")]
    public double DailyLimitPct { get; set; }

    [JsonPropertyName("daily_limit_enabled")]
    public bool DailyLimitEnabled { get; set; }

    [JsonPropertyName("monthly_limit_pct")]
    public double MonthlyLimitPct { get; set; }

    [JsonPropertyName("monthly_limit_enabled")]
    public bool MonthlyLimitEnabled { get; set; }
}

public class OpenTrade
{
    [JsonPropertyName("deal_id")]
    public string DealId { get; set; } = string.Empty;

    [JsonPropertyName("epic")]
    public string Epic { get; set; } = string.Empty;

    [JsonPropertyName("direction")]
    public string Direction { get; set; } = string.Empty;

    [JsonPropertyName("entry_time")]
    public string EntryTime { get; set; } = string.Empty;

    [JsonPropertyName("entry_price")]
    public double EntryPrice { get; set; }

    [JsonPropertyName("current_price")]
    public double CurrentPrice { get; set; }

    [JsonPropertyName("unrealized_pnl")]
    public double UnrealizedPnL { get; set; }

    [JsonPropertyName("size")]
    public double Size { get; set; }

    [JsonPropertyName("resolution")]
    public string? Resolution { get; set; }

    [JsonPropertyName("strategy")]
    public string? Strategy { get; set; }

    [JsonPropertyName("stop_level")]
    public double? StopLevel { get; set; }

    [JsonPropertyName("profit_level")]
    public double? ProfitLevel { get; set; }
}

public class ClosedTrade
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("epic")]
    public string Epic { get; set; } = string.Empty;

    [JsonPropertyName("strategy")]
    public string? Strategy { get; set; }

    [JsonPropertyName("direction")]
    public string Direction { get; set; } = string.Empty;

    [JsonPropertyName("size")]
    public double Size { get; set; }

    [JsonPropertyName("entry_time")]
    public string EntryTime { get; set; } = string.Empty;

    [JsonPropertyName("exit_time")]
    public string ExitTime { get; set; } = string.Empty;

    [JsonPropertyName("entry_price")]
    public double EntryPrice { get; set; }

    [JsonPropertyName("exit_price")]
    public double ExitPrice { get; set; }

    [JsonPropertyName("pnl")]
    public double PnL { get; set; }

    [JsonPropertyName("exit_type")]
    public string? ExitType { get; set; }

    [JsonPropertyName("stop_loss")]
    public double? StopLoss { get; set; }

    [JsonPropertyName("take_profit")]
    public double? TakeProfit { get; set; }

    [JsonPropertyName("is_win")]
    public bool IsWin => PnL > 0;
}

public class RiskStatus
{
    [JsonPropertyName("account_id")]
    public string AccountId { get; set; } = string.Empty;

    [JsonPropertyName("balance")]
    public double Balance { get; set; }

    [JsonPropertyName("equity")]
    public double Equity { get; set; }

    [JsonPropertyName("daily_pnl_pct")]
    public double DailyPnLPct { get; set; }

    [JsonPropertyName("monthly_pnl_pct")]
    public double MonthlyPnLPct { get; set; }

    [JsonPropertyName("is_halted")]
    public bool IsHalted { get; set; }

    [JsonPropertyName("daily_limit_pct")]
    public double DailyLimitPct { get; set; }

    [JsonPropertyName("daily_limit_enabled")]
    public bool DailyLimitEnabled { get; set; }

    [JsonPropertyName("monthly_limit_pct")]
    public double MonthlyLimitPct { get; set; }

    [JsonPropertyName("monthly_limit_enabled")]
    public bool MonthlyLimitEnabled { get; set; }

    [JsonPropertyName("halt_reason")]
    public string HaltReason { get; set; } = string.Empty;

    [JsonPropertyName("can_resume")]
    public bool CanResume { get; set; }

    [JsonPropertyName("start_day_balance")]
    public double StartDayBalance { get; set; }

    [JsonPropertyName("start_month_balance")]
    public double StartMonthBalance { get; set; }

    [JsonPropertyName("is_resume_override")]
    public bool IsResumeOverride { get; set; }
}

public class AvailableStrategy
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("default_parameters")]
    public Dictionary<string, double> DefaultParameters { get; set; } = new();

    [JsonPropertyName("supports_ml")]
    public bool SupportsMl { get; set; } = false;

    [JsonPropertyName("default_position_size")]
    public double DefaultPositionSize { get; set; } = 0.01;

    [JsonPropertyName("default_sizing_type")]
    public string DefaultSizingType { get; set; } = "FIXED";
}

public class ConfigUpdateResponse
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = "success";

    [JsonPropertyName("market_data_changed")]
    public bool MarketDataChanged { get; set; }
}

public class ActiveStrategyMetadata
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("epic")]
    public string Epic { get; set; } = string.Empty;

    [JsonPropertyName("resolution")]
    public string Resolution { get; set; } = string.Empty;

    [JsonPropertyName("active")]
    public bool Active { get; set; } = true;

    [JsonPropertyName("use_ml")]
    public bool UseMl { get; set; } = false;

    [JsonPropertyName("position_size")]
    public double PositionSize { get; set; }

    [JsonPropertyName("sizing_type")]
    public string? SizingType { get; set; }
}


public class CandleModel
{
    [JsonPropertyName("time")]
    public long Time { get; set; }

    [JsonPropertyName("open")]
    public double Open { get; set; }

    [JsonPropertyName("high")]
    public double High { get; set; }

    [JsonPropertyName("low")]
    public double Low { get; set; }

    [JsonPropertyName("close")]
    public double Close { get; set; }

    [JsonPropertyName("volume")]
    public double Volume { get; set; }
}

public class TradingSettings
{
    [JsonPropertyName("default_size")]
    public double DefaultSize { get; set; } = 0.01;

    [JsonPropertyName("use_dynamic_sizing")]
    public bool UseDynamicSizing { get; set; } = false;

    [JsonPropertyName("risk_pct_per_trade")]
    public double RiskPctPerTrade { get; set; } = 0.01;

    [JsonPropertyName("fixed_leverage_factor")]
    public double FixedLeverageFactor { get; set; } = 0.1;
}

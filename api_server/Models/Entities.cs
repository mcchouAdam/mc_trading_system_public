using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace ApiServer.Models;

[Table("trades")]
public class TradeEntity
{
    [Key]
    [Column("deal_id")]
    public string DealId { get; set; } = string.Empty;

    [Column("deal_reference")]
    public string? DealReference { get; set; }

    [Column("strategy")]
    public string? Strategy { get; set; }

    [Column("source")]
    public string Source { get; set; } = "AUTO";

    [Column("epic")]
    public string Epic { get; set; } = string.Empty;

    [Column("direction")]
    public string Direction { get; set; } = string.Empty;

    [Column("size")]
    public decimal Size { get; set; }

    [Column("leverage")]
    public int? Leverage { get; set; }

    [Column("entry_time")]
    public DateTime EntryTime { get; set; }

    [Column("entry_price")]
    public decimal EntryPrice { get; set; }

    [Column("exit_time")]
    public DateTime? ExitTime { get; set; }

    [Column("exit_price")]
    public decimal? ExitPrice { get; set; }

    [Column("realized_pnl")]
    public decimal? RealizedPnl { get; set; }

    [Column("currency")]
    public string? Currency { get; set; }

    [Column("resolution")]
    public string? Resolution { get; set; }

    [Column("stop_loss")]
    public double? StopLoss { get; set; }

    [Column("take_profit")]
    public double? TakeProfit { get; set; }

    [Column("exit_type")]
    public string? ExitType { get; set; }

    [Column("created_at")]
    public DateTime? CreatedAt { get; set; }

    [Column("updated_at")]
    public DateTime? UpdatedAt { get; set; }
}

[Table("market_candles")]
public class MarketCandleEntity
{
    [Column("epic")]
    public string Epic { get; set; } = string.Empty;

    [Column("resolution")]
    public string Resolution { get; set; } = string.Empty;

    [Column("time")]
    public DateTime Time { get; set; }

    [Column("open_price")]
    public decimal OpenPrice { get; set; }

    [Column("high_price")]
    public decimal HighPrice { get; set; }

    [Column("low_price")]
    public decimal LowPrice { get; set; }

    [Column("close_price")]
    public decimal ClosePrice { get; set; }

    [Column("volume")]
    public decimal Volume { get; set; }

    [Column("is_final")]
    public bool? IsFinal { get; set; }

    [Column("created_at")]
    public DateTime? CreatedAt { get; set; }
}

[Table("applied_seeds")]
public class AppliedSeedEntity
{
    [Key]
    [Column("file_name")]
    public string FileName { get; set; } = string.Empty;

    [Column("applied_at")]
    public DateTime? AppliedAt { get; set; }
}

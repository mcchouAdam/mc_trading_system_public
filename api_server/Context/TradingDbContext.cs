using Microsoft.EntityFrameworkCore;
using ApiServer.Models;

namespace ApiServer.Context;

public class TradingDbContext : DbContext
{
    public TradingDbContext(DbContextOptions<TradingDbContext> options) : base(options)
    {
    }

    public DbSet<TradeEntity> Trades { get; set; } = null!;
    public DbSet<MarketCandleEntity> MarketCandles { get; set; } = null!;
    public DbSet<AppliedSeedEntity> AppliedSeeds { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Map Composite Primary Key for MarketCandles
        modelBuilder.Entity<MarketCandleEntity>()
            .HasKey(c => new { c.Epic, c.Resolution, c.Time });

        // Add Index for performance optimization when querying latest candles
        modelBuilder.Entity<MarketCandleEntity>()
            .HasIndex(c => new { c.Epic, c.Resolution, c.Time })
            .HasDatabaseName("IX_MarketCandles_Epic_Resolution_Time_Desc")
            .IsDescending(false, false, true);
    }
}

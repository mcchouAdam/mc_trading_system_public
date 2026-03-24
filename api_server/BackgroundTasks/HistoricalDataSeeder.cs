using Npgsql;
using Parquet;
using Parquet.Data;
using ApiServer.Core;
using Microsoft.EntityFrameworkCore;

namespace ApiServer.BackgroundTasks;

public class HistoricalDataSeeder : BaseBackgroundService
{
    private readonly IServiceProvider _serviceProvider;

    public HistoricalDataSeeder(IServiceProvider serviceProvider, ILogger<HistoricalDataSeeder> logger)
        : base(logger)
    {
        _serviceProvider = serviceProvider;
    }

    protected override async Task ExecuteWorkAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Checking for database seed data...");

        var appliedSeeds = new HashSet<string>();
        try
        {
            using var scope = _serviceProvider.CreateScope();
            var dbContext = scope.ServiceProvider.GetRequiredService<ApiServer.Context.TradingDbContext>();
            appliedSeeds = new HashSet<string>(await dbContext.AppliedSeeds.Select(s => s.FileName).ToListAsync(cancellationToken));
        }
        catch (Exception ex) 
        {
            _logger.LogWarning("Could not load applied_seeds. Tracking table may be missing: {Message}", ex.Message);
        }

        var seedDir = Path.Combine(Directory.GetCurrentDirectory(), "data", "seed");
        if (!Directory.Exists(seedDir)) return;

        var parquetFiles = Directory.GetFiles(seedDir, "*.parquet");
        if (parquetFiles.Length == 0) return;

        _logger.LogInformation("Discovered {Count} parquet files. Starting throttled seeding...", parquetFiles.Length);

        foreach (var file in parquetFiles)
        {
            if (cancellationToken.IsCancellationRequested) break;

            var fileName = Path.GetFileName(file);
            if (appliedSeeds.Contains(fileName)) continue;

            using var scope = _serviceProvider.CreateScope();
            var dbContext = scope.ServiceProvider.GetRequiredService<ApiServer.Context.TradingDbContext>();
            var conn = (NpgsqlConnection)dbContext.Database.GetDbConnection();
            if (conn.State != System.Data.ConnectionState.Open) await conn.OpenAsync(cancellationToken);

            await SeedParquetFileAsync(file, conn, cancellationToken);
            
            await conn.CloseAsync();
            
            _logger.LogInformation("Throttling for 1s to allow GC...");
            GC.Collect(2, GCCollectionMode.Forced, true);
            await Task.Delay(1000, cancellationToken);
        }

        _logger.LogInformation("Database seed from Parquet complete.");
    }

    private async Task SeedParquetFileAsync(string filePath, NpgsqlConnection conn, CancellationToken ct)
    {
        _logger.LogInformation("Loading {File}...", Path.GetFileName(filePath));
        try
        {
            using var stream = System.IO.File.OpenRead(filePath);
            using var parquetReader = await ParquetReader.CreateAsync(stream, cancellationToken: ct);

            // Expected Format: {epic}__{resolution}__{range}.parquet
            // e.g. BTCUSD__MINUTE_15__20240101.parquet
            var fileName = Path.GetFileNameWithoutExtension(filePath);
            var parts = fileName.Split(new[] { "__" }, StringSplitOptions.RemoveEmptyEntries);
            
            if (parts.Length < 2)
            {
                _logger.LogWarning("Invalid seed filename format: {File}. Skipping.", fileName);
                return;
            }

            string epic = parts[0];
            string resolution = parts[1];

            var tempTable = $"temp_candles_{Guid.NewGuid():N}";
            using var createTempCmd = new NpgsqlCommand($"CREATE TEMP TABLE {tempTable} (LIKE market_candles INCLUDING ALL);", conn);
            await createTempCmd.ExecuteNonQueryAsync(ct);

            // Using COPY STDIN into a temporary table for resolving duplicates
            using (var writer = await conn.BeginBinaryImportAsync($"COPY {tempTable} (epic, resolution, time, open_price, high_price, low_price, close_price, volume) FROM STDIN (FORMAT BINARY)", ct))
            {
                var dataFields = parquetReader.Schema.GetDataFields();

                for (int i = 0; i < parquetReader.RowGroupCount; i++)
                {
                    using var rowGroupReader = parquetReader.OpenRowGroupReader(i);
                    
                    var dataCols = new DataColumn[dataFields.Length];
                    for (int c = 0; c < dataFields.Length; c++)
                    {
                        dataCols[c] = await rowGroupReader.ReadColumnAsync(dataFields[c], ct);
                    }

                    int numRows = dataCols[0].Data.Length;

                    for (int r = 0; r < numRows; r++)
                    {
                        await writer.StartRowAsync(ct);
                        await writer.WriteAsync(epic, ct);
                        await writer.WriteAsync(resolution, ct);
                        
                        await writer.WriteAsync((DateTime)dataCols[0].Data.GetValue(r)!, ct); // time
                        await writer.WriteAsync(Convert.ToDecimal(dataCols[1].Data.GetValue(r)), NpgsqlTypes.NpgsqlDbType.Numeric, ct); // open
                        await writer.WriteAsync(Convert.ToDecimal(dataCols[2].Data.GetValue(r)), NpgsqlTypes.NpgsqlDbType.Numeric, ct); // high
                        await writer.WriteAsync(Convert.ToDecimal(dataCols[3].Data.GetValue(r)), NpgsqlTypes.NpgsqlDbType.Numeric, ct); // low
                        await writer.WriteAsync(Convert.ToDecimal(dataCols[4].Data.GetValue(r)), NpgsqlTypes.NpgsqlDbType.Numeric, ct); // close
                        
                        if (dataCols.Length > 5)
                            await writer.WriteAsync(Convert.ToDecimal(dataCols[5].Data.GetValue(r)), NpgsqlTypes.NpgsqlDbType.Numeric, ct); // vol
                        else
                            await writer.WriteAsync(0m, NpgsqlTypes.NpgsqlDbType.Numeric, ct); // default
                    }
                }
                await writer.CompleteAsync(ct);
            }

            using var mergeCmd = new NpgsqlCommand($@"
                INSERT INTO market_candles (epic, resolution, time, open_price, high_price, low_price, close_price, volume)
                SELECT epic, resolution, time, open_price, high_price, low_price, close_price, volume FROM {tempTable}
                ON CONFLICT (epic, resolution, time) DO NOTHING;
                DROP TABLE {tempTable};
            ", conn);
            await mergeCmd.ExecuteNonQueryAsync(ct);
            
            // Record successful migration
            using var insertCmd = new NpgsqlCommand("INSERT INTO applied_seeds (file_name) VALUES (@file) ON CONFLICT DO NOTHING", conn);
            insertCmd.Parameters.AddWithValue("file", Path.GetFileName(filePath));
            await insertCmd.ExecuteNonQueryAsync(ct);

            _logger.LogInformation("=> Successfully seeded {File}", Path.GetFileName(filePath));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to seed {File}. Check column schema alignment.", filePath);
        }
    }
}

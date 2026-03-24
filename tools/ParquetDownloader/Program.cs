using System;
using System.Net.Http;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Parquet;
using Parquet.Data;
using Parquet.Schema;
using System.Text;
using System.Globalization;
using Microsoft.Extensions.Configuration;

namespace ParquetDownloader;

class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("=========================================================");
        Console.WriteLine(" CAPITAL.COM -> PARQUET DOWNLOADER (C#) ");
        Console.WriteLine("=========================================================\n");

        var builder = new ConfigurationBuilder()
            .SetBasePath(Directory.GetCurrentDirectory())
            .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true);
            
        IConfiguration config = builder.Build();
        string envPath = config["EnvFilePath"];

        if (!string.IsNullOrEmpty(envPath))
        {
            var absolutePath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), envPath));
            if (File.Exists(absolutePath))
            {
                DotNetEnv.Env.Load(absolutePath);
            }
            else
            {
                Console.WriteLine($"[!] .env file not found at evaluated path: {absolutePath}");
            }
        }
        else
        {
            Console.WriteLine("[!] No EnvFilePath specified in appsettings.json.");
        }

        if (args.Length < 4)
        {
            Console.WriteLine("Usage:   dotnet run <EPICS> <RESOLUTION> <FROM> <TO>");
            Console.WriteLine("Example: dotnet run BTCUSD,ETHUSD,US100 MINUTE_15 20260101T0100 20260201T2359");
            Console.WriteLine("Format:  yyyyMMddTHHmm (UTC+0)");
            return;
        }

        string epicsInput = args[0].ToUpper();
        string[] epics = epicsInput.Split(',').Select(e => e.Trim()).Where(e => !string.IsNullOrEmpty(e)).ToArray();
        string resolution = args[1].ToUpper();
        string fromStr = args[2];
        string toStr = args[3];

        if (!DateTime.TryParseExact(fromStr, "yyyyMMddTHHmm", CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out DateTime fromDate))
        {
            Console.WriteLine("[!] Invalid FROM format. Expected yyyyMMddTHHmm"); return;
        }
        if (!DateTime.TryParseExact(toStr, "yyyyMMddTHHmm", CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out DateTime toDate))
        {
            Console.WriteLine("[!] Invalid TO format. Expected yyyyMMddTHHmm"); return;
        }

        if (toDate > DateTime.UtcNow)
        {
            toDate = DateTime.UtcNow;
            toStr = toDate.ToString("yyyyMMddTHHmm");
            Console.WriteLine($"[*] 'TO' date exceeds current time. Adjusted to current UTC: {toStr}");
        }

        string baseUrl = Environment.GetEnvironmentVariable("CAPITAL_REST_URL") ?? "https://demo-api-capital.backend-capital.com";
        string apiKey = Environment.GetEnvironmentVariable("CAPITAL_API_KEY") ?? "";
        string identifier = Environment.GetEnvironmentVariable("CAPITAL_LOGIN_ID") ?? "";
        string password = Environment.GetEnvironmentVariable("CAPITAL_PASSWORD") ?? "";

        if (string.IsNullOrEmpty(apiKey) || string.IsNullOrEmpty(identifier) || string.IsNullOrEmpty(password))
        {
            Console.WriteLine("[!] Missing credentials. Please set CAPITAL_API_KEY, CAPITAL_LOGIN_ID, CAPITAL_PASSWORD.");
            return;
        }

        using var client = new HttpClient { BaseAddress = new Uri(baseUrl) };
        client.DefaultRequestHeaders.Add("X-CAP-API-KEY", apiKey);

        // 1. Capital.com Login Session
        Console.WriteLine("[*] Authenticating with Capital.com...");
        var payload = new { identifier, password, encryptedPassword = false };
        var authContent = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        var authResp = await client.PostAsync("/api/v1/session", authContent);

        if (!authResp.IsSuccessStatusCode)
        {
            Console.WriteLine($"[!] Auth failed: {await authResp.Content.ReadAsStringAsync()}"); return;
        }

        string cst = authResp.Headers.GetValues("CST").FirstOrDefault() ?? "";
        string xst = authResp.Headers.GetValues("X-SECURITY-TOKEN").FirstOrDefault() ?? "";

        // Loop over each epic
        foreach (var epic in epics)
        {
            Console.WriteLine($"\n=========================================================");
            Console.WriteLine($"[*] Fetching {resolution} for {epic} from {fromDate:u} to {toDate:u}");
            Console.WriteLine($"=========================================================");
            
            DateTime currentTo = toDate;
            var times = new List<DateTime>();
            var opens = new List<double>();
            var highs = new List<double>();
            var lows = new List<double>();
            var closes = new List<double>();
            var vols = new List<double>();

            while (currentTo > fromDate)
            {
                string reqTo = currentTo.ToString("yyyy-MM-ddTHH:mm:ss");
                var req = new HttpRequestMessage(HttpMethod.Get, $"/api/v1/prices/{epic}?resolution={resolution}&max=1000&to={reqTo}");
                req.Headers.Add("CST", cst);
                req.Headers.Add("X-SECURITY-TOKEN", xst);

                var dataResp = await client.SendAsync(req);
                if (!dataResp.IsSuccessStatusCode)
                {
                    if (dataResp.StatusCode == System.Net.HttpStatusCode.TooManyRequests)
                    {
                        Console.WriteLine("[!] Rate Limited. Waiting 10s...");
                        await Task.Delay(10000);
                        continue;
                    }
                    Console.WriteLine($"[!] Fetch failed for {epic}: {await dataResp.Content.ReadAsStringAsync()}");
                    break;
                }

                var content = await dataResp.Content.ReadAsStringAsync();
                var root = JsonNode.Parse(content);
                var pricesNode = root?["prices"]?.AsArray();

                if (pricesNode == null || pricesNode.Count == 0)
                {
                    break;
                }

                var batchTimes = new List<DateTime>();
                var batchRecords = new List<(DateTime t, double o, double h, double l, double c, double v)>();

                foreach (var pNode in pricesNode)
                {
                    try
                    {
                        if (pNode == null) continue;
                        var dtStr = pNode["snapshotTimeUTC"]?.ToString();
                        if (!string.IsNullOrEmpty(dtStr) && DateTime.TryParse(dtStr, null, DateTimeStyles.AdjustToUniversal, out var dt))
                        {
                            if (dt >= fromDate && dt <= toDate)
                            {
                                batchRecords.Add((
                                    dt,
                                    (double)(pNode["openPrice"]?["bid"]?.GetValue<decimal>() ?? 0),
                                    (double)(pNode["highPrice"]?["bid"]?.GetValue<decimal>() ?? 0),
                                    (double)(pNode["lowPrice"]?["bid"]?.GetValue<decimal>() ?? 0),
                                    (double)(pNode["closePrice"]?["bid"]?.GetValue<decimal>() ?? 0),
                                    (double)(pNode["lastTradedVolume"]?.GetValue<decimal>() ?? 0)
                                ));
                                batchTimes.Add(dt);
                            }
                        }
                    }
                    catch { }
                }

                if (batchTimes.Count == 0 && pricesNode.Count > 0)
                {
                    DateTime oldestDtInBatch = DateTime.UtcNow;
                    foreach(var pNode in pricesNode) {
                        if (pNode == null) continue;
                        if (DateTime.TryParse(pNode["snapshotTimeUTC"]?.ToString(), null, DateTimeStyles.AdjustToUniversal, out var dt))
                            if (dt < oldestDtInBatch) oldestDtInBatch = dt;
                    }
                    if (oldestDtInBatch < fromDate) break; 
                    currentTo = oldestDtInBatch.AddSeconds(-1);
                    continue; 
                }
                if (batchRecords.Count == 0) break;

                foreach (var b in batchRecords.OrderBy(x => x.t))
                {
                    times.Add(b.t);
                    opens.Add(b.o);
                    highs.Add(b.h);
                    lows.Add(b.l);
                    closes.Add(b.c);
                    vols.Add(b.v);
                }

                var oldestTimeInBatch = batchTimes.Min();
                Console.WriteLine($"[+] Checked up to: {oldestTimeInBatch:u} | Total fetched: {times.Count}");
                
                currentTo = oldestTimeInBatch.AddSeconds(-1);
                await Task.Delay(250); 
            }

            if (times.Count == 0) {
                Console.WriteLine($"[!] No records downloaded in this range for {epic}.");
                continue;
            }

            Console.WriteLine($"\n[*] Fully Downloaded. Processing {times.Count} rows API Schema for {epic}...");
            
            var distinctSorted = times
                .Select((t, i) => new { t, o=opens[i], h=highs[i], l=lows[i], c=closes[i], v=vols[i] })
                .GroupBy(x => x.t)
                .Select(g => g.First())
                .OrderBy(x => x.t)
                .ToList();

            var timeField = new DateTimeDataField("time", DateTimeFormat.DateAndTime);
            var openField = new DataField<double>("open");
            var highField = new DataField<double>("high");
            var lowField = new DataField<double>("low");
            var closeField = new DataField<double>("close");
            var volField = new DataField<double>("volume");
            var schema = new ParquetSchema(timeField, openField, highField, lowField, closeField, volField);

            string rootTarget = Path.Combine(Directory.GetCurrentDirectory(), "..", "..");
            string relativeOutDir = Path.Combine("data", "seed");
            string outDir = Path.Combine(rootTarget, relativeOutDir);
            Directory.CreateDirectory(outDir);

            string fileName = $"{epic}__{resolution}__{fromStr}_{toStr}.parquet";
            string fileOut = Path.Combine(outDir, fileName);

            using var fileStream = File.Create(fileOut);
            using var parquetWriter = await ParquetWriter.CreateAsync(schema, fileStream);
            using var groupWriter = parquetWriter.CreateRowGroup();

            await groupWriter.WriteColumnAsync(new DataColumn(timeField, distinctSorted.Select(x=>x.t).ToArray()));
            await groupWriter.WriteColumnAsync(new DataColumn(openField, distinctSorted.Select(x=>x.o).ToArray()));
            await groupWriter.WriteColumnAsync(new DataColumn(highField, distinctSorted.Select(x=>x.h).ToArray()));
            await groupWriter.WriteColumnAsync(new DataColumn(lowField, distinctSorted.Select(x=>x.l).ToArray()));
            await groupWriter.WriteColumnAsync(new DataColumn(closeField, distinctSorted.Select(x=>x.c).ToArray()));
            await groupWriter.WriteColumnAsync(new DataColumn(volField, distinctSorted.Select(x=>x.v).ToArray()));

            string displayPath = Path.Combine(relativeOutDir, fileName).Replace("\\", "/");
            Console.WriteLine($"[SUCCESS] Saved {distinctSorted.Count} unique candles to {displayPath}");
        }

        Console.WriteLine("\n[INFO] All requested downloads complete. When you run `api_server`, it will parse these Parquet files and inject them locally.");
    }
}

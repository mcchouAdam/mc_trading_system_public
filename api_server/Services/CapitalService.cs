using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Nodes;
using ApiServer.Core;
using ApiServer.Services.Interfaces;

namespace ApiServer.Services;

public class CapitalService : ICapitalService
{
    private readonly HttpClient _httpClient;
    private readonly IRedisClient _redisClient;
    private readonly string _apiKey;

    public CapitalService(HttpClient httpClient, IConfiguration config, IRedisClient redisClient)
    {
        _httpClient = httpClient;
        _httpClient.BaseAddress = new Uri(config["CAPITAL_REST_URL"] ?? "https://demo-api-capital.backend-capital.com");
        _apiKey = config["CAPITAL_API_KEY"] ?? "";
        _redisClient = redisClient;
    }

    private async Task<HttpRequestMessage> CreateRequestAsync(HttpMethod method, string url)
    {
        var db = _redisClient.GetDatabase();
        var cst = await db.StringGetAsync("CAPITAL_CST");
        var token = await db.StringGetAsync("CAPITAL_TOKEN");

        var request = new HttpRequestMessage(method, url);
        request.Headers.Add("X-CAP-API-KEY", _apiKey);
        if (cst.HasValue) request.Headers.Add("CST", cst.ToString());
        if (token.HasValue) request.Headers.Add("X-SECURITY-TOKEN", token.ToString());
        
        return request;
    }

    public async Task<List<object>> GetKlinesAsync(string epic, string resolution, int maxBars, DateTime? to = null)
    {
        var url = $"/api/v1/prices/{epic}?resolution={resolution}&max={maxBars}";
        if (to.HasValue) 
        {
            url += $"&to={to.Value:yyyy-MM-ddTHH:mm:ss}";
        }
        var request = await CreateRequestAsync(HttpMethod.Get, url);
        var response = await _httpClient.SendAsync(request);
        
        if (!response.IsSuccessStatusCode) 
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            Console.WriteLine($"[CapitalService] GetKlines Error {response.StatusCode}: {errorBody}");
            return new List<object>();
        }

        var content = await response.Content.ReadAsStringAsync();
        var data = JsonNode.Parse(content);
        var prices = data?["prices"]?.AsArray();
        var history = new List<object>();

        if (prices != null)
        {
            foreach (var p in prices)
            {
                try
                {
                    var snapshotTimeStr = p?["snapshotTimeUTC"]?.ToString();
                    if (!string.IsNullOrEmpty(snapshotTimeStr))
                    {
                        if (!snapshotTimeStr.EndsWith("Z", StringComparison.OrdinalIgnoreCase)) snapshotTimeStr += "Z";
                        if (DateTimeOffset.TryParse(snapshotTimeStr, out var dto)) {
                            var utcDt = dto.UtcDateTime;
                        double.TryParse(p?["openPrice"]?["bid"]?.ToString(), out var o);
                        double.TryParse(p?["highPrice"]?["bid"]?.ToString(), out var h);
                        double.TryParse(p?["lowPrice"]?["bid"]?.ToString(), out var l);
                        double.TryParse(p?["closePrice"]?["bid"]?.ToString(), out var c);

                        history.Add(new
                        {
                            time = new DateTimeOffset(utcDt).ToUnixTimeSeconds(),
                            open = o,
                            high = h,
                            low = l,
                            close = c,
                        });
                        }
                    }
                }
                catch { }
            }
        }
        return history;
    }

    public async Task<List<object>?> GetClosedTradesAsync(string fromDate, string toDate, int limit = 100)
    {
        var url = $"/api/v1/history/transactions?from={fromDate}&to={toDate}&detailed=true&max={limit}&type=TRADE";
        var request = await CreateRequestAsync(HttpMethod.Get, url);
        var response = await _httpClient.SendAsync(request);
        
        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            Console.WriteLine($"[CapitalService] GetClosedTrades Error {response.StatusCode}: {errorBody}");
            return null;
        }

        var content = await response.Content.ReadAsStringAsync();
        var data = JsonNode.Parse(content);
        var transactions = data?["transactions"]?.AsArray();
        var trades = new List<object>();

        if (transactions != null)
        {
            foreach (var t in transactions)
            {
                var transactionType = t?["transactionType"]?.ToString();
                var note = t?["note"]?.ToString()?.ToLower() ?? "";
                
                if (transactionType == "TRADE" && note.Contains("closed"))
                {
                    double.TryParse(t?["size"]?.ToString(), out var pnl);
                    if (pnl == 0) double.TryParse(t?["profitAndLoss"]?.ToString(), out pnl);

                    var dateUtc = t?["dateUtc"]?.ToString() ?? "";
                    
                    trades.Add(new
                    {
                        id = t?["dealId"]?.ToString() ?? "",
                        epic = t?["instrumentName"]?.ToString() ?? "",
                        date = dateUtc.Split('.')[0].Replace("T", " "),
                        pnl = pnl,
                        is_win = pnl > 0
                    });
                }
            }
        }
        return trades;
    }

    public async Task<bool> ClosePositionAsync(string dealId)
    {
        var request = await CreateRequestAsync(HttpMethod.Delete, $"/api/v1/positions/{dealId}");
        var response = await _httpClient.SendAsync(request);
        return response.IsSuccessStatusCode;
    }

    public async Task<List<object>?> SearchMarketsAsync(string searchTerm)
    {
        var url = $"/api/v1/markets?searchTerm={searchTerm}";
        var request = await CreateRequestAsync(HttpMethod.Get, url);
        var response = await _httpClient.SendAsync(request);
        
        if (!response.IsSuccessStatusCode) return null;

        var content = await response.Content.ReadAsStringAsync();
        var data = JsonNode.Parse(content);
        var markets = data?["markets"]?.AsArray();
        var results = new List<object>();

        if (markets != null)
        {
            foreach (var m in markets)
            {
                results.Add(new
                {
                    epic = m?["epic"]?.ToString() ?? "",
                    name = m?["instrumentName"]?.ToString() ?? ""
                });
            }
        }
        return results;
    }

    public async Task<JsonNode?> GetAccountsAsync()
    {
        var request = await CreateRequestAsync(HttpMethod.Get, "/api/v1/accounts");
        var response = await _httpClient.SendAsync(request);
        if (!response.IsSuccessStatusCode) return null;
        var content = await response.Content.ReadAsStringAsync();
        return JsonNode.Parse(content);
    }

    public async Task<JsonNode?> GetOpenPositionsAsync()
    {
        var request = await CreateRequestAsync(HttpMethod.Get, "/api/v1/positions");
        var response = await _httpClient.SendAsync(request);
        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            Console.WriteLine($"[CapitalService] GetOpenPositions Error {response.StatusCode}: {errorBody}");
            return null;
        }
        var content = await response.Content.ReadAsStringAsync();
        return JsonNode.Parse(content);
    }

    public async Task<bool> PlaceOrderAsync(string epic, string direction, double size)
    {
        var request = await CreateRequestAsync(HttpMethod.Post, "/api/v1/positions");
        var payload = new
        {
            epic = epic,
            direction = direction,
            size = size
        };
        request.Content = System.Net.Http.Json.JsonContent.Create(payload);
        var response = await _httpClient.SendAsync(request);
        return response.IsSuccessStatusCode;
    }

    public async Task<bool> UpdatePositionLimitsAsync(string dealId, double? stopLevel, double? profitLevel)
    {
        var request = await CreateRequestAsync(HttpMethod.Put, $"/api/v1/positions/{dealId}");
        var payload = new Dictionary<string, object>();
        if (stopLevel.HasValue) payload["stopLevel"] = stopLevel.Value;
        if (profitLevel.HasValue) payload["profitLevel"] = profitLevel.Value;
        
        request.Content = System.Net.Http.Json.JsonContent.Create(payload);
        var response = await _httpClient.SendAsync(request);
        return response.IsSuccessStatusCode;
    }

    public async Task<JsonNode?> GetTransactionsAsync(int lastPeriodSeconds)
    {
        var from = DateTime.UtcNow.AddSeconds(-lastPeriodSeconds).ToString("yyyy-MM-ddTHH:mm:ss");
        var to = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss");
        var url = $"/api/v1/history/transactions?from={from}&to={to}&detailed=true";
        
        var request = await CreateRequestAsync(HttpMethod.Get, url);
        var response = await _httpClient.SendAsync(request);
        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            Console.WriteLine($"[CapitalService] GetTransactions Error {response.StatusCode}: {errorBody}");
            return null;
        }
        var content = await response.Content.ReadAsStringAsync();
        return JsonNode.Parse(content);
    }
}

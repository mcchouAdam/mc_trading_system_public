using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using ApiServer.Core;
using ApiServer.Hubs;
using Microsoft.AspNetCore.SignalR;
using NetMQ;
using NetMQ.Sockets;

namespace ApiServer.BackgroundTasks;

public class MarketDataStreamer : BaseBackgroundService
{
    private readonly IServiceProvider _serviceProvider;
    private readonly IHubContext<MarketHub> _hubContext;
    private readonly string _zmqHost;
    private readonly List<string> _subscribedEpics = new() { "BTCUSD", "US100" };

    public MarketDataStreamer(IServiceProvider serviceProvider, IHubContext<MarketHub> hubContext, ILogger<MarketDataStreamer> logger)
        : base(logger)
    {
        _serviceProvider = serviceProvider;
        _hubContext = hubContext;
        _zmqHost = Environment.GetEnvironmentVariable("ZMQ_HOST") ?? "127.0.0.1";
    }

    protected override async Task ExecuteWorkAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Connecting to ZMQ Price Streamer at {Host}:5555...", _zmqHost);
        
        using var subscriber = new SubscriberSocket();
        subscriber.Connect($"tcp://{_zmqHost}:5555");
        
        foreach (var epic in _subscribedEpics)
        {
            subscriber.Subscribe($"PRICE:{epic}:TICK");
        }

        while (!stoppingToken.IsCancellationRequested)
        {
            var msg = new NetMQMessage();
            if (subscriber.TryReceiveMultipartMessage(ref msg))
            {
                if (msg.FrameCount >= 2)
                {
                    var topic = msg[0].ConvertToString();
                    var payload = msg[1].ConvertToString();
                    
                    var parts = topic.Split(':');
                    if (parts.Length >= 2)
                    {
                        var epic = parts[1];
                        await ProcessAndBroadcastTick(epic, payload, stoppingToken);
                    }
                }
            }
            else
            {
                await Task.Delay(1, stoppingToken);
                
                // Periodically check Redis for new subscriptions
                if (DateTime.UtcNow.Second % 30 == 0 && DateTime.UtcNow.Millisecond < 50)
                {
                     await UpdateSubscriptionsFromRedis(subscriber);
                }
            }
        }
    }

    private async Task ProcessAndBroadcastTick(string epic, string message, CancellationToken ct)
    {
        var payload = JsonNode.Parse(message);
        if (payload == null) return;

        var type = (string?)payload["type"];
        if (type != "tick") return;

        var tsNode = payload["timestamp"];
        long ts = tsNode?.GetValue<long>() ?? DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        while (ts > 4000000000) ts /= 1000;

        double.TryParse(payload["bid"]?.ToString(), out var bid);
        if (bid == 0) return;

        var tick = new
        {
            epic = payload["epic"]?.ToString() ?? epic,
            resolution = "MINUTE", 
            time = ts,
            open = bid,
            high = bid,
            low = bid,
            close = bid
        };

        await _hubContext.Clients.Group($"MARKET:{epic}").SendAsync(HubEvents.TICK, tick, ct);
    }

    private async Task UpdateSubscriptionsFromRedis(SubscriberSocket subscriber)
    {
        using var scope = _serviceProvider.CreateScope();
        var redis = scope.ServiceProvider.GetRequiredService<IRedisClient>();
        var db = redis.GetDatabase();
        var value = await db.StringGetAsync("MARKET_DATA_SUBSCRIBE");
        
        if (value.HasValue)
        {
            var epics = JsonSerializer.Deserialize<string[]>(value.ToString());
            if (epics != null)
            {
                foreach (var epic in epics)
                {
                    if (!_subscribedEpics.Contains(epic))
                    {
                        subscriber.Subscribe($"PRICE:{epic}:TICK");
                        _subscribedEpics.Add(epic);
                        _logger.LogInformation("Subscribed to new epic from Redis: {Epic}", epic);
                    }
                }
            }
        }
    }
}

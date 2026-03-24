using Microsoft.AspNetCore.SignalR;

namespace ApiServer.Hubs;

public class MarketHub : Hub
{
    public async Task Subscribe(string epic)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, $"MARKET:{epic}");
        Console.WriteLine($"[MarketHub] Client {Context.ConnectionId} subscribed to {epic}");
    }

    public async Task Unsubscribe(string epic)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, $"MARKET:{epic}");
        Console.WriteLine($"[MarketHub] Client {Context.ConnectionId} unsubscribed from {epic}");
    }
}

using Microsoft.AspNetCore.SignalR;

namespace ApiServer.Hubs;

public class TradeHub : Hub
{
    public override async Task OnConnectedAsync()
    {
        Console.WriteLine($"[TradeHub] Client {Context.ConnectionId} connected.");
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        Console.WriteLine($"[TradeHub] Client {Context.ConnectionId} disconnected.");
        await base.OnDisconnectedAsync(exception);
    }
}

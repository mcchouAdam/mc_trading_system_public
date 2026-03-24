using ApiServer.Services.Interfaces;
using ApiServer.Core;
using ApiServer.Services;
using ApiServer.Context;
using ApiServer.Hubs;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Mvc;

ApiServer.Core.DbConnectionHelper.LoadEnvFile();

var builder = WebApplication.CreateBuilder(args);
var envName = (Environment.GetEnvironmentVariable("ENVIRONMENT") ?? "local").ToLower();

builder.Configuration
    .SetBasePath(Directory.GetCurrentDirectory())
    .AddJsonFile("appsettings.json", optional: true)
    .AddJsonFile($"Config/{envName}.json", optional: false, reloadOnChange: true)
    .AddEnvironmentVariables();

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<ApiServer.Core.Handlers.GlobalExceptionHandler>();

// Configure DI
builder.Services.AddSingleton<IRedisClient, RedisClient>();
builder.Services.AddScoped<IRiskService, RiskService>();
builder.Services.AddHttpClient<ICapitalService, CapitalService>();
builder.Services.AddScoped<IMarketDataService, MarketDataService>();
builder.Services.AddScoped<ApiServer.Repositories.TradeRepository>();
builder.Services.AddScoped<ApiServer.Repositories.MarketCandleRepository>();
builder.Services.AddScoped<ITradeService, TradeService>();
builder.Services.AddScoped<ISystemService, SystemService>();
builder.Services.AddSignalR();

// Entity Framework Core setup
var dbUrl = ApiServer.Core.DbConnectionHelper.GetRequiredConnectionString(builder.Configuration);
builder.Configuration["DATABASE_URL"] = dbUrl;

builder.Services.AddDbContext<TradingDbContext>(options =>
    options.UseNpgsql(dbUrl));

// Configure Background Tasks
builder.Services.AddHostedService<ApiServer.BackgroundTasks.AccountSyncTask>();
builder.Services.AddHostedService<ApiServer.BackgroundTasks.RiskEnforcementTask>();
builder.Services.AddHostedService<ApiServer.BackgroundTasks.MarketDataSyncTask>();
builder.Services.AddHostedService<ApiServer.BackgroundTasks.HistoricalDataSeeder>();
builder.Services.AddHostedService<ApiServer.BackgroundTasks.MarketDataStreamer>();

// Configure CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll",
        builder => builder
            .SetIsOriginAllowed(origin => true) // In production, specify exact origins
            .AllowAnyMethod()
            .AllowAnyHeader()
            .AllowCredentials());
});

var app = builder.Build();

ApiServer.Core.DatabaseSetup.RunDbUpMigrations(dbUrl);

app.UseSwagger();
app.UseSwaggerUI();

app.UseExceptionHandler();
app.UseStatusCodePages();
app.UseWebSockets();
app.UseCors("AllowAll");

app.MapControllers();
app.MapHub<MarketHub>("/hub/market");
app.MapHub<TradeHub>("/hub/trade");

app.Run();

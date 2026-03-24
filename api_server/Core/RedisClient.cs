using StackExchange.Redis;

namespace ApiServer.Core;

public interface IRedisClient
{
    IDatabase GetDatabase();
    ISubscriber GetSubscriber();
}

public class RedisClient : IRedisClient
{
    private readonly ConnectionMultiplexer _redis;

    public RedisClient(IConfiguration configuration)
    {
        var redisHost = configuration["REDIS_HOST"];
        var redisPort = configuration["REDIS_PORT"];
        var redisPassword = configuration["REDIS_PASSWORD"];

        var options = ConfigurationOptions.Parse($"{redisHost}:{redisPort}");
        if (!string.IsNullOrEmpty(redisPassword))
        {
            options.Password = redisPassword;
        }
        options.AbortOnConnectFail = false;
        options.ConnectRetry = 3;
        options.ConnectTimeout = 5000;
        
        _redis = ConnectionMultiplexer.Connect(options);
    }

    public IDatabase GetDatabase() => _redis.GetDatabase();
    public ISubscriber GetSubscriber() => _redis.GetSubscriber();
}

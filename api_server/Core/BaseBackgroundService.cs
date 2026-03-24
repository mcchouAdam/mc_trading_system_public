namespace ApiServer.Core;

public abstract class BaseBackgroundService : BackgroundService
{
    protected readonly ILogger _logger;
    protected virtual int RetryDelayMs => 5000;

    protected BaseBackgroundService(ILogger logger)
    {
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("{Name} is starting.", GetType().Name);

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await ExecuteWorkAsync(stoppingToken);
                break; 
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Unhandled exception in {Name}. Retrying in {Delay}ms.", GetType().Name, RetryDelayMs);
                
                try
                {
                    await Task.Delay(RetryDelayMs, stoppingToken);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }
        }

        _logger.LogInformation("{Name} is shutting down.", GetType().Name);
    }

    protected abstract Task ExecuteWorkAsync(CancellationToken stoppingToken);
}

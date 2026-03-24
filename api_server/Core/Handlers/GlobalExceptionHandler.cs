using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using ApiServer.Core.Exceptions;
using System.Net;

namespace ApiServer.Core.Handlers;

public class GlobalExceptionHandler : IExceptionHandler
{
    private readonly ILogger<GlobalExceptionHandler> _logger;

    public GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger)
    {
        _logger = logger;
    }

    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        _logger.LogError(exception, "An unhandled exception occurred: {Message}", exception.Message);

        var (statusCode, message, details) = exception switch
        {
            AppException appEx => ((int)appEx.StatusCode, appEx.Message, appEx.Details),
            KeyNotFoundException => (StatusCodes.Status404NotFound, "Resource not found", null),
            ArgumentException => (StatusCodes.Status400BadRequest, "Invalid argument provided", null),
            UnauthorizedAccessException => (StatusCodes.Status401Unauthorized, "Unauthorized access", null),
            _ => (StatusCodes.Status500InternalServerError, "Internal Server Error", null)
        };

        var problemDetails = new ProblemDetails
        {
            Status = statusCode,
            Title = message,
            Detail = details?.ToString() ?? exception.Message,
            Instance = httpContext.Request.Path
        };

        if (details != null)
        {
            problemDetails.Extensions["details"] = details;
        }

        httpContext.Response.StatusCode = statusCode;

        await httpContext.Response.WriteAsJsonAsync(problemDetails, cancellationToken);

        return true;
    }
}

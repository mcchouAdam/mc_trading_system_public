using System.Net;

namespace ApiServer.Core.Exceptions;

public abstract class AppException : Exception
{
    public HttpStatusCode StatusCode { get; }
    public object? Details { get; }

    protected AppException(string message, HttpStatusCode statusCode, object? details = null) 
        : base(message)
    {
        StatusCode = statusCode;
        Details = details;
    }
}

public class NotFoundException : AppException
{
    public NotFoundException(string message, object? details = null) 
        : base(message, HttpStatusCode.NotFound, details) { }
}

public class BadRequestException : AppException
{
    public BadRequestException(string message, object? details = null) 
        : base(message, HttpStatusCode.BadRequest, details) { }
}

public class UnauthorizedException : AppException
{
    public UnauthorizedException(string message = "Unauthorized") 
        : base(message, HttpStatusCode.Unauthorized) { }
}

public class ForbiddenException : AppException
{
    public ForbiddenException(string message = "Forbidden") 
        : base(message, HttpStatusCode.Forbidden) { }
}

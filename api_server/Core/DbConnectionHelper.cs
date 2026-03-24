using Microsoft.Extensions.Configuration;

namespace ApiServer.Core;

public static class DbConnectionHelper
{
    public static void LoadEnvFile()
    {
        try { DotNetEnv.Env.TraversePath().Load(); } catch { }
    }

    public static string GetRequiredConnectionString(IConfiguration configuration)
    {
        var user = configuration["POSTGRES_USER"];
        var pass = configuration["POSTGRES_PASSWORD"];
        var host = configuration["POSTGRES_HOST"];
        var port = configuration["POSTGRES_PORT"];
        var db = configuration["POSTGRES_DB"];

        if (string.IsNullOrEmpty(user) || string.IsNullOrEmpty(pass) || string.IsNullOrEmpty(db))
            throw new Exception("PostgreSQL creds (USER/PASS/DB) are missing. Check .env!");

        return $"Host={host};Port={port};Database={db};Username={user};Password={pass};Include Error Detail=true";
    }
}

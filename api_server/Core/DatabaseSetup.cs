using DbUp;
using Microsoft.Extensions.Configuration;

namespace ApiServer.Core;

public static class DatabaseSetup
{
    public static void RunDbUpMigrations(string rawConnectionString)
    {
        Console.WriteLine("\n======================================");
        Console.WriteLine("[DbUp] Starting database migration check...");
        var resources = System.Reflection.Assembly.GetExecutingAssembly().GetManifestResourceNames();
        Console.WriteLine($"[DbUp] Discovered {resources.Length} total embedded resources.");
        foreach(var res in resources)
        {
            if (res.EndsWith(".sql", StringComparison.OrdinalIgnoreCase))
                Console.WriteLine($"[DbUp] Found SQL Resource: {res}");
        }
        Console.WriteLine("======================================\n");

        EnsureDatabase.For.PostgresqlDatabase(rawConnectionString);

        var upgrader = DeployChanges.To
            .PostgresqlDatabase(rawConnectionString)
            .WithScriptsEmbeddedInAssembly(System.Reflection.Assembly.GetExecutingAssembly(), s => s.EndsWith(".sql", StringComparison.OrdinalIgnoreCase))
            .JournalToPostgresqlTable("public", "migration_history")
            .LogToConsole()
            .Build();

        var result = upgrader.PerformUpgrade();

        if (!result.Successful)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine(result.Error);
            Console.ResetColor();
            throw new Exception("Migration failed", result.Error);
        }

        Console.ForegroundColor = ConsoleColor.Green;
        Console.WriteLine("Success! Database migrations applied.");
        Console.ResetColor();
    }
}

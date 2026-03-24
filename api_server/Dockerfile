FROM mcr.microsoft.com/dotnet/sdk:10.0-preview AS build
WORKDIR /src
COPY ["api_server/ApiServer.csproj", "api_server/"]
RUN dotnet restore "api_server/ApiServer.csproj"

COPY api_server/ api_server/
COPY machine_learning/ machine_learning/
WORKDIR "/src/api_server"
RUN dotnet publish "ApiServer.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0-preview AS base
WORKDIR /app
EXPOSE 8080
COPY --from=build /app/publish .

RUN mkdir -p machine_learning data/seed
COPY --from=build /src/machine_learning/model_registry.json ./machine_learning/

COPY data/seed/ ./data/seed/

ENTRYPOINT ["dotnet", "ApiServer.dll"]

FROM mcr.microsoft.com/dotnet/sdk:8.0

WORKDIR /app
COPY QaRunner.csproj /app/QaRunner.csproj
RUN dotnet restore /app/QaRunner.csproj
COPY Program.cs /app/Program.cs
RUN dotnet publish /app/QaRunner.csproj -c Release -o /out

EXPOSE 8090
CMD ["dotnet", "/out/QaRunner.dll"]

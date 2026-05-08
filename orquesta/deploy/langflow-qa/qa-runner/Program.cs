using System.Diagnostics;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Neo4j.Driver;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://0.0.0.0:8090");
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
    options.SerializerOptions.DictionaryKeyPolicy = JsonNamingPolicy.SnakeCaseLower;
    options.SerializerOptions.PropertyNameCaseInsensitive = true;
});

var app = builder.Build();
var workdir = Path.GetFullPath(Environment.GetEnvironmentVariable("QA_RUNNER_WORKDIR") ?? "/work");
Directory.CreateDirectory(workdir);

app.MapGet("/health", () => Results.Json(new
{
    ok = true,
    service = "electro-sur-qa-runner",
    workdir,
    time = DateTimeOffset.UtcNow
}));

app.MapPost("/jobs", async (QaJobRequest request) =>
{
    if (request.Repos.Count == 0)
    {
        return Results.BadRequest(new { error = "Debes enviar al menos un repo." });
    }

    var state = await CreateJob(request, workdir);
    await CloneStage(state, workdir);
    await InspectStage(state, workdir);
    await DotnetStage(state, workdir);
    await SmokeStage(state, workdir);
    await GraphStage(state, workdir);
    var paths = ReportPaths(workdir, state.Report.JobId);

    return Results.Json(new
    {
        job_id = state.Report.JobId,
        status = "completed",
        findings = state.Report.Findings,
        report_json = paths.ReportJson,
        report_md = paths.ReportMd,
        memgraph_cypher = paths.Cypher,
        memgraph_ingested = state.Report.GraphIngest.Success,
        memgraph_error = state.Report.GraphIngest.Error
    });
});

app.MapPost("/pipeline/start", async (JsonElement body) =>
{
    var request = RequestFromBody(body);
    if (request.Repos.Count == 0)
    {
        return Results.BadRequest(new { error = "Debes enviar al menos un repo." });
    }
    var state = await CreateJob(request, workdir);
    return Results.Json(StageResponse("01_start", state, workdir));
});

app.MapPost("/pipeline/clone", async (JsonElement body) =>
{
    var state = await LoadState(ExtractJobId(body), workdir);
    await CloneStage(state, workdir);
    return Results.Json(StageResponse("02_clone", state, workdir));
});

app.MapPost("/pipeline/inspect", async (JsonElement body) =>
{
    var state = await LoadState(ExtractJobId(body), workdir);
    await InspectStage(state, workdir);
    return Results.Json(StageResponse("03_inspect", state, workdir));
});

app.MapPost("/pipeline/dotnet", async (JsonElement body) =>
{
    var state = await LoadState(ExtractJobId(body), workdir);
    await DotnetStage(state, workdir);
    return Results.Json(StageResponse("04_dotnet", state, workdir));
});

app.MapPost("/pipeline/smoke", async (JsonElement body) =>
{
    var state = await LoadState(ExtractJobId(body), workdir);
    await SmokeStage(state, workdir);
    return Results.Json(StageResponse("05_smoke", state, workdir));
});

app.MapPost("/pipeline/graph", async (JsonElement body) =>
{
    var state = await LoadState(ExtractJobId(body), workdir);
    await GraphStage(state, workdir);
    return Results.Json(StageResponse("06_graph", state, workdir));
});

app.MapPost("/pipeline/report", async (JsonElement body) =>
{
    var state = await LoadState(ExtractJobId(body), workdir);
    return Results.Json(StageResponse("07_report", state, workdir, includeMessage: true));
});

app.MapGet("/jobs/{jobId}", async (string jobId) =>
{
    var path = Path.Combine(workdir, "jobs", jobId, "report.json");
    if (!File.Exists(path))
    {
        return Results.NotFound(new { error = "Job no encontrado." });
    }
    var json = await File.ReadAllTextAsync(path);
    return Results.Content(json, "application/json");
});

app.Run();

static async Task<QaJobState> CreateJob(QaJobRequest request, string workdir)
{
    var jobId = $"{DateTimeOffset.UtcNow:yyyyMMdd-HHmmss}-{Guid.NewGuid():N}"[..24];
    var jobDir = Path.Combine(workdir, "jobs", jobId);
    Directory.CreateDirectory(Path.Combine(jobDir, "repos"));

    var state = new QaJobState
    {
        Request = request,
        Report = new QaReport
        {
            JobId = jobId,
            Module = string.IsNullOrWhiteSpace(request.Module) ? "modulo-sin-nombre" : request.Module,
            Environment = request.Environment,
            Notes = request.Notes,
            StartedAt = DateTimeOffset.UtcNow,
        }
    };
    await SaveState(state, workdir);
    return state;
}

static async Task CloneStage(QaJobState state, string workdir)
{
    var reposDir = Path.Combine(workdir, "jobs", state.Report.JobId, "repos");
    Directory.CreateDirectory(reposDir);

    foreach (var repo in state.Request.Repos)
    {
        var name = RepoName(repo);
        var dest = Path.Combine(reposDir, name);
        var repoReport = state.Report.Repos.FirstOrDefault(r => r.Name == name);
        if (repoReport is null)
        {
            repoReport = new RepoReport
            {
                Name = name,
                Url = repo.Url,
                Branch = repo.Branch,
                Kind = repo.Kind,
                Path = dest,
            };
            state.Report.Repos.Add(repoReport);
        }

        if (repoReport.Clone is not null && repoReport.Clone.ReturnCode == 0)
        {
            continue;
        }

        if (Directory.Exists(Path.Combine(dest, ".git")))
        {
            repoReport.Clone = new CommandResult(["git", "clone", "--cached"], dest, DateTimeOffset.UtcNow, DateTimeOffset.UtcNow, 0, "Repositorio ya clonado en esta corrida.", "", false);
            continue;
        }

        repoReport.Clone = await CloneRepo(repo, dest, state.Request.MaxSeconds);
    }
    await SaveState(state, workdir);
}

static async Task InspectStage(QaJobState state, string workdir)
{
    foreach (var repoReport in state.Report.Repos.Where(r => r.Clone?.ReturnCode == 0))
    {
        repoReport.Inventory = DetectRepo(repoReport.Path);
        if (repoReport.Inventory.Frontend && !repoReport.Warnings.Any(w => w.Contains("Frontend detectado", StringComparison.OrdinalIgnoreCase)))
        {
            repoReport.Warnings.Add("Frontend detectado. Este runner base hace inventario y smoke por URL; build Node queda para el runner Node separado.");
        }
    }
    await SaveState(state, workdir);
}

static async Task DotnetStage(QaJobState state, string workdir)
{
    foreach (var repoReport in state.Report.Repos.Where(r => r.Clone?.ReturnCode == 0 && r.Inventory.Dotnet))
    {
        if (repoReport.Checks.Count > 0)
        {
            continue;
        }

        repoReport.Checks.Add(await RunCommand(["dotnet", "--info"], repoReport.Path, 60));
        repoReport.Checks.Add(await RunCommand(["dotnet", "restore"], repoReport.Path, state.Request.MaxSeconds));
        if (state.Request.RunBuilds)
        {
            repoReport.Checks.Add(await RunCommand(["dotnet", "build", "--no-restore", "--configuration", "Release"], repoReport.Path, state.Request.MaxSeconds));
        }
        if (state.Request.RunTests)
        {
            repoReport.Checks.Add(await RunCommand(["dotnet", "test", "--no-build", "--configuration", "Release", "--logger", "trx"], repoReport.Path, state.Request.MaxSeconds));
        }
    }
    await SaveState(state, workdir);
}

static async Task SmokeStage(QaJobState state, string workdir)
{
    state.Report.Smoke = await RunSmoke(state.Request.QaTargets);
    await SaveState(state, workdir);
}

static async Task GraphStage(QaJobState state, string workdir)
{
    state.Report.FinishedAt = DateTimeOffset.UtcNow;
    state.Report.Findings = SummarizeFindings(state.Report);

    var paths = ReportPaths(workdir, state.Report.JobId);
    var cypherText = ToCypher(state.Report);
    state.Report.GraphIngest = await TryIngestMemgraph(cypherText);

    await File.WriteAllTextAsync(paths.ReportMd, ToMarkdown(state.Report, paths.ReportJson));
    await File.WriteAllTextAsync(paths.Cypher, cypherText);
    await SaveState(state, workdir);
}

static object StageResponse(string stage, QaJobState state, string workdir, bool includeMessage = false)
{
    var paths = ReportPaths(workdir, state.Report.JobId);
    var repoSummary = state.Report.Repos.Select(repo => new
    {
        repo.Name,
        repo.Kind,
        clone_ok = repo.Clone?.ReturnCode == 0,
        dotnet = repo.Inventory.Dotnet,
        frontend = repo.Inventory.Frontend,
        gateway = repo.Inventory.Gateway,
        projects = repo.Inventory.Projects.Count,
        controllers = repo.Inventory.Controllers.Count,
        endpoints = repo.Inventory.Endpoints.Count,
        nugets = repo.Inventory.NugetPackages.Count,
        checks_failed = repo.Checks.Count(c => c.ReturnCode != 0),
    });

    var message = includeMessage
        ? $"QA {state.Report.Module} job {state.Report.JobId}: {state.Report.Findings.Count} hallazgos. Reporte: {paths.ReportMd}"
        : null;

    return new
    {
        job_id = state.Report.JobId,
        stage,
        status = "ok",
        module = state.Report.Module,
        environment = state.Report.Environment,
        stage_log = StageLog(stage, state.Report),
        repos = repoSummary,
        smoke_total = state.Report.Smoke.Count,
        smoke_failed = state.Report.Smoke.Count(s => !s.Ok),
        findings = state.Report.Findings,
        report_json = paths.ReportJson,
        report_md = paths.ReportMd,
        memgraph_cypher = paths.Cypher,
        memgraph_ingested = state.Report.GraphIngest.Success,
        memgraph_error = state.Report.GraphIngest.Error,
        message,
    };
}

static object StageLog(string stage, QaReport report)
{
    return stage switch
    {
        "01_start" => new
        {
            title = "Corrida creada",
            items = new[]
            {
                $"job_id={report.JobId}",
                $"module={report.Module}",
                $"environment={report.Environment}",
                $"repos={report.Repos.Count}",
            }
        },
        "02_clone" => new
        {
            title = "Descarga de repos",
            repos = report.Repos.Select(repo => new
            {
                repo.Name,
                repo.Url,
                repo.Branch,
                ok = repo.Clone?.ReturnCode == 0,
                return_code = repo.Clone?.ReturnCode,
                stdout = Tail(repo.Clone?.StdoutTail ?? "", 1200),
                stderr = Tail(repo.Clone?.StderrTail ?? "", 1200),
            }).ToList()
        },
        "03_inspect" => new
        {
            title = "Inventario tecnico",
            repos = report.Repos.Select(repo => new
            {
                repo.Name,
                repo.Inventory.Dotnet,
                repo.Inventory.Frontend,
                repo.Inventory.Gateway,
                solutions = repo.Inventory.Solutions,
                projects = repo.Inventory.Projects,
                package_json = repo.Inventory.PackageJson,
                gateway_configs = repo.Inventory.GatewayConfigs,
                controllers = repo.Inventory.Controllers.Take(30).ToList(),
                endpoints = repo.Inventory.Endpoints.Take(80).ToList(),
                nugets = repo.Inventory.NugetPackages.Take(80).ToList(),
                warnings = repo.Warnings,
            }).ToList()
        },
        "04_dotnet" => new
        {
            title = "Restore build test .NET",
            repos = report.Repos.Select(repo => new
            {
                repo.Name,
                checks = repo.Checks.Select(check => new
                {
                    command = string.Join(" ", check.Command),
                    check.Cwd,
                    check.ReturnCode,
                    check.Timeout,
                    stdout = Tail(check.StdoutTail, 1600),
                    stderr = Tail(check.StderrTail, 1600),
                }).ToList()
            }).ToList()
        },
        "05_smoke" => new
        {
            title = "Smoke Gateway UI",
            targets = report.Smoke.Select(smoke => new
            {
                smoke.Name,
                smoke.Url,
                smoke.ThroughGateway,
                smoke.ExpectedStatus,
                smoke.StatusCode,
                smoke.Ok,
                smoke.Error,
                body = Tail(smoke.BodyHead, 800),
            }).ToList()
        },
        "06_graph" => new
        {
            title = "Memgraph",
            report.GraphIngest.Attempted,
            report.GraphIngest.Success,
            report.GraphIngest.Error,
            nodes = new
            {
                repos = report.Repos.Count,
                nugets = report.Repos.Sum(repo => repo.Inventory.NugetPackages.Count),
                findings = report.Findings.Count,
            }
        },
        "07_report" => new
        {
            title = "Reporte final",
            findings = report.Findings,
            totals = new
            {
                repos = report.Repos.Count,
                smoke = report.Smoke.Count,
                smoke_failed = report.Smoke.Count(s => !s.Ok),
                failed_checks = report.Repos.Sum(repo => repo.Checks.Count(check => check.ReturnCode != 0)),
            }
        },
        _ => new { title = stage }
    };
}

static async Task SaveState(QaJobState state, string workdir)
{
    var paths = ReportPaths(workdir, state.Report.JobId);
    Directory.CreateDirectory(Path.GetDirectoryName(paths.RequestJson)!);
    await File.WriteAllTextAsync(paths.RequestJson, JsonSerializer.Serialize(state.Request, JsonOptions()));
    await File.WriteAllTextAsync(paths.ReportJson, JsonSerializer.Serialize(state.Report, JsonOptions()));
}

static async Task<QaJobState> LoadState(string jobId, string workdir)
{
    var paths = ReportPaths(workdir, jobId);
    if (!File.Exists(paths.RequestJson) || !File.Exists(paths.ReportJson))
    {
        throw new InvalidOperationException($"Job no encontrado: {jobId}");
    }

    var request = JsonSerializer.Deserialize<QaJobRequest>(await File.ReadAllTextAsync(paths.RequestJson), JsonOptions()) ?? new QaJobRequest();
    var report = JsonSerializer.Deserialize<QaReport>(await File.ReadAllTextAsync(paths.ReportJson), JsonOptions()) ?? new QaReport();
    return new QaJobState { Request = request, Report = report };
}

static (string RequestJson, string ReportJson, string ReportMd, string Cypher) ReportPaths(string workdir, string jobId)
{
    var jobDir = Path.Combine(workdir, "jobs", jobId);
    return (
        Path.Combine(jobDir, "request.json"),
        Path.Combine(jobDir, "report.json"),
        Path.Combine(jobDir, "report.md"),
        Path.Combine(jobDir, "memgraph.cypher")
    );
}

static QaJobRequest RequestFromBody(JsonElement body)
{
    var candidate = UnwrapPayload(body);
    return candidate.Deserialize<QaJobRequest>(JsonOptions()) ?? new QaJobRequest();
}

static string ExtractJobId(JsonElement body)
{
    var candidate = UnwrapPayload(body);
    if (TryGetString(candidate, "job_id", out var jobId) || TryGetString(candidate, "jobId", out jobId))
    {
        return jobId;
    }
    throw new InvalidOperationException("No encontre job_id en la respuesta de la etapa anterior.");
}

static JsonElement UnwrapPayload(JsonElement body)
{
    var current = body;
    for (var i = 0; i < 4; i++)
    {
        if (current.ValueKind != JsonValueKind.Object)
        {
            return current;
        }
        if (current.TryGetProperty("result", out var result))
        {
            current = result;
            continue;
        }
        if (current.TryGetProperty("data", out var data))
        {
            current = data;
            continue;
        }
        if (current.TryGetProperty("qa_result", out var qaResult))
        {
            current = qaResult;
            continue;
        }
        return current;
    }
    return current;
}

static bool TryGetString(JsonElement element, string property, out string value)
{
    value = "";
    if (element.ValueKind == JsonValueKind.Object
        && element.TryGetProperty(property, out var prop)
        && prop.ValueKind == JsonValueKind.String)
    {
        value = prop.GetString() ?? "";
        return !string.IsNullOrWhiteSpace(value);
    }
    return false;
}

static JsonSerializerOptions JsonOptions() => new()
{
    WriteIndented = true,
    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    DictionaryKeyPolicy = JsonNamingPolicy.SnakeCaseLower,
    PropertyNameCaseInsensitive = true
};

static string RepoName(RepoSpec spec)
{
    if (!string.IsNullOrWhiteSpace(spec.Name))
    {
        return SafeName(spec.Name);
    }
    var last = spec.Url.TrimEnd('/').Split('/').LastOrDefault() ?? "repo";
    if (last.EndsWith(".git", StringComparison.OrdinalIgnoreCase))
    {
        last = last[..^4];
    }
    return SafeName(last);
}

static string SafeName(string value)
{
    var safe = Regex.Replace(value.Trim(), @"[^a-zA-Z0-9_.-]+", "-").Trim('-');
    return string.IsNullOrWhiteSpace(safe) ? "repo" : safe;
}

static async Task<CommandResult> CloneRepo(RepoSpec spec, string dest, int timeout)
{
    var args = new List<string> { "clone", "--depth", "1" };
    if (!string.IsNullOrWhiteSpace(spec.Branch))
    {
        args.AddRange(["--branch", spec.Branch]);
    }
    args.AddRange([spec.Url, dest]);
    return await RunCommand(["git", .. args], Directory.GetCurrentDirectory(), timeout);
}

static async Task<CommandResult> RunCommand(string[] command, string cwd, int timeoutSeconds)
{
    var started = DateTimeOffset.UtcNow;
    try
    {
        using var process = new Process();
        process.StartInfo = new ProcessStartInfo
        {
            FileName = command[0],
            Arguments = string.Join(" ", command.Skip(1).Select(QuoteArg)),
            WorkingDirectory = cwd,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        process.Start();
        var stdoutTask = process.StandardOutput.ReadToEndAsync();
        var stderrTask = process.StandardError.ReadToEndAsync();
        var waitTask = process.WaitForExitAsync();
        var delayTask = Task.Delay(TimeSpan.FromSeconds(timeoutSeconds));
        var completed = await Task.WhenAny(waitTask, delayTask);
        if (!process.HasExited)
        {
            TryKill(process);
        }
        var stdout = await stdoutTask;
        var stderr = await stderrTask;
        return new CommandResult(command, cwd, started, DateTimeOffset.UtcNow, process.HasExited ? process.ExitCode : 124, Tail(stdout), Tail(stderr), !process.HasExited);
    }
    catch (Exception ex)
    {
        return new CommandResult(command, cwd, started, DateTimeOffset.UtcNow, 127, "", ex.ToString(), false);
    }
}

static string QuoteArg(string arg) => arg.Contains(' ') || arg.Contains('"') ? "\"" + arg.Replace("\"", "\\\"") + "\"" : arg;

static void TryKill(Process process)
{
    try { process.Kill(entireProcessTree: true); } catch { }
}

static string Tail(string value, int max = 12000) => value.Length <= max ? value : value[^max..];

static async Task<GraphIngestResult> TryIngestMemgraph(string cypher)
{
    var uri = Environment.GetEnvironmentVariable("MEMGRAPH_URI");
    if (string.IsNullOrWhiteSpace(uri))
    {
        return new GraphIngestResult(false, false, "MEMGRAPH_URI no configurado.");
    }

    try
    {
        var statements = cypher
            .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Where(statement => !string.IsNullOrWhiteSpace(statement))
            .ToList();

        await using var driver = GraphDatabase.Driver(uri, AuthTokens.None);
        await using var session = driver.AsyncSession();
        foreach (var statement in statements)
        {
            var cursor = await session.RunAsync(statement);
            await cursor.ConsumeAsync();
        }

        return new GraphIngestResult(true, true, null);
    }
    catch (Exception ex)
    {
        return new GraphIngestResult(true, false, Tail(ex.ToString(), 2000));
    }
}

static RepoInventory DetectRepo(string root)
{
    var inventory = new RepoInventory
    {
        Solutions = Find(root, "*.sln", 50),
        Projects = Find(root, "*.csproj", 200),
        PackageJson = Find(root, "package.json", 50),
        GatewayConfigs = FindMany(root, ["ocelot*.json", "*gateway*.json", "nginx*.conf"], 50),
        Controllers = Find(root, "*Controller.cs", 300),
        Appsettings = Find(root, "appsettings*.json", 100),
        FrontendRoutes = FindMany(root, ["*.routing.ts", "*routes*.ts", "app.routes.ts"], 200),
    };
    inventory.Dotnet = inventory.Solutions.Count > 0 || inventory.Projects.Count > 0;
    inventory.Frontend = inventory.PackageJson.Count > 0;
    inventory.Gateway = inventory.GatewayConfigs.Count > 0;
    inventory.NugetPackages = ExtractNugets(root, inventory.Projects);
    inventory.Endpoints = ExtractEndpoints(root, inventory.Controllers);
    return inventory;
}

static List<string> Find(string root, string pattern, int limit) => FindMany(root, [pattern], limit);

static List<string> FindMany(string root, string[] patterns, int limit)
{
    var output = new List<string>();
    foreach (var pattern in patterns)
    {
        foreach (var path in Directory.EnumerateFiles(root, pattern, SearchOption.AllDirectories))
        {
            var parts = path.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            if (parts.Any(p => p is ".git" or "node_modules" or "bin" or "obj" or "dist" or "build"))
            {
                continue;
            }
            output.Add(Path.GetRelativePath(root, path));
            if (output.Count >= limit)
            {
                return output;
            }
        }
    }
    return output;
}

static string ReadSmall(string path, int max = 20000)
{
    try
    {
        var text = File.ReadAllText(path);
        return text.Length <= max ? text : text[..max];
    }
    catch
    {
        return "";
    }
}

static List<NugetPackage> ExtractNugets(string root, List<string> projects)
{
    var packages = new List<NugetPackage>();
    var regex = new Regex("<PackageReference\\s+Include=\"([^\"]+)\"\\s+Version=\"([^\"]+)\"", RegexOptions.IgnoreCase);
    foreach (var project in projects.Take(100))
    {
        var text = ReadSmall(Path.Combine(root, project));
        foreach (Match match in regex.Matches(text))
        {
            packages.Add(new NugetPackage(project, match.Groups[1].Value, match.Groups[2].Value));
        }
    }
    return packages;
}

static List<EndpointInfo> ExtractEndpoints(string root, List<string> controllers)
{
    var endpoints = new List<EndpointInfo>();
    var routeRegex = new Regex("\\[(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|Route)\\s*(?:\\(\\s*\"([^\"]*)\"\\s*\\))?\\]", RegexOptions.IgnoreCase);
    var classRouteRegex = new Regex("\\[Route\\s*\\(\\s*\"([^\"]+)\"\\s*\\)\\]", RegexOptions.IgnoreCase);
    foreach (var controller in controllers.Take(120))
    {
        var text = ReadSmall(Path.Combine(root, controller));
        var routeMatch = classRouteRegex.Match(text);
        var baseRoute = routeMatch.Success ? routeMatch.Groups[1].Value : "";
        foreach (Match match in routeRegex.Matches(text))
        {
            endpoints.Add(new EndpointInfo(controller, match.Groups[1].Value, $"{baseRoute}/{match.Groups[2].Value}".Trim('/')));
        }
    }
    return endpoints;
}

static async Task<List<SmokeResult>> RunSmoke(List<QaTarget> targets)
{
    var client = new HttpClient { Timeout = TimeSpan.FromSeconds(20) };
    var results = new List<SmokeResult>();
    foreach (var target in targets)
    {
        var started = DateTimeOffset.UtcNow;
        try
        {
            var response = await client.GetAsync(target.Url);
            var body = await response.Content.ReadAsStringAsync();
            results.Add(new SmokeResult(target.Name, target.Url, target.ThroughGateway, target.ExpectedStatus, (int)response.StatusCode, (int)response.StatusCode == target.ExpectedStatus, Tail(body, 1000), null, started, DateTimeOffset.UtcNow));
        }
        catch (Exception ex)
        {
            results.Add(new SmokeResult(target.Name, target.Url, target.ThroughGateway, target.ExpectedStatus, null, false, "", ex.Message, started, DateTimeOffset.UtcNow));
        }
    }
    return results;
}

static List<Finding> SummarizeFindings(QaReport report)
{
    var findings = new List<Finding>();
    foreach (var repo in report.Repos)
    {
        foreach (var check in repo.Checks.Where(c => c.ReturnCode != 0))
        {
            var cmd = string.Join(" ", check.Command);
            var severity = cmd.Contains("dotnet build") || cmd.Contains("dotnet test") ? "Alta" : "Media";
            findings.Add(new Finding(severity, repo.Name, $"Comando fallo: {cmd}", Tail((check.StderrTail + "\n" + check.StdoutTail).Trim(), 1200)));
        }
        if (repo.Inventory.Dotnet && repo.Inventory.NugetPackages.Count == 0)
        {
            findings.Add(new Finding("Baja", repo.Name, "No se detectaron PackageReference directos", "Puede usar Directory.Packages.props o paquetes transitivos; requiere revisar el esquema NuGet real de la empresa."));
        }
    }
    foreach (var smoke in report.Smoke.Where(s => !s.Ok))
    {
        findings.Add(new Finding("Alta", smoke.ThroughGateway ? "gateway" : "smoke", $"Smoke target fallo: {smoke.Name}", smoke.Error ?? $"HTTP {smoke.StatusCode}, esperado {smoke.ExpectedStatus}"));
    }
    return findings;
}

static string ToMarkdown(QaReport report, string jsonPath)
{
    var sb = new StringBuilder();
    sb.AppendLine($"# QA Electro Sur: {report.Module}");
    sb.AppendLine();
    sb.AppendLine($"- Ambiente: `{report.Environment}`");
    sb.AppendLine($"- Job: `{report.JobId}`");
    sb.AppendLine($"- Inicio: `{report.StartedAt}`");
    sb.AppendLine($"- Fin: `{report.FinishedAt}`");
    sb.AppendLine();
    sb.AppendLine("## Hallazgos");
    if (report.Findings.Count == 0)
    {
        sb.AppendLine("- Sin hallazgos criticos por ahora.");
    }
    foreach (var finding in report.Findings)
    {
        sb.AppendLine($"- [{finding.Severity}] {finding.Area}: {finding.Title}");
    }
    sb.AppendLine();
    sb.AppendLine("## Inventario");
    foreach (var repo in report.Repos)
    {
        sb.AppendLine($"- `{repo.Name}`: dotnet={repo.Inventory.Dotnet} frontend={repo.Inventory.Frontend} gateway={repo.Inventory.Gateway}");
        sb.AppendLine($"- `{repo.Name}` proyectos={repo.Inventory.Projects.Count} controllers={repo.Inventory.Controllers.Count} endpoints={repo.Inventory.Endpoints.Count} nugets={repo.Inventory.NugetPackages.Count}");
    }
    sb.AppendLine();
    sb.AppendLine("## Smoke");
    if (report.Smoke.Count == 0)
    {
        sb.AppendLine("- No se definieron URLs de smoke/gateway.");
    }
    foreach (var smoke in report.Smoke)
    {
        sb.AppendLine($"- {(smoke.Ok ? "OK" : "FALLO")}: `{smoke.Name}` {smoke.Url}");
    }
    sb.AppendLine();
    sb.AppendLine("## Memgraph");
    sb.AppendLine(report.GraphIngest.Success
        ? "- Ingestion al grafo: OK."
        : $"- Ingestion al grafo: pendiente/fallo. {report.GraphIngest.Error}");
    sb.AppendLine();
    sb.AppendLine($"Reporte JSON: `{Path.GetFileName(jsonPath)}`");
    return sb.ToString();
}

static string EscapeCypher(string value) => value.Replace("\\", "\\\\").Replace("'", "\\'");

static string ToCypher(QaReport report)
{
    var sb = new StringBuilder();
    sb.AppendLine($"MERGE (m:Modulo {{name:'{EscapeCypher(report.Module)}'}}) SET m.environment='{EscapeCypher(report.Environment)}', m.last_job='{report.JobId}';");
    foreach (var repo in report.Repos)
    {
        sb.AppendLine($"MERGE (r:Repo {{name:'{EscapeCypher(repo.Name)}'}}) SET r.url='{EscapeCypher(repo.Url)}', r.kind='{EscapeCypher(repo.Kind)}';");
        sb.AppendLine($"MATCH (m:Modulo {{name:'{EscapeCypher(report.Module)}'}}), (r:Repo {{name:'{EscapeCypher(repo.Name)}'}}) MERGE (m)-[:USA_REPO]->(r);");
        foreach (var package in repo.Inventory.NugetPackages.Take(300))
        {
            sb.AppendLine($"MERGE (p:NuGet {{name:'{EscapeCypher(package.Name)}', version:'{EscapeCypher(package.Version)}'}});");
            sb.AppendLine($"MATCH (r:Repo {{name:'{EscapeCypher(repo.Name)}'}}), (p:NuGet {{name:'{EscapeCypher(package.Name)}', version:'{EscapeCypher(package.Version)}'}}) MERGE (r)-[:USA_NUGET {{project:'{EscapeCypher(package.Project)}'}}]->(p);");
        }
    }
    foreach (var finding in report.Findings.Take(300))
    {
        sb.AppendLine($"MATCH (m:Modulo {{name:'{EscapeCypher(report.Module)}'}}) CREATE (h:Hallazgo {{job_id:'{report.JobId}', severity:'{EscapeCypher(finding.Severity)}', area:'{EscapeCypher(finding.Area)}', title:'{EscapeCypher(finding.Title)}', evidence:'{EscapeCypher(finding.Evidence)}'}}) MERGE (m)-[:TIENE_HALLAZGO]->(h);");
    }
    return sb.ToString();
}

record RepoSpec(string Url, string? Branch = null, string? Name = null, string Kind = "auto");
record QaTarget(string Name, string Url, int ExpectedStatus = 200, bool ThroughGateway = true);
record CommandResult(string[] Command, string Cwd, DateTimeOffset StartedAt, DateTimeOffset FinishedAt, int ReturnCode, string StdoutTail, string StderrTail, bool Timeout);
record NugetPackage(string Project, string Name, string Version);
record EndpointInfo(string File, string Verb, string Route);
record SmokeResult(string Name, string Url, bool ThroughGateway, int ExpectedStatus, int? StatusCode, bool Ok, string BodyHead, string? Error, DateTimeOffset StartedAt, DateTimeOffset FinishedAt);
record Finding(string Severity, string Area, string Title, string Evidence);
record GraphIngestResult(bool Attempted, bool Success, string? Error);

class RepoInventory
{
    public bool Dotnet { get; set; }
    public bool Frontend { get; set; }
    public bool Gateway { get; set; }
    public List<string> Solutions { get; set; } = [];
    public List<string> Projects { get; set; } = [];
    public List<string> PackageJson { get; set; } = [];
    public List<string> GatewayConfigs { get; set; } = [];
    public List<string> Controllers { get; set; } = [];
    public List<string> Appsettings { get; set; } = [];
    public List<string> FrontendRoutes { get; set; } = [];
    public List<NugetPackage> NugetPackages { get; set; } = [];
    public List<EndpointInfo> Endpoints { get; set; } = [];
}

class QaJobRequest
{
    public string Module { get; set; } = "";
    public string Environment { get; set; } = "qa";
    public List<RepoSpec> Repos { get; set; } = [];
    public List<QaTarget> QaTargets { get; set; } = [];
    public string? Notes { get; set; }
    public bool RunBuilds { get; set; } = true;
    public bool RunTests { get; set; } = true;
    public bool RunFrontendBuild { get; set; } = true;
    public int MaxSeconds { get; set; } = 900;
}

class RepoReport
{
    public string Name { get; set; } = "";
    public string Url { get; set; } = "";
    public string? Branch { get; set; }
    public string Kind { get; set; } = "auto";
    public string Path { get; set; } = "";
    public CommandResult? Clone { get; set; }
    public RepoInventory Inventory { get; set; } = new();
    public List<CommandResult> Checks { get; set; } = [];
    public List<string> Warnings { get; set; } = [];
}

class QaReport
{
    public string JobId { get; set; } = "";
    public string Module { get; set; } = "";
    public string Environment { get; set; } = "";
    public string? Notes { get; set; }
    public DateTimeOffset StartedAt { get; set; }
    public DateTimeOffset FinishedAt { get; set; }
    public List<RepoReport> Repos { get; set; } = [];
    public List<SmokeResult> Smoke { get; set; } = [];
    public List<Finding> Findings { get; set; } = [];
    public GraphIngestResult GraphIngest { get; set; } = new(false, false, null);
}

class QaJobState
{
    public QaJobRequest Request { get; set; } = new();
    public QaReport Report { get; set; } = new();
}

param(
    [int]$Port = 5055,
    [switch]$InstallDeps,
    [switch]$SkipInstall,
    [switch]$SkipBrowser,
    [switch]$OpenAdmin
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BindHost = "127.0.0.1"
Set-Location -LiteralPath $ProjectRoot

Write-Host ""
Write-Host "AI SOLUTION production-style Flask website runner" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example." -ForegroundColor Yellow
    Write-Host "For production, open .env and add your Gemini/reCAPTCHA keys plus strong admin credentials." -ForegroundColor Yellow
    Write-Host ""
}

function Test-PythonRuntime {
    param(
        [string]$Command,
        [string[]]$PrefixArgs = @(),
        [string]$Label = "Python"
    )

    if (-not $Command) {
        return $null
    }

    $probe = "import importlib, sys; required = ['flask', 'flask_sqlalchemy', 'flask_wtf', 'psycopg', 'email_validator']; [importlib.import_module(name) for name in required]; print(sys.executable)"

    try {
        $output = & $Command @PrefixArgs -c $probe 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            return [pscustomobject]@{
                Label = $Label
                Command = $Command
                PrefixArgs = $PrefixArgs
                Executable = ($output | Select-Object -Last 1).Trim()
            }
        }
    } catch {
        return $null
    }

    return $null
}

function Resolve-PythonRuntime {
    $candidates = @()
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        $candidates += [pscustomobject]@{ Command = $venvPython; PrefixArgs = @(); Label = "Existing virtual environment" }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $candidates += [pscustomobject]@{ Command = $pythonCommand.Source; PrefixArgs = @(); Label = "System python" }
    }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $candidates += [pscustomobject]@{ Command = $pyLauncher.Source; PrefixArgs = @("-3"); Label = "Python launcher" }
    }

    foreach ($candidate in $candidates) {
        $runtime = Test-PythonRuntime -Command $candidate.Command -PrefixArgs $candidate.PrefixArgs -Label $candidate.Label
        if ($runtime) {
            return $runtime
        }
    }

    if ($SkipInstall) {
        throw "No usable Python runtime with the required packages was found."
    }

    if (-not $InstallDeps) {
        throw "No usable Python runtime with the required packages was found. Re-run RUN_AI_SOLUTION.ps1 with -InstallDeps on a machine with internet access if you want the script to create its own virtual environment."
    }

    if (-not $pythonCommand) {
        throw "Python is not available on PATH, so the script cannot create a virtual environment automatically."
    }

    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
        & $pythonCommand.Source -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Virtual environment creation failed."
        }
    }

    Write-Host "Installing required packages..." -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip upgrade failed."
    }
    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }

    $runtime = Test-PythonRuntime -Command $venvPython -Label "Fresh virtual environment"
    if ($runtime) {
        return $runtime
    }

    throw "Dependencies were installed, but the runtime probe still failed."
}

function Invoke-Python {
    param([string[]]$Arguments)
    & $PythonRuntime.Command @($PythonRuntime.PrefixArgs) @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("Python command failed: " + ($Arguments -join " "))
    }
}

function Get-AppRuntimeMetadata {
    $probe = @'
from app import app

print(f"ADMIN_ROUTE_PREFIX={app.config.get('ADMIN_ROUTE_PREFIX', '/secure-admin')}")
print(f"DATABASE_RUNTIME_LABEL={app.config.get('DATABASE_RUNTIME_LABEL', 'unknown')}")
print(f"DATABASE_RUNTIME_FALLBACK={1 if app.config.get('DATABASE_RUNTIME_FALLBACK', False) else 0}")
'@

    try {
        $output = & $PythonRuntime.Command @($PythonRuntime.PrefixArgs) -c $probe 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            $metadata = @{
                admin_route_prefix = "/secure-admin"
                database_runtime_label = "unknown"
                database_runtime_fallback = $false
            }

            foreach ($line in $output) {
                if ($line -match "^(?<key>[A-Z_]+)=(?<value>.*)$") {
                    switch ($matches["key"]) {
                        "ADMIN_ROUTE_PREFIX" {
                            if ($matches["value"]) {
                                $metadata.admin_route_prefix = $matches["value"]
                            }
                        }
                        "DATABASE_RUNTIME_LABEL" {
                            if ($matches["value"]) {
                                $metadata.database_runtime_label = $matches["value"]
                            }
                        }
                        "DATABASE_RUNTIME_FALLBACK" {
                            $metadata.database_runtime_fallback = ($matches["value"] -eq "1")
                        }
                    }
                }
            }

            return [pscustomobject]$metadata
        }
    } catch {
        return $null
    }

    return $null
}

function Test-PortInUse {
    param([int]$CandidatePort)
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $CandidatePort)
        $listener.Start()
        $listener.Stop()
        return $false
    } catch {
        return $true
    }
}

$PythonRuntime = Resolve-PythonRuntime

Write-Host "Using Python runtime: $($PythonRuntime.Executable)" -ForegroundColor Cyan
Write-Host "Runtime source: $($PythonRuntime.Label)" -ForegroundColor DarkGray
Write-Host ""

while (Test-PortInUse -CandidatePort $Port) {
    Write-Host "Port $Port is already in use. Trying $($Port + 1)..." -ForegroundColor Yellow
    $Port += 1
}

Write-Host ""
Write-Host "Preparing application database..." -ForegroundColor Cyan
Write-Host "If PostgreSQL is unavailable, the app will fall back to a local SQLite database automatically." -ForegroundColor DarkGray
Invoke-Python -Arguments @("-m", "flask", "--app", "app", "init-db")

$RuntimeMetadata = Get-AppRuntimeMetadata
$AdminRoutePrefix = "/secure-admin"
if ($RuntimeMetadata -and $RuntimeMetadata.admin_route_prefix) {
    $AdminRoutePrefix = [string]$RuntimeMetadata.admin_route_prefix
}
if (-not $AdminRoutePrefix.StartsWith("/")) {
    $AdminRoutePrefix = "/$AdminRoutePrefix"
}

$DatabaseRuntimeLabel = "unknown"
$DatabaseFallbackNote = ""
if ($RuntimeMetadata -and $RuntimeMetadata.database_runtime_label) {
    $DatabaseRuntimeLabel = [string]$RuntimeMetadata.database_runtime_label
}
if ($RuntimeMetadata -and $RuntimeMetadata.database_runtime_fallback) {
    $DatabaseFallbackNote = " (SQLite fallback active)"
}

$PublicUrl = "http://${BindHost}:$Port"
$AdminLoginUrl = "$PublicUrl$AdminRoutePrefix/login"
$AutoOpenUrl = if ($OpenAdmin) { $AdminLoginUrl } else { $PublicUrl }

Write-Host ""
Write-Host "Starting AI SOLUTION website..." -ForegroundColor Green
Write-Host "Public site:  $PublicUrl" -ForegroundColor Green
Write-Host "Admin login:  $AdminLoginUrl" -ForegroundColor Green
Write-Host "Database:     $DatabaseRuntimeLabel$DatabaseFallbackNote" -ForegroundColor DarkGray
Write-Host "Stop server:  Press Ctrl+C in this window" -ForegroundColor DarkGray
Write-Host ""

if (-not $SkipBrowser) {
    try {
        Start-Process -WindowStyle Hidden -FilePath "powershell" -ArgumentList @(
            "-NoProfile",
            "-Command",
            "Start-Sleep -Seconds 2; Start-Process '$AutoOpenUrl'"
        ) | Out-Null
    } catch {
        Write-Host "Browser auto-open skipped. You can open the URL manually." -ForegroundColor Yellow
    }
}

& $PythonRuntime.Command @($PythonRuntime.PrefixArgs) -m flask --app app run --host $BindHost --port $Port
exit $LASTEXITCODE

param(
    [int]$Port = 8016,
    [string]$RequestFile = ".\sample_request.json",
    [int]$StartupTimeoutSec = 20,
    [int]$ObserveTimeoutSec = 45
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$runtimeDir = Join-Path $PSScriptRoot "runtime"
if (-not (Test-Path $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$serverOut = Join-Path $runtimeDir "selfcheck_${stamp}_server_out.log"
$serverErr = Join-Path $runtimeDir "selfcheck_${stamp}_server_err.log"
$requestOut = Join-Path $runtimeDir "selfcheck_${stamp}_request_out.log"
$requestErr = Join-Path $runtimeDir "selfcheck_${stamp}_request_err.log"

function Read-LogText {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return ""
    }

    try {
        $fs = New-Object System.IO.FileStream($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        $sr = New-Object System.IO.StreamReader($fs)
        try {
            return $sr.ReadToEnd()
        }
        finally {
            $sr.Dispose()
            $fs.Dispose()
        }
    }
    catch {
        return ""
    }
}

$serverProc = $null
$requestProc = $null

try {
    Write-Host "[1/4] Starting server on port $Port ..." -ForegroundColor Cyan
    $serverArgs = @(
        "-m", "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "$Port",
        "--log-level", "info"
    )

    $serverProc = Start-Process python -ArgumentList $serverArgs -PassThru -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr

    $startupOk = $false
    $startupDeadline = (Get-Date).AddSeconds($StartupTimeoutSec)
    while ((Get-Date) -lt $startupDeadline) {
        Start-Sleep -Milliseconds 300
        if ($serverProc.HasExited) {
            throw "Server process exited early. See $serverErr"
        }

        $content = (Read-LogText -Path $serverOut) + "`n" + (Read-LogText -Path $serverErr)
        if ($content -match "Application startup complete\.") {
            $startupOk = $true
            break
        }
    }

    if (-not $startupOk) {
        throw "Server startup timeout after $StartupTimeoutSec seconds. See $serverErr"
    }

    Write-Host "[2/4] Sending render request ..." -ForegroundColor Cyan
    $requestPath = Resolve-Path $RequestFile
    $invokeCmd = "Invoke-RestMethod -Uri 'http://127.0.0.1:$Port/v1/video/render' -Method Post -ContentType 'application/json' -InFile '$requestPath' | Out-Null"
    $requestProc = Start-Process powershell -ArgumentList @("-NoProfile", "-Command", $invokeCmd) -PassThru -RedirectStandardOutput $requestOut -RedirectStandardError $requestErr

    Write-Host "[3/4] Observing logs for up to $ObserveTimeoutSec seconds ..." -ForegroundColor Cyan
    $markers = @(
        @{ Name = "startup"; Pattern = "\[startup\]"; Required = $true },
        @{ Name = "access_post"; Pattern = "POST /v1/video/render"; Required = $true },
        @{ Name = "api_entry"; Pattern = "\[api\] render request received"; Required = $true },
        @{ Name = "graph_nodes"; Pattern = "\[graph\] node="; Required = $true },
        @{ Name = "audio"; Pattern = "\[audio\]"; Required = $false },
        @{ Name = "llm"; Pattern = "\[llm\]"; Required = $false },
        @{ Name = "render"; Pattern = "\[render\]"; Required = $false }
    )

    $results = @{}
    foreach ($m in $markers) {
        $results[$m.Name] = $false
    }

    $observeDeadline = (Get-Date).AddSeconds($ObserveTimeoutSec)
    while ((Get-Date) -lt $observeDeadline) {
        Start-Sleep -Milliseconds 500

        $joined = (Read-LogText -Path $serverOut) + "`n" + (Read-LogText -Path $serverErr)
        foreach ($m in $markers) {
            if (-not $results[$m.Name] -and $joined -match $m.Pattern) {
                $results[$m.Name] = $true
            }
        }

        $requiredMissing = $markers | Where-Object { $_.Required -and -not $results[$_.Name] }
        if ($requiredMissing.Count -eq 0) {
            break
        }
    }

    if ($requestProc -and -not $requestProc.HasExited) {
        Stop-Process -Id $requestProc.Id -Force -ErrorAction SilentlyContinue
    }

    Write-Host "[4/4] Summary" -ForegroundColor Cyan
    $table = foreach ($m in $markers) {
        [PSCustomObject]@{
            Marker = $m.Name
            Required = $m.Required
            Seen = $results[$m.Name]
        }
    }
    $table | Format-Table -AutoSize

    $missingRequired = $markers | Where-Object { $_.Required -and -not $results[$_.Name] }
    if ($missingRequired) {
        Write-Host "Missing required markers:" -ForegroundColor Red
        $missingRequired | ForEach-Object { Write-Host " - $($_.Name)" -ForegroundColor Red }
        Write-Host "Server log: $serverErr"
        Write-Host "Request stderr: $requestErr"
        exit 2
    }

    Write-Host "All required markers were observed." -ForegroundColor Green
    Write-Host "Server log: $serverErr"
    Write-Host "Request stderr: $requestErr"
}
finally {
    if ($requestProc -and -not $requestProc.HasExited) {
        Stop-Process -Id $requestProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($serverProc -and -not $serverProc.HasExited) {
        Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
    }
}


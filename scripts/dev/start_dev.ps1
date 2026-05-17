param(
    [int]$Port = 8005,
    [switch]$NoReload,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$arguments = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "$Port"
)

if (-not $NoReload) {
    $arguments += @(
        "--reload",
        "--reload-dir", "app",
        "--reload-exclude", "runtime",
        "--reload-exclude", "log"
    )
}

Write-Host "Launching:" -ForegroundColor Cyan
Write-Host "python $($arguments -join ' ')"

if ($WhatIf) {
    Write-Host "WhatIf enabled: command was not executed." -ForegroundColor Yellow
    exit 0
}

python @arguments

<#
.SYNOPSIS
  Start MinIO, FastAPI backend, and Next.js frontend (Windows).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\start_full_stack.ps1
  .\scripts\start_full_stack.ps1 -SkipFrontend
#>
param(
  [string]$RepoRoot = (Split-Path $PSScriptRoot -Parent),
  [string]$VenvPython = "",
  [switch]$SkipFrontend,
  [switch]$SkipMinio
)

$ErrorActionPreference = "Stop"

if (-not $VenvPython) {
  $candidates = @(
    (Join-Path $RepoRoot ".venv311\Scripts\python.exe"),
    (Join-Path $RepoRoot ".venv\Scripts\python.exe")
  )
  foreach ($c in $candidates) {
    if (Test-Path $c) { $VenvPython = $c; break }
  }
}
if (-not (Test-Path $VenvPython)) {
  throw "Python venv not found. Create: py -3.11 -m venv .venv311"
}

Write-Host "Using Python: $VenvPython" -ForegroundColor DarkGray
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $VenvPython -m pip install -q "mcp[cli]>=1.27.1" "pywin32>=306" 2>&1 | Out-Null
$ErrorActionPreference = $prevEap
$depsOk = & $VenvPython -c "import pywintypes; from mcp.server.fastmcp import FastMCP" 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "WARNING: MCP dependencies missing in venv. Run: pip install -r requirements.txt" -ForegroundColor Yellow
  Write-Host $depsOk -ForegroundColor Yellow
}

function Stop-PortListener([int]$Port) {
  Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object {
      if (Get-Process -Id $_ -ErrorAction SilentlyContinue) {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
      }
    }
}

function Stop-UvicornProcesses() {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*uvicorn*app.main*' } |
    ForEach-Object {
      Write-Host "Stopping stale uvicorn PID $($_.ProcessId)" -ForegroundColor DarkGray
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "=== HFU Anatomy Chatbot - full stack ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"

if (-not $SkipMinio) {
  Write-Host ""
  Write-Host "[1/3] Starting MinIO (Docker)..."
  Push-Location $RepoRoot
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  docker compose --profile minio up -d minio 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0) {
    Write-Host "MinIO start skipped (Docker not running). Use -SkipMinio or start Docker Desktop." -ForegroundColor Yellow
  }
  $ErrorActionPreference = $prevEap
  Pop-Location
} else {
  Write-Host ""
  Write-Host "[1/3] Skipping MinIO"
}

Write-Host "[2/3] Stopping old listeners on 8000..."
Stop-UvicornProcesses
Stop-PortListener 8000
Start-Sleep -Seconds 1

$backendCmd = @(
  "Set-Location '$RepoRoot'"
  "`$env:STORAGE_PROVIDER='minio'"
  "`$env:MINIO_ENABLED='true'"
  "`$env:MINIO_ENDPOINT='localhost:9000'"
  "`$env:MINIO_ACCESS_KEY='minioadmin'"
  "`$env:MINIO_SECRET_KEY='minioadmin'"
  "`$env:MINIO_BUCKET='anatomy-images'"
  "`$env:MINIO_SECURE='false'"
  "`$env:PYTHONPATH='$RepoRoot'"
  "Write-Host 'Backend API: http://127.0.0.1:8000/docs' -ForegroundColor Green"
  "& '$VenvPython' -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
) -join "; "

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Sleep -Seconds 8

$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
  $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)").CommandLine
  if ($cmd -like "*$VenvPython*") {
    Write-Host "Backend verified on venv Python (PID $($listener.OwningProcess))" -ForegroundColor Green
  } else {
    Write-Host "WARNING: port 8000 is NOT using the venv Python:" -ForegroundColor Yellow
    Write-Host "  $cmd" -ForegroundColor Yellow
    Write-Host "  Stop other uvicorn processes and restart with this script." -ForegroundColor Yellow
  }
} else {
  Write-Host "WARNING: nothing listening on port 8000 yet (backend may still be starting)." -ForegroundColor Yellow
}

if (-not $SkipFrontend) {
  Write-Host "[3/3] Stopping old listeners on 3000..."
  Stop-PortListener 3000

  $frontendCmd = @(
    "Set-Location '$RepoRoot\frontend'"
    "if (-not (Test-Path node_modules)) { npm install }"
    "Write-Host 'Frontend UI: http://127.0.0.1:3000' -ForegroundColor Green"
    "npm run dev"
  ) -join "; "

  Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
} else {
  Write-Host "[3/3] Skipping frontend"
}

Write-Host ""
Write-Host "=== Started ===" -ForegroundColor Cyan
Write-Host "  UI:       http://127.0.0.1:3000"
Write-Host "  API:      http://127.0.0.1:8000/docs"
Write-Host "  MinIO:    http://127.0.0.1:9001"
Write-Host "  LM Studio must be running on http://127.0.0.1:1234/v1"
Write-Host ""
Write-Host "See RUNBOOK.md for full documentation."

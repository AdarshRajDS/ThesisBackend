# Reset textbook RAG corpus: PDFs, Chroma indices, extracted figures, local outputs.
# Does NOT remove: data/hub (embedding models), anatomy_mcp/exports, exportable catalog.
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

# Chroma locks files while the API is running — stop backend/MCP Python first.
$venvPython = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*$([IO.Path]::Combine($repoRoot, '.venv311'))*"
}
if ($venvPython) {
    Write-Host "Stopping $($venvPython.Count) backend .venv311 process(es) so Chroma can be cleared..."
    $venvPython | Stop-Process -Force
    Start-Sleep -Seconds 2
}

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim().Trim('"'), "Process")
        }
    }
}

$hfHome = $env:HF_HOME
if (-not $hfHome) { $hfHome = "data" }

$dirsToClear = @(
    (Join-Path $hfHome "raw"),
    (Join-Path $hfHome "processed"),
    (Join-Path $hfHome "outputs"),
    (Join-Path $hfHome "images"),
    "outputs",
    "uploads"
)

Write-Host "HF_HOME / data root: $hfHome"
Write-Host ""

foreach ($dir in $dirsToClear) {
    if (-not (Test-Path -LiteralPath $dir)) {
        Write-Host "[skip] $dir (not found)"
        continue
    }
    $count = (Get-ChildItem -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object).Count
    Remove-Item -LiteralPath $dir -Recurse -Force
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Write-Host "[cleared] $dir ($count items removed)"
}

# Recreate expected processed subdirs
$processed = Join-Path $hfHome "processed"
New-Item -ItemType Directory -Path (Join-Path $processed "images") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $processed "chroma") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $processed "multimodal_chroma") -Force | Out-Null

# Optional legacy chroma at data/chroma
$legacyChroma = Join-Path $hfHome "chroma"
if (Test-Path -LiteralPath $legacyChroma) {
    Remove-Item -LiteralPath $legacyChroma -Recurse -Force
    Write-Host "[cleared] $legacyChroma"
}

# Clear MinIO / Supabase figure objects when configured
$py = Join-Path $repoRoot ".venv311\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host ""
Write-Host "Clearing object storage bucket (if reachable)..."
& $py -c @"
from app.services.object_storage import (
    _minio_client,
    _using_supabase,
    _supabase_client,
    settings,
)

removed = 0
if _using_supabase():
    client = _supabase_client()
    if client:
        bucket = settings.supabase_bucket
        try:
            items = client.storage.from_(bucket).list() or []
            for item in items:
                name = item.get('name') if isinstance(item, dict) else getattr(item, 'name', None)
                if name:
                    client.storage.from_(bucket).remove([name])
                    removed += 1
        except Exception as exc:
            print(f'Supabase clear skipped: {exc}')
        else:
            print(f'Supabase bucket {bucket}: removed {removed} top-level object(s)')
else:
    client = _minio_client()
    if client and settings.minio_enabled:
        bucket = settings.minio_bucket
        try:
            if client.bucket_exists(bucket):
                for obj in client.list_objects(bucket, recursive=True):
                    client.remove_object(bucket, obj.object_name)
                    removed += 1
            print(f'MinIO bucket {bucket}: removed {removed} object(s)')
        except Exception as exc:
            print(f'MinIO clear skipped: {exc}')
    else:
        print('MinIO not configured or unreachable — local /outputs only')
"@

Write-Host ""
Write-Host "Done. Restart the FastAPI backend, then upload your new PDF."
Write-Host "Kept: data/hub (models), anatomy_mcp/exports, label catalogs."

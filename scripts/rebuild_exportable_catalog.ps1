# Build anatomy_mcp/label_index/exportable_catalog.json from Z-Anatomy Startup.blend
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim().Trim('"'), "Process")
        }
    }
}

$blender = $env:BLENDER_BIN
if (-not $blender) { $blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }
$blend = $env:Z_ANATOMY_BLEND
if (-not $blend) { throw "Set Z_ANATOMY_BLEND in .env" }

$script = Join-Path $repoRoot "anatomy_mcp\blender_scripts\build_exportable_catalog.py"
Write-Host "Writing catalog under anatomy_mcp\label_index\ ..."
& $blender --background $blend --python $script

# Build anatomy_mcp/exports/scene_scan/annotations_full.json from Z-Anatomy Startup.blend
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
if (-not $blender) {
    $blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
}
if (-not (Test-Path -LiteralPath $blender)) {
    throw "Blender not found at: $blender. Set BLENDER_BIN in .env to your blender.exe path."
}

$blend = $env:Z_ANATOMY_BLEND
if (-not $blend) {
    $blend = "C:\Users\Admin\Downloads\Z-Anatomy (1)\Z-Anatomy\Startup.blend"
}
if (-not (Test-Path -LiteralPath $blend)) {
    throw "Blend file not found at: $blend. Set Z_ANATOMY_BLEND in .env"
}

$script = Join-Path $repoRoot "anatomy_mcp\blender_scripts\scan_annotations_full.py"
Write-Host "Blender: $blender"
Write-Host "Blend:   $blend"
Write-Host "Writing annotation scan to anatomy_mcp\exports\scene_scan\ ..."
& $blender --background $blend --python $script

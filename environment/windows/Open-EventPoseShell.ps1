$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Set-OpenEBEnvironment.ps1')

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Write-Host 'OpenEB 5.2.0 environment loaded for this child shell.'
Write-Host "Project: $projectRoot"
Write-Host "MV_HAL_PLUGIN_PATH: $env:MV_HAL_PLUGIN_PATH"
Write-Host 'Keep OpenEB/Stream and h5py training work in separate Python processes.'

& powershell.exe -NoLogo -NoExit -Command "Set-Location -LiteralPath '$projectRoot'"
if ($LASTEXITCODE -ne 0) { throw "Child PowerShell exited with code $LASTEXITCODE" }

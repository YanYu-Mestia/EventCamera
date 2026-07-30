$ErrorActionPreference = 'Stop'

$OpenEBRoot = 'D:\OpenEB_Dev\openeb'
$OpenEBVcpkgBin = 'D:\OpenEB_Dev\vcpkg-2024.11.16\installed\x64-windows\bin'
$OpenEBPython = Join-Path $OpenEBRoot 'py3venv\Scripts\python.exe'

$requiredPaths = @(
    $OpenEBRoot,
    (Join-Path $OpenEBRoot 'build\bin\Release'),
    (Join-Path $OpenEBRoot 'build\lib\Release'),
    (Join-Path $OpenEBRoot 'build\py3\Release'),
    (Join-Path $OpenEBRoot 'build\lib\metavision\hal\plugins'),
    (Join-Path $OpenEBRoot 'build\lib\hdf5\plugin'),
    $OpenEBVcpkgBin,
    $OpenEBPython
)
foreach ($path in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required OpenEB path is missing: $path" }
}

$env:MV_HAL_PLUGIN_PATH = Join-Path $OpenEBRoot 'build\lib\metavision\hal\plugins'
$env:HDF5_PLUGIN_PATH = Join-Path $OpenEBRoot 'build\lib\hdf5\plugin'
$prepend = @(
    (Join-Path $OpenEBRoot 'build\bin\Release'),
    (Join-Path $OpenEBRoot 'build\lib\Release'),
    (Join-Path $OpenEBRoot 'build\py3\Release'),
    $OpenEBVcpkgBin
)
$pathParts = @($prepend + ($env:PATH -split ';' | Where-Object { $_ })) | Select-Object -Unique
$env:PATH = $pathParts -join ';'

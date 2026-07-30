$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Set-OpenEBEnvironment.ps1')

$bin = Join-Path $OpenEBRoot 'build\bin\Release'
$plugin = Join-Path $env:MV_HAL_PLUGIN_PATH 'hal_plugin_prophesee.dll'
$diagnosticRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("EventPoseFinal-openeb-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $diagnosticRoot | Out-Null

try {
    $version = (& (Join-Path $bin 'metavision_software_info.exe') -v 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $version -ne '5.2.0') { throw "Unexpected OpenEB version: $version" }
    if (-not (Test-Path -LiteralPath $plugin -PathType Leaf)) { throw "Production HAL plugin missing: $plugin" }

    $eventsCsv = Join-Path $diagnosticRoot 'events.csv'
    $rawFile = Join-Path $diagnosticRoot 'official_test.raw'
    $decodedCsv = Join-Path $diagnosticRoot 'decoded.csv'
    @(
        '10,20,1,1000'
        '11,20,0,2000'
        '12,21,1,3000'
        '13,21,0,4000'
        '14,22,1,5000'
        '15,22,0,6000'
        '16,23,1,7000'
        '17,23,0,8000'
        '18,24,1,9000'
        '19,24,0,10000'
    ) | Set-Content -LiteralPath $eventsCsv -Encoding ascii

    & (Join-Path $bin 'metavision_evt2_raw_file_encoder.exe') $rawFile $eventsCsv | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'EVT2 encoder failed.' }
    & (Join-Path $bin 'metavision_evt2_raw_file_decoder.exe') $rawFile $decodedCsv | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'EVT2 decoder failed.' }
    $decodedCount = @(Get-Content -LiteralPath $decodedCsv | Where-Object { $_ -and -not $_.StartsWith('%') }).Count
    if ($decodedCount -ne 10) { throw "Expected 10 decoded events, got $decodedCount" }

    $fileInfo = (& (Join-Path $bin 'metavision_file_info.exe') -i $rawFile 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "OpenEB could not inspect the valid EVT2 file:`n$fileInfo" }

    $pythonResult = (& $OpenEBPython -c "import metavision_sdk_stream,sys; print(sys.version.split()[0])" 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Python Stream import failed: $pythonResult" }

    $cameraOutput = (& (Join-Path $bin 'metavision_hal_ls.exe') -v 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw "HAL enumeration failed: $cameraOutput" }
    $cameraState = if ($cameraOutput -match 'No device found') { 'not connected (expected until hardware is available)' } else { $cameraOutput }

    Write-Output "OpenEB version: $version"
    Write-Output 'HAL plugin: found'
    Write-Output "EVT2 round-trip: $decodedCount events"
    Write-Output "Python Stream import: OK ($pythonResult)"
    Write-Output "Camera: $cameraState"
}
finally {
    if (Test-Path -LiteralPath $diagnosticRoot) {
        $resolvedDiagnostic = [System.IO.Path]::GetFullPath($diagnosticRoot)
        $resolvedTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
        if ($resolvedDiagnostic.StartsWith($resolvedTemp, [System.StringComparison]::OrdinalIgnoreCase) -and
            (Split-Path -Leaf $resolvedDiagnostic).StartsWith('EventPoseFinal-openeb-')) {
            Remove-Item -LiteralPath $resolvedDiagnostic -Recurse -Force
        }
    }
}

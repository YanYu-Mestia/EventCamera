# Windows OpenEB 5.2.0

## Verified state

- OpenEB source/build root: `D:\OpenEB_Dev\openeb`
- OpenEB version: 5.2.0
- Python: `D:\OpenEB_Dev\openeb\py3venv\Scripts\python.exe` (3.11.6)
- HAL plugin: `D:\OpenEB_Dev\openeb\build\lib\metavision\hal\plugins\hal_plugin_prophesee.dll`
- No event camera was available during verification.

Run the repeatable diagnostic from PowerShell:

```powershell
& D:\EventPoseFinal\environment\windows\Test-OpenEB.ps1
```

Open a child PowerShell with the required process-local paths:

```powershell
& D:\EventPoseFinal\environment\windows\Open-EventPoseShell.ps1
```

The diagnostic creates a valid ten-event EVT2 RAW file using OpenEB's own encoder, decodes and inspects it, then removes the temporary fixture. `tests/fixtures/test_dummy.invalid.raw` is only a historical custom byte stream and must not be used to validate OpenEB.

## DLL guardrail

The OpenEB build uses HDF5 1.14.2, while `h5py 3.16.0` in the existing Windows environment uses HDF5 2.0.0. Loading OpenEB Stream and h5py in the same Python process can fail according to import order. Keep Windows OpenEB ingestion in its own process and write portable intermediate data for WSL; run training and h5py-dependent processing separately in WSL.

This organization pass does not rebuild OpenEB or modify the existing environment.

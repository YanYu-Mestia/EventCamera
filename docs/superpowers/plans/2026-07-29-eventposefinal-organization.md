# EventPoseFinal Organization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `D:\EventPoseFinal` as the single, flat, verified working entry point for the event-camera pose-estimation project without deleting or modifying any existing project source, dataset, environment, installer, or experiment artifact.

**Architecture:** Copy the existing Git worktree byte-for-byte, then extract only the known project-owned code and supplied documents into a few functional folders. Keep large data, third-party repositories, OpenEB build products, and Python environments at their existing paths, exposing them through ignored local configuration and Windows junctions; Windows owns OpenEB ingestion and diagnostics, while WSL owns data processing and model work.

**Tech Stack:** Git, PowerShell 7/Windows PowerShell, Windows junctions, OpenEB/Metavision SDK 5.2.0, Python 3.11, WSL Ubuntu, Bash, TOML, SHA-256 inventories.

---

## File Map

The migration creates or modifies only the following project files. Files described as “byte-for-byte copy” are not refactored in this pass.

| Path under `D:\EventPoseFinal` | Responsibility |
| --- | --- |
| `.gitignore` | Exclude local paths, junction targets, data, environments, model artifacts, caches, and generated experiments. |
| `README.md` | State the verified project stage and give the Windows/WSL entry points. |
| `configs/paths.example.toml` | Committable reference for all external Windows and WSL paths. |
| `configs/paths.local.toml` | Ignored machine-local path configuration. |
| `scripts/data/dhp19_dataset.py` | Byte-for-byte copy of the loose DHP19 loader; still contains dummy labels and is not production-ready. |
| `scripts/data/event_to_voxel.py` | Byte-for-byte copy of the NumPy voxel demonstration. |
| `scripts/data/view_npy.py` | Byte-for-byte copy of the preprocessed-voxel viewer. |
| `scripts/diagnostics/test_camera.py` | Byte-for-byte copy of the future-camera probe. |
| `scripts/diagnostics/generate_invalid_raw.py` | Byte-for-byte copy of `generate_raw.py`, renamed to make its non-OpenEB format visible. |
| `scripts/diagnostics/filter_benchmark_demo.py` | Byte-for-byte copy of `test_filter.py`, renamed to make its fabricated output visible. |
| `tests/fixtures/test_dummy.invalid.raw` | Byte-for-byte copy of the custom byte stream; explicitly not an OpenEB RAW fixture. |
| `environment/windows/Set-OpenEBEnvironment.ps1` | Configure process-local DLL, plugin, executable, and Python paths. |
| `environment/windows/Open-EventPoseShell.ps1` | Open a prepared Windows shell without permanently changing the user environment. |
| `environment/windows/Test-OpenEB.ps1` | Generate a valid EVT2 fixture, round-trip it, inspect it, and report camera availability. |
| `environment/wsl/check_environment.sh` | Report WSL paths, package availability, PyTorch/CUDA state, and missing training packages. |
| `data/README.md` | Explain ignored dataset junctions. |
| `third_party/README.md` | Explain ignored third-party junctions. |
| `docs/inventory/assets.tsv` | Flat provenance inventory: source, target, class, status, size, time, and SHA-256. |
| `docs/inventory/README.md` | Explain trust labels, renamed files, excluded installer, and source preservation. |
| `docs/notes/*.docx` | Byte-for-byte copies of the six supplied historical notes. |
| `docs/notes/README.md` | Mark the DOCX notes as historical and non-authoritative. |
| `docs/research/*` | Byte-for-byte copies of the research TXT, PDF, and flowchart PNG. |
| `docs/research/README.md` | Record the purpose and provenance of the research material. |
| `docs/setup/windows-openeb.md` | Verified OpenEB status, one-command checks, and the HDF5 DLL guardrail. |
| `docs/setup/wsl.md` | Verified WSL boundary, current inventory command, and deferred setup work. |

`experiments` is not created while it is empty. It will appear only when a real run produces content, and its generated contents remain ignored.

## Safety Rules Used by Every Task

- Run organization commands from `D:\Code\EventCamera` unless a step says otherwise.
- Stop immediately if `D:\EventPoseFinal` exists before Task 2; inspect it instead of merging or overwriting it.
- Copy first and compare SHA-256. Do not move, rename, edit, or delete anything at the old paths.
- Do not rebuild OpenEB, modify either vcpkg tree, install packages, push Git commits, or copy third-party repositories into Git.
- Preserve the staged `README.md` blob `d00ba81a02d5a6c46375f5a657823e26fd98345d` and staged `.gitignore` blob `29efeee484fedfdeb0f1712bf076cbfd11099e9a` across the initial worktree copy.
- The organization pass remains uncommitted for user review. Do not stage migrated code or documents during execution.
- Cleanup is restricted to the migration audit directory and valid OpenEB fixture generated by this plan. Old project folders, datasets, environments, installers, and experiment artifacts remain untouched.

### Task 1: Record the Immutable Preflight Snapshot

**Files:**
- Create temporarily: `%TEMP%\EventPoseFinal-migration-20260729\repository.txt`
- Create temporarily: `%TEMP%\EventPoseFinal-migration-20260729\source-paths.tsv`
- Create temporarily: `%TEMP%\EventPoseFinal-migration-20260729\source-working-tree.tsv`

- [ ] **Step 1: Assert that the target is absent and resolve the temporary audit directory**

Run in PowerShell:

```powershell
$ErrorActionPreference = 'Stop'
$sourceRoot = 'D:\Code\EventCamera'
$targetRoot = 'D:\EventPoseFinal'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$resolvedTempParent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$resolvedMigrationTemp = [System.IO.Path]::GetFullPath($migrationTemp)
if (-not $resolvedMigrationTemp.StartsWith($resolvedTempParent, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Audit path escaped the temporary directory: $resolvedMigrationTemp"
}
if (Test-Path -LiteralPath $targetRoot) {
    throw 'D:\EventPoseFinal already exists. Stop for inspection; do not merge or overwrite it.'
}
New-Item -ItemType Directory -Path $migrationTemp -Force | Out-Null
Write-Output "SOURCE=$sourceRoot"
Write-Output "TARGET_ABSENT=$(-not (Test-Path -LiteralPath $targetRoot))"
Write-Output "AUDIT=$resolvedMigrationTemp"
```

Expected: `TARGET_ABSENT=True`, and `AUDIT` resolves beneath the current user's Windows temporary directory.

- [ ] **Step 2: Capture Git identity, history, remote, and staged-user-change hashes**

Run:

```powershell
$sourceRoot = 'D:\Code\EventCamera'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$repositorySnapshot = @(
    "source=$sourceRoot"
    "branch=$(git -C $sourceRoot branch --show-current)"
    "head=$(git -C $sourceRoot rev-parse HEAD)"
    "origin_main=$(git -C $sourceRoot rev-parse origin/main)"
    "origin=$(git -C $sourceRoot remote get-url origin)"
    "readme_index=$(git -C $sourceRoot rev-parse :README.md)"
    "gitignore_index=$(git -C $sourceRoot rev-parse :.gitignore)"
    'status_begin'
    (git -C $sourceRoot status --short --branch)
    'status_end'
)
$repositorySnapshot | Set-Content -LiteralPath (Join-Path $migrationTemp 'repository.txt') -Encoding utf8
Get-Content -LiteralPath (Join-Path $migrationTemp 'repository.txt')
```

Expected:

```text
branch=main
origin_main=49f505cf269dfdfcec36dc64dc58ecc9632f8d52
origin=https://github.com/YanYu-Mestia/EventCamera.git
readme_index=d00ba81a02d5a6c46375f5a657823e26fd98345d
gitignore_index=29efeee484fedfdeb0f1712bf076cbfd11099e9a
```

The exact `head=` value is the plan commit at execution time. Status must show only the already-known staged `README.md` and `.gitignore` changes before migration starts.

- [ ] **Step 3: Capture every in-scope root and its classification**

Run:

```powershell
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$sourcePaths = @(
    [pscustomobject]@{ Path='D:\Code\EventCamera'; Class='git-source'; Required=$true },
    [pscustomobject]@{ Path='D:\Code\event_camera'; Class='loose-code'; Required=$true },
    [pscustomobject]@{ Path='D:\DHP19'; Class='dataset-raw'; Required=$true },
    [pscustomobject]@{ Path='D:\DHP19_preprocessed'; Class='dataset-derived'; Required=$true },
    [pscustomobject]@{ Path='D:\event_camera'; Class='empty-legacy'; Required=$false },
    [pscustomobject]@{ Path='D:\Event_Project'; Class='third-party-parent'; Required=$true },
    [pscustomobject]@{ Path='D:\MMPose'; Class='third-party-parent'; Required=$true },
    [pscustomobject]@{ Path='D:\OpenEB_Dev'; Class='sdk-parent'; Required=$true },
    [pscustomobject]@{ Path='D:\RPG_vid2e'; Class='third-party-parent'; Required=$true },
    [pscustomobject]@{ Path='D:\vcpkg-2024.11.16'; Class='unconfirmed-vcpkg'; Required=$false },
    [pscustomobject]@{ Path='D:\OpenEB_Dev\vcpkg-2024.11.16'; Class='openeb-vcpkg'; Required=$true },
    [pscustomobject]@{ Path='D:\OpenEB_Dev\openeb'; Class='openeb-5.2.0'; Required=$true }
)
$sourcePaths | ForEach-Object {
    $exists = Test-Path -LiteralPath $_.Path
    if ($_.Required -and -not $exists) { throw "Required source is missing: $($_.Path)" }
    [pscustomobject]@{ Path=$_.Path; Class=$_.Class; Required=$_.Required; Exists=$exists }
} | Export-Csv -LiteralPath (Join-Path $migrationTemp 'source-paths.tsv') -Delimiter "`t" -NoTypeInformation -Encoding utf8
Import-Csv -LiteralPath (Join-Path $migrationTemp 'source-paths.tsv') -Delimiter "`t" | Format-Table -AutoSize
```

Expected: every `Required=True` row also has `Exists=True`. The empty legacy folder and unconfirmed duplicate vcpkg tree are recorded but do not block organization.

- [ ] **Step 4: Hash the source repository working tree without traversing `.git`**

Run:

```powershell
$sourceRoot = 'D:\Code\EventCamera'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$gitDirectoryPrefix = (Join-Path $sourceRoot '.git') + [System.IO.Path]::DirectorySeparatorChar
Get-ChildItem -LiteralPath $sourceRoot -Recurse -File -Force |
    Where-Object { -not $_.FullName.StartsWith($gitDirectoryPrefix, [System.StringComparison]::OrdinalIgnoreCase) } |
    ForEach-Object {
        [pscustomobject]@{
            RelativePath = [System.IO.Path]::GetRelativePath($sourceRoot, $_.FullName)
            Length = $_.Length
            SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    } | Sort-Object RelativePath |
    Export-Csv -LiteralPath (Join-Path $migrationTemp 'source-working-tree.tsv') -Delimiter "`t" -NoTypeInformation -Encoding utf8
Import-Csv -LiteralPath (Join-Path $migrationTemp 'source-working-tree.tsv') -Delimiter "`t" | Format-Table -AutoSize
```

Expected: the list includes `.gitignore`, `README.md`, the approved organization spec, and this implementation plan.

- [ ] **Step 5: Checkpoint the source before copying**

Run:

```powershell
$sourceRoot = 'D:\Code\EventCamera'
git -C $sourceRoot status --short --branch
git -C $sourceRoot diff --cached --check
```

Expected: branch `main`, only the pre-existing staged line-ending changes, and no whitespace-error output from `git diff --cached --check`.

### Task 2: Copy the Git Worktree to the New Root

**Files:**
- Create: `D:\EventPoseFinal\` as an exact initial copy of `D:\Code\EventCamera\`, including `.git`

- [ ] **Step 1: Copy the source repository without following junctions**

Run:

```powershell
$sourceRoot = 'D:\Code\EventCamera'
$targetRoot = 'D:\EventPoseFinal'
if (Test-Path -LiteralPath $targetRoot) { throw 'Target appeared after preflight; stop.' }
& robocopy.exe $sourceRoot $targetRoot /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XJ /NFL /NDL /NP
$robocopyExit = $LASTEXITCODE
if ($robocopyExit -gt 7) { throw "robocopy failed with exit code $robocopyExit" }
Write-Output "ROBOCOPY_SUCCESS=$robocopyExit"
```

Expected: `ROBOCOPY_SUCCESS` is between 1 and 7. (`robocopy` uses nonzero success codes.)

- [ ] **Step 2: Compare every copied working-tree file to the preflight hash list**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$sourceManifest = Import-Csv -LiteralPath (Join-Path $migrationTemp 'source-working-tree.tsv') -Delimiter "`t"
$copyProblems = foreach ($row in $sourceManifest) {
    $copiedPath = Join-Path $targetRoot $row.RelativePath
    if (-not (Test-Path -LiteralPath $copiedPath -PathType Leaf)) {
        "MISSING`t$($row.RelativePath)"
        continue
    }
    $copiedHash = (Get-FileHash -LiteralPath $copiedPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($copiedHash -ne $row.SHA256) { "HASH_MISMATCH`t$($row.RelativePath)" }
}
if ($copyProblems) { $copyProblems; throw 'Initial worktree copy verification failed.' }
Write-Output "WORKTREE_COPY_VERIFIED=$($sourceManifest.Count)"
```

Expected: `WORKTREE_COPY_VERIFIED=` followed by the number of source working-tree files, with no missing or mismatch rows.

- [ ] **Step 3: Verify the copied `.git` state against the source snapshot**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$expected = @{}
Get-Content -LiteralPath (Join-Path $migrationTemp 'repository.txt') |
    Where-Object { $_ -match '^[a-z_]+=' } |
    ForEach-Object { $key, $value = $_ -split '=', 2; $expected[$key] = $value }

$actual = @{
    branch = git -C $targetRoot branch --show-current
    head = git -C $targetRoot rev-parse HEAD
    origin_main = git -C $targetRoot rev-parse origin/main
    origin = git -C $targetRoot remote get-url origin
    readme_index = git -C $targetRoot rev-parse :README.md
    gitignore_index = git -C $targetRoot rev-parse :.gitignore
}
foreach ($key in $actual.Keys) {
    if ($actual[$key] -ne $expected[$key]) { throw "$key differs: expected $($expected[$key]), got $($actual[$key])" }
}
$actual.GetEnumerator() | Sort-Object Key | Format-Table -AutoSize
git -C $targetRoot status --short --branch
```

Expected: all values match the source snapshot, and the two pre-existing staged changes remain staged and content-identical.

- [ ] **Step 4: Confirm the remote baseline is still an ancestor**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
git -C $targetRoot merge-base --is-ancestor 49f505cf269dfdfcec36dc64dc58ecc9632f8d52 HEAD
if ($LASTEXITCODE -ne 0) { throw 'The original GitHub commit is not an ancestor of the copied HEAD.' }
Write-Output 'ORIGIN_BASELINE_ANCESTOR=True'
```

Expected: `ORIGIN_BASELINE_ANCESTOR=True`.

### Task 3: Add the Minimal Skeleton and Ignore Boundaries

**Files:**
- Modify: `D:\EventPoseFinal\.gitignore`
- Create: `D:\EventPoseFinal\configs\paths.example.toml`
- Create: `D:\EventPoseFinal\data\README.md`
- Create: `D:\EventPoseFinal\third_party\README.md`
- Create directories only when populated: `scripts/data`, `scripts/diagnostics`, `tests/fixtures`, `docs/setup`, `docs/research`, `docs/notes`, `docs/inventory`, `environment/windows`, `environment/wsl`

- [ ] **Step 1: Create only the directories that receive files in this plan**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$directories = @(
    'configs',
    'scripts\data',
    'scripts\diagnostics',
    'tests\fixtures',
    'docs\setup',
    'docs\research',
    'docs\notes',
    'docs\inventory',
    'data',
    'third_party',
    'environment\windows',
    'environment\wsl'
)
foreach ($relative in $directories) {
    New-Item -ItemType Directory -Path (Join-Path $targetRoot $relative) -Force | Out-Null
}
if (Test-Path -LiteralPath (Join-Path $targetRoot 'experiments')) {
    throw 'experiments should not be created until a real run produces content.'
}
```

Expected: all listed directories exist, and `experiments` remains absent.

- [ ] **Step 2: Extend `.gitignore` without discarding its pre-existing staged content**

Use `apply_patch` on `D:\EventPoseFinal\.gitignore` to append exactly:

```gitignore

# Machine-local project paths
configs/paths.local.toml

# Datasets and generated experiments
data/*
!data/README.md
experiments/

# Independent third-party repositories and SDK trees
third_party/*
!third_party/README.md

# Model and training artifacts
*.pth
*.pt
*.ckpt
*.onnx
checkpoints/
runs/
wandb/

# Local array and event data
*.npy
*.npz
*.aedat
*.aedat4
*.dat
*.h5
*.hdf5
*.raw
!tests/fixtures/test_dummy.invalid.raw
```

Do not normalize or otherwise rewrite the existing lines during this step.

- [ ] **Step 3: Create the committable path template**

Use `apply_patch` to create `D:\EventPoseFinal\configs\paths.example.toml`:

```toml
[windows]
project_root = "D:/EventPoseFinal"
dhp19_raw = "D:/DHP19"
dhp19_preprocessed = "D:/DHP19_preprocessed"
openeb_root = "D:/OpenEB_Dev/openeb"
openeb_vcpkg = "D:/OpenEB_Dev/vcpkg-2024.11.16"
openeb_python = "D:/OpenEB_Dev/openeb/py3venv/Scripts/python.exe"
mmpose = "D:/MMPose/mmpose"
v2e_experiments = "D:/Event_Project/v2e_exps_public"
rpg_vid2e = "D:/RPG_vid2e/rpg_vid2e"

[wsl]
project_root = "/mnt/d/EventPoseFinal"
dhp19_raw = "/mnt/d/DHP19"
dhp19_preprocessed = "/mnt/d/DHP19_preprocessed"
python = "/home/mestia/miniconda3/bin/python"
```

- [ ] **Step 4: Create the two link-boundary READMEs**

Use `apply_patch` to create `D:\EventPoseFinal\data\README.md`:

```markdown
# Local data links

This directory contains ignored Windows junctions only. The actual datasets remain at `D:\DHP19` and `D:\DHP19_preprocessed`; WSL code should use `/mnt/d/DHP19` and `/mnt/d/DHP19_preprocessed` directly.
```

Use `apply_patch` to create `D:\EventPoseFinal\third_party\README.md`:

```markdown
# Local third-party links

This directory contains ignored Windows junctions to independent repositories and SDK sources. Their contents and Git histories do not belong to the EventPoseFinal repository.
```

- [ ] **Step 5: Verify ignore behavior before any junction is created**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
git -C $targetRoot check-ignore -q configs/paths.local.toml
if ($LASTEXITCODE -ne 0) { throw 'paths.local.toml is not ignored.' }
git -C $targetRoot check-ignore -q data/DHP19/example.npy
if ($LASTEXITCODE -ne 0) { throw 'Dataset content is not ignored.' }
git -C $targetRoot check-ignore -q third_party/openeb/CMakeLists.txt
if ($LASTEXITCODE -ne 0) { throw 'Third-party content is not ignored.' }
git -C $targetRoot check-ignore -q experiments/run-001/model.pth
if ($LASTEXITCODE -ne 0) { throw 'Experiment output is not ignored.' }
git -C $targetRoot check-ignore data/README.md third_party/README.md
if ($LASTEXITCODE -eq 0) { throw 'Tracked link-boundary README is unexpectedly ignored.' }
Write-Output 'IGNORE_BOUNDARIES=OK'
```

Expected: `IGNORE_BOUNDARIES=OK`.

### Task 4: Extract and Verify Project-Owned Files and Documents

**Files:**
- Create byte-for-byte: the seven code/fixture targets and nine supplied document/research targets listed below
- Create generated: `D:\EventPoseFinal\docs\inventory\assets.tsv`
- Create: `D:\EventPoseFinal\docs\inventory\README.md`
- Create: `D:\EventPoseFinal\docs\notes\README.md`
- Create: `D:\EventPoseFinal\docs\research\README.md`

- [ ] **Step 1: Define the complete flat copy map and trust labels**

Run:

```powershell
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$copyMap = @(
    [pscustomobject]@{ Source='D:\Code\event_camera\dhp19_dataset.py'; Target='scripts\data\dhp19_dataset.py'; Class='project-code'; Trust='prototype-dummy-labels' },
    [pscustomobject]@{ Source='D:\OpenEB_Dev\openeb\event_to_voxel.py'; Target='scripts\data\event_to_voxel.py'; Class='project-code'; Trust='prototype' },
    [pscustomobject]@{ Source='D:\OpenEB_Dev\openeb\view_npy.py'; Target='scripts\data\view_npy.py'; Class='project-code'; Trust='prototype-hard-coded-path' },
    [pscustomobject]@{ Source='D:\OpenEB_Dev\openeb\test_camera.py'; Target='scripts\diagnostics\test_camera.py'; Class='project-code'; Trust='future-camera-probe' },
    [pscustomobject]@{ Source='D:\OpenEB_Dev\openeb\generate_raw.py'; Target='scripts\diagnostics\generate_invalid_raw.py'; Class='project-code'; Trust='invalid-openeb-format-demo' },
    [pscustomobject]@{ Source='D:\OpenEB_Dev\openeb\test_filter.py'; Target='scripts\diagnostics\filter_benchmark_demo.py'; Class='project-code'; Trust='fabricated-output-demo' },
    [pscustomobject]@{ Source='D:\OpenEB_Dev\openeb\test_dummy.raw'; Target='tests\fixtures\test_dummy.invalid.raw'; Class='custom-fixture'; Trust='not-openeb-raw' },
    [pscustomobject]@{ Source='D:\Desktop\OpenEB 开发环境与相机连接.docx'; Target='docs\notes\OpenEB 开发环境与相机连接.docx'; Class='historical-note'; Trust='ai-generated-unverified' },
    [pscustomobject]@{ Source='D:\Desktop\Metavision SDK 环境搭建成功.docx'; Target='docs\notes\Metavision SDK 环境搭建成功.docx'; Class='historical-note'; Trust='ai-generated-unverified' },
    [pscustomobject]@{ Source='D:\Desktop\步骤.docx'; Target='docs\notes\步骤.docx'; Class='historical-note'; Trust='ai-generated-unverified' },
    [pscustomobject]@{ Source='D:\Desktop\运行事件相机测试代码.docx'; Target='docs\notes\运行事件相机测试代码.docx'; Class='historical-note'; Trust='ai-generated-unverified' },
    [pscustomobject]@{ Source='D:\Desktop\相机未找到，但SDK通了.docx'; Target='docs\notes\相机未找到，但SDK通了.docx'; Class='historical-note'; Trust='ai-generated-unverified' },
    [pscustomobject]@{ Source='D:\Desktop\2.docx'; Target='docs\notes\2.docx'; Class='historical-note'; Trust='ai-generated-unverified' },
    [pscustomobject]@{ Source='D:\Desktop\基于事件相机的人体姿态估计预训练基础模型研究.txt'; Target='docs\research\基于事件相机的人体姿态估计预训练基础模型研究.txt'; Class='research'; Trust='reference' },
    [pscustomobject]@{ Source='D:\Desktop\2026416创新.pdf'; Target='docs\research\2026416创新.pdf'; Class='research'; Trust='project-proposal' },
    [pscustomobject]@{ Source='D:\Desktop\姿态估计项目\流程图.png'; Target='docs\research\流程图.png'; Class='research'; Trust='project-flowchart' }
)
if (($copyMap.Target | Group-Object | Where-Object Count -gt 1)) { throw 'The flat copy map contains a target collision.' }
$missing = $copyMap | Where-Object { -not (Test-Path -LiteralPath $_.Source -PathType Leaf) }
if ($missing) { $missing | Format-Table; throw 'One or more required copy sources are missing.' }
$copyMap | Export-Csv -LiteralPath (Join-Path $migrationTemp 'copy-map.tsv') -Delimiter "`t" -NoTypeInformation -Encoding utf8
Write-Output "COPY_MAP_READY=$($copyMap.Count)"
```

Expected: `COPY_MAP_READY=16`.

- [ ] **Step 2: Copy each mapped file without overwriting an existing target**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$copyMap = Import-Csv -LiteralPath (Join-Path $migrationTemp 'copy-map.tsv') -Delimiter "`t"
foreach ($entry in $copyMap) {
    $destination = Join-Path $targetRoot $entry.Target
    if (Test-Path -LiteralPath $destination) { throw "Refusing to overwrite $destination" }
    Copy-Item -LiteralPath $entry.Source -Destination $destination
}
Write-Output "COPIED=$($copyMap.Count)"
```

Expected: `COPIED=16`.

- [ ] **Step 3: Hash both sides, fail on any mismatch, and generate the flat inventory**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$copyMap = Import-Csv -LiteralPath (Join-Path $migrationTemp 'copy-map.tsv') -Delimiter "`t"
$inventory = foreach ($entry in $copyMap) {
    $sourceItem = Get-Item -LiteralPath $entry.Source
    $destination = Join-Path $targetRoot $entry.Target
    $sourceHash = (Get-FileHash -LiteralPath $entry.Source -Algorithm SHA256).Hash.ToLowerInvariant()
    $targetHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($sourceHash -ne $targetHash) { throw "Hash mismatch: $($entry.Source) -> $destination" }
    [pscustomobject]@{
        SourcePath = $entry.Source
        TargetPath = $destination
        Class = $entry.Class
        Trust = $entry.Trust
        Action = 'copied-source-preserved'
        Bytes = $sourceItem.Length
        SourceModified = $sourceItem.LastWriteTime.ToString('yyyy-MM-ddTHH:mm:sszzz')
        SHA256 = $sourceHash
    }
}

$installer = Get-Item -LiteralPath 'D:\Code\event_camera\Miniconda3-latest-Linux-x86_64.sh'
$inventory += [pscustomobject]@{
    SourcePath = $installer.FullName
    TargetPath = ''
    Class = 'installer'
    Trust = 'external-download'
    Action = 'inventory-only-not-copied'
    Bytes = $installer.Length
    SourceModified = $installer.LastWriteTime.ToString('yyyy-MM-ddTHH:mm:sszzz')
    SHA256 = (Get-FileHash -LiteralPath $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}

$inventory | Export-Csv -LiteralPath (Join-Path $targetRoot 'docs\inventory\assets.tsv') -Delimiter "`t" -NoTypeInformation -Encoding utf8
Import-Csv -LiteralPath (Join-Path $targetRoot 'docs\inventory\assets.tsv') -Delimiter "`t" | Format-Table Class,Action,Bytes,SourcePath,TargetPath -AutoSize
```

Expected: 17 inventory rows: 16 verified copies and one inventory-only Miniconda installer. The installer hash is `42cfece170da342364a78d629e06b94dfd81b0f2717d7655729100d888d606b4` and it is not present under `D:\EventPoseFinal`.

- [ ] **Step 4: Write the inventory guide**

Use `apply_patch` to create `D:\EventPoseFinal\docs\inventory\README.md`:

```markdown
# Asset inventory

`assets.tsv` is the flat provenance record for files extracted during the first organization pass. `copied-source-preserved` means the target was copied and SHA-256 matched while the original remained untouched; `inventory-only-not-copied` means the large installer remains only at its old path.

Trust labels are important:

- `prototype-dummy-labels`: the DHP19 loader returns zero-filled 3D pose labels and is not trainable ground truth.
- `invalid-openeb-format-demo` and `not-openeb-raw`: the custom byte format is not a valid OpenEB RAW stream.
- `fabricated-output-demo`: the script prints predefined benchmark numbers and is not evidence of measured filtering performance.
- `ai-generated-unverified`: historical setup notes may be useful context, but only `docs/setup` is treated as verified guidance.

Renaming a target does not change its bytes. Original and target paths plus SHA-256 make every extracted file traceable without recreating old source folder trees.
```

- [ ] **Step 5: Write the notes and research indexes**

Use `apply_patch` to create `D:\EventPoseFinal\docs\notes\README.md`:

```markdown
# Historical notes

These DOCX files were copied unchanged from `D:\Desktop`. They document earlier AI-assisted attempts and observations, but they are not authoritative installation instructions. Use `docs/setup/windows-openeb.md` and `docs/setup/wsl.md` for the verified current state.
```

Use `apply_patch` to create `D:\EventPoseFinal\docs\research\README.md`:

```markdown
# Research material

This flat folder keeps the supplied project proposal (`2026416创新.pdf`), research note, and pose-estimation flowchart together. They were copied unchanged; provenance and hashes are recorded in `docs/inventory/assets.tsv`.
```

- [ ] **Step 6: Verify no source was modified during extraction**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$inventory = Import-Csv -LiteralPath (Join-Path $targetRoot 'docs\inventory\assets.tsv') -Delimiter "`t"
$sourceMutation = foreach ($row in $inventory | Where-Object Action -eq 'copied-source-preserved') {
    $currentHash = (Get-FileHash -LiteralPath $row.SourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($currentHash -ne $row.SHA256) { $row.SourcePath }
}
if ($sourceMutation) { $sourceMutation; throw 'A source file changed during extraction.' }
Write-Output 'COPIED_FILES_HASH_VERIFIED=16'
```

Expected: `COPIED_FILES_HASH_VERIFIED=16`.

### Task 5: Configure Local Paths and Convenience Junctions

**Files:**
- Create ignored: `D:\EventPoseFinal\configs\paths.local.toml`
- Create ignored junctions under `D:\EventPoseFinal\data` and `D:\EventPoseFinal\third_party`

- [ ] **Step 1: Create the ignored local path file from the verified template**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
Copy-Item -LiteralPath (Join-Path $targetRoot 'configs\paths.example.toml') -Destination (Join-Path $targetRoot 'configs\paths.local.toml')
git -C $targetRoot check-ignore -q configs/paths.local.toml
if ($LASTEXITCODE -ne 0) { throw 'Local path configuration is not ignored.' }
```

Expected: `configs/paths.local.toml` exists and `git check-ignore` succeeds.

- [ ] **Step 2: Validate every intended junction target before creating links**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$junctionMap = @(
    [pscustomobject]@{ Link='data\DHP19'; Target='D:\DHP19' },
    [pscustomobject]@{ Link='data\DHP19_preprocessed'; Target='D:\DHP19_preprocessed' },
    [pscustomobject]@{ Link='third_party\openeb'; Target='D:\OpenEB_Dev\openeb' },
    [pscustomobject]@{ Link='third_party\mmpose'; Target='D:\MMPose\mmpose' },
    [pscustomobject]@{ Link='third_party\v2e_exps_public'; Target='D:\Event_Project\v2e_exps_public' },
    [pscustomobject]@{ Link='third_party\rpg_vid2e'; Target='D:\RPG_vid2e\rpg_vid2e' }
)
foreach ($entry in $junctionMap) {
    if (-not (Test-Path -LiteralPath $entry.Target -PathType Container)) { throw "Missing junction target: $($entry.Target)" }
    $linkPath = Join-Path $targetRoot $entry.Link
    if (Test-Path -LiteralPath $linkPath) { throw "Refusing to replace existing link path: $linkPath" }
}
$junctionMap | Export-Csv -LiteralPath (Join-Path $migrationTemp 'junction-map.tsv') -Delimiter "`t" -NoTypeInformation -Encoding utf8
$junctionMap | Format-Table -AutoSize
```

Expected: six rows and no missing target error.

- [ ] **Step 3: Create the six Windows junctions**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$junctionMap = Import-Csv -LiteralPath (Join-Path $migrationTemp 'junction-map.tsv') -Delimiter "`t"
foreach ($entry in $junctionMap) {
    New-Item -ItemType Junction -Path (Join-Path $targetRoot $entry.Link) -Target $entry.Target | Out-Null
}
Get-Item -LiteralPath ($junctionMap | ForEach-Object { Join-Path $targetRoot $_.Link }) | Select-Object FullName,LinkType,Target
```

Expected: every row has `LinkType` equal to `Junction` and the intended external target.

- [ ] **Step 4: Confirm links resolve and remain outside Git**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$junctionMap = Import-Csv -LiteralPath (Join-Path $migrationTemp 'junction-map.tsv') -Delimiter "`t"
foreach ($entry in $junctionMap) {
    $linkPath = Join-Path $targetRoot $entry.Link
    if (-not (Test-Path -LiteralPath $linkPath -PathType Container)) { throw "Unresolved junction: $linkPath" }
    git -C $targetRoot check-ignore -q ($entry.Link -replace '\\','/')
    if ($LASTEXITCODE -ne 0) { throw "Junction is not ignored: $($entry.Link)" }
}
git -C $targetRoot status --short
```

Expected: no junction target contents appear in Git status.

### Task 6: Add a Deterministic Windows OpenEB Boundary

**Files:**
- Create: `D:\EventPoseFinal\environment\windows\Set-OpenEBEnvironment.ps1`
- Create: `D:\EventPoseFinal\environment\windows\Open-EventPoseShell.ps1`
- Create: `D:\EventPoseFinal\environment\windows\Test-OpenEB.ps1`

- [ ] **Step 1: Write the process-local OpenEB environment initializer**

Use `apply_patch` to create `D:\EventPoseFinal\environment\windows\Set-OpenEBEnvironment.ps1`:

```powershell
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
```

- [ ] **Step 2: Write the prepared-shell entry point**

Use `apply_patch` to create `D:\EventPoseFinal\environment\windows\Open-EventPoseShell.ps1`:

```powershell
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Set-OpenEBEnvironment.ps1')

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Write-Host 'OpenEB 5.2.0 environment loaded for this child shell.'
Write-Host "Project: $projectRoot"
Write-Host "MV_HAL_PLUGIN_PATH: $env:MV_HAL_PLUGIN_PATH"
Write-Host 'Keep OpenEB/Stream and h5py training work in separate Python processes.'

& powershell.exe -NoLogo -NoExit -Command "Set-Location -LiteralPath '$projectRoot'"
if ($LASTEXITCODE -ne 0) { throw "Child PowerShell exited with code $LASTEXITCODE" }
```

- [ ] **Step 3: Write the no-camera-safe diagnostic with a valid EVT2 round trip**

Use `apply_patch` to create `D:\EventPoseFinal\environment\windows\Test-OpenEB.ps1`:

```powershell
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
```

- [ ] **Step 4: Parse all PowerShell files before executing them**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$parseErrors = @()
Get-ChildItem -LiteralPath (Join-Path $targetRoot 'environment\windows') -Filter '*.ps1' | ForEach-Object {
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors) { $parseErrors += $errors }
}
if ($parseErrors) { $parseErrors; throw 'PowerShell parse errors found.' }
Write-Output 'POWERSHELL_PARSE=OK'
```

Expected: `POWERSHELL_PARSE=OK`.

- [ ] **Step 5: Run the Windows diagnostic without a camera**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
& (Join-Path $targetRoot 'environment\windows\Test-OpenEB.ps1')
```

Expected:

```text
OpenEB version: 5.2.0
HAL plugin: found
EVT2 round-trip: 10 events
Python Stream import: OK (3.11.6)
Camera: not connected (expected until hardware is available)
```

If a camera is connected later, the last line may instead contain its HAL identity. The diagnostic must still exit successfully.

### Task 7: Add and Verify the WSL Environment Inventory

**Files:**
- Create: `D:\EventPoseFinal\environment\wsl\check_environment.sh`

- [ ] **Step 1: Write the WSL check script**

Use `apply_patch` to create `D:\EventPoseFinal\environment\wsl\check_environment.sh` with LF endings:

```bash
#!/usr/bin/env bash
set -uo pipefail

project_root="/mnt/d/EventPoseFinal"
raw_root="/mnt/d/DHP19"
preprocessed_root="/mnt/d/DHP19_preprocessed"
python_bin="${1:-/home/mestia/miniconda3/bin/python}"

for required_path in "$project_root" "$raw_root" "$preprocessed_root"; do
    if [[ -e "$required_path" ]]; then
        printf 'path=ok %s\n' "$required_path"
    else
        printf 'path=missing %s\n' "$required_path"
    fi
done

if [[ ! -x "$python_bin" ]]; then
    printf 'python=missing %s\n' "$python_bin"
    exit 2
fi

"$python_bin" - <<'PY'
import importlib
import sys

print(f"python={sys.version.split()[0]}")
missing_core = []
for module in ("numpy", "torch"):
    try:
        imported = importlib.import_module(module)
        print(f"package=ok {module} {getattr(imported, '__version__', 'unknown')}")
    except Exception as exc:
        missing_core.append(module)
        print(f"package=missing {module} {exc}")

for module in ("cv2", "mmengine", "mmpose"):
    try:
        imported = importlib.import_module(module)
        print(f"optional=ok {module} {getattr(imported, '__version__', 'unknown')}")
    except Exception:
        print(f"optional=missing {module}")

try:
    import torch
    print(f"cuda_available={torch.cuda.is_available()}")
    print(f"cuda_build={torch.version.cuda}")
except Exception:
    pass

if missing_core:
    raise SystemExit(2)
PY
```

- [ ] **Step 2: Validate Bash syntax**

Run:

```powershell
wsl.exe -d Ubuntu -- bash -n /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh
if ($LASTEXITCODE -ne 0) { throw 'WSL environment script has invalid Bash syntax.' }
Write-Output 'BASH_PARSE=OK'
```

Expected: `BASH_PARSE=OK`.

- [ ] **Step 3: Run the inventory in WSL without installing or changing anything**

Run:

```powershell
wsl.exe -d Ubuntu -- bash /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh
if ($LASTEXITCODE -ne 0) { throw 'WSL is missing a core path or core package; keep the detailed output for review.' }
```

Expected on the currently observed base environment:

```text
path=ok /mnt/d/EventPoseFinal
path=ok /mnt/d/DHP19
path=ok /mnt/d/DHP19_preprocessed
python=3.14.6
package=ok numpy 2.4.4
package=ok torch 2.11.0+cu128
optional=missing cv2
optional=missing mmengine
optional=missing mmpose
```

`cuda_available` and `cuda_build` are reported from the live machine and are not hard-coded acceptance values. Optional packages remain deferred; this task performs no installation.

### Task 8: Write Verified Setup Guidance and the Project Entry README

**Files:**
- Create: `D:\EventPoseFinal\docs\setup\windows-openeb.md`
- Create: `D:\EventPoseFinal\docs\setup\wsl.md`
- Modify: `D:\EventPoseFinal\README.md`

- [ ] **Step 1: Write the verified Windows/OpenEB guide**

Use `apply_patch` to create `D:\EventPoseFinal\docs\setup\windows-openeb.md`:

```markdown
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
```

- [ ] **Step 2: Write the verified WSL guide**

Use `apply_patch` to create `D:\EventPoseFinal\docs\setup\wsl.md`:

```markdown
# WSL data and training environment

WSL is the intended home for DHP19 parsing, voxel validation, PyTorch training, evaluation, and visualization. The shared project is `/mnt/d/EventPoseFinal`; datasets remain at `/mnt/d/DHP19` and `/mnt/d/DHP19_preprocessed`.

Run the read-only environment inventory:

```bash
bash /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh
```

The currently observed `/home/mestia/miniconda3` base has Python 3.14.6, NumPy 2.4.4, and PyTorch 2.11.0+cu128. OpenCV, MMEngine, and MMPose were not found in that base during organization. Installing a stable project-specific GPU environment is intentionally deferred until CUDA compatibility and the selected pose framework are reviewed.

Do not treat `/home/mestia/openeb` as the authoritative SDK checkout. Windows `D:\OpenEB_Dev\openeb` remains the verified OpenEB 5.2.0 installation.
```

- [ ] **Step 3: Replace the one-line README with the verified project status**

Use `apply_patch` to replace `D:\EventPoseFinal\README.md` with:

```markdown
# EventPoseFinal

Event-camera human-pose research workspace, organized on 2026-07-29 from the earlier `EventCamera` repository and scattered prototype files.

## Current stage

- DHP19 raw data and 659 preprocessed NPY samples exist outside Git.
- Prototype AEDAT parsing, voxel generation, and visualization scripts have been recovered and hash-inventoried.
- The recovered DHP19 dataset currently returns zero-filled placeholder pose labels; real label alignment, training, and evaluation are not implemented yet.
- Windows OpenEB 5.2.0 can load its production HAL plugin and round-trip a valid EVT2 file. No physical event camera has been tested.
- WSL has a usable PyTorch base, but the final isolated GPU training environment and pose framework are still pending.

## Start here

Windows OpenEB diagnostic:

```powershell
& D:\EventPoseFinal\environment\windows\Test-OpenEB.ps1
```

WSL environment inventory:

```bash
bash /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh
```

Local paths are documented in `configs/paths.example.toml` and overridden by ignored `configs/paths.local.toml`. Source provenance and reliability labels are in `docs/inventory/assets.tsv`; verified setup notes are in `docs/setup`.

## Environment boundary

Use Windows only for OpenEB, future camera recording, and RAW conversion. Use WSL for DHP19 processing, PyTorch, training, and evaluation. Do not import Windows OpenEB Stream and h5py in the same Python process because their HDF5 DLL versions conflict.

## Preservation policy

The first organization pass copies and verifies files but does not delete old projects, move datasets, rebuild environments, copy third-party histories into Git, or push to GitHub.
```

- [ ] **Step 4: Compile-check recovered Python syntax without importing dependencies**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$pythonFiles = @(
    'scripts\data\dhp19_dataset.py',
    'scripts\data\event_to_voxel.py',
    'scripts\data\view_npy.py',
    'scripts\diagnostics\test_camera.py',
    'scripts\diagnostics\generate_invalid_raw.py',
    'scripts\diagnostics\filter_benchmark_demo.py'
) | ForEach-Object { Join-Path $targetRoot $_ }
& 'D:\OpenEB_Dev\openeb\py3venv\Scripts\python.exe' -m py_compile @pythonFiles
if ($LASTEXITCODE -ne 0) { throw 'A recovered Python file does not compile.' }
Write-Output 'PYTHON_COMPILE=OK'
```

Expected: `PYTHON_COMPILE=OK`. Do not run `filter_benchmark_demo.py`; its numbers are predefined, not measured.

- [ ] **Step 5: Parse both TOML files with Python 3.11**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
& 'D:\OpenEB_Dev\openeb\py3venv\Scripts\python.exe' -c "import pathlib,tomllib; root=pathlib.Path(r'D:\EventPoseFinal'); [tomllib.loads((root/p).read_text(encoding='utf-8')) for p in ('configs/paths.example.toml','configs/paths.local.toml')]; print('TOML_PARSE=OK')"
if ($LASTEXITCODE -ne 0) { throw 'TOML path configuration is invalid.' }
```

Expected: `TOML_PARSE=OK`.

### Task 9: Run Acceptance Checks and Clean Only Reproducible Temporary Files

**Files:**
- Verify all files under `D:\EventPoseFinal`
- Delete only after successful verification: `%TEMP%\EventPoseFinal-migration-20260729`
- Delete only after successful verification: `C:\Users\yanyuMestia\.codex\visualizations\2026\07\29\019fadb2-8d5c-77b3-879d-211af57fca94\openeb_check`

- [ ] **Step 1: Recheck Git identity and preservation of the user's staged blobs**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
if ((git -C $targetRoot remote get-url origin) -ne 'https://github.com/YanYu-Mestia/EventCamera.git') { throw 'Unexpected Git remote.' }
git -C $targetRoot merge-base --is-ancestor 49f505cf269dfdfcec36dc64dc58ecc9632f8d52 HEAD
if ($LASTEXITCODE -ne 0) { throw 'Original GitHub baseline is no longer an ancestor.' }
if ((git -C $targetRoot rev-parse :README.md) -ne 'd00ba81a02d5a6c46375f5a657823e26fd98345d') { throw 'Staged README blob changed.' }
if ((git -C $targetRoot rev-parse :.gitignore) -ne '29efeee484fedfdeb0f1712bf076cbfd11099e9a') { throw 'Staged .gitignore blob changed.' }
Write-Output 'GIT_SOURCE_AND_STAGED_STATE=PRESERVED'
```

Expected: `GIT_SOURCE_AND_STAGED_STATE=PRESERVED`. The target working-tree README and `.gitignore` now differ from their copied staged versions, but the user's index entries remain untouched.

- [ ] **Step 2: Re-verify the 16 copied files from the inventory**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$assetInventory = Import-Csv -LiteralPath (Join-Path $targetRoot 'docs\inventory\assets.tsv') -Delimiter "`t"
$copyRows = @($assetInventory | Where-Object Action -eq 'copied-source-preserved')
if ($copyRows.Count -ne 16) { throw "Expected 16 copied rows, got $($copyRows.Count)" }
foreach ($row in $copyRows) {
    foreach ($path in @($row.SourcePath, $row.TargetPath)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing inventoried file: $path" }
        $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -ne $row.SHA256) { throw "Inventory hash mismatch: $path" }
    }
}
Write-Output 'INVENTORY_HASHES=16/16'
```

Expected: `INVENTORY_HASHES=16/16`.

- [ ] **Step 3: Verify external paths, junctions, and WSL paths without traversing large trees**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$junctionMap = Import-Csv -LiteralPath (Join-Path $migrationTemp 'junction-map.tsv') -Delimiter "`t"
foreach ($entry in $junctionMap) {
    $item = Get-Item -LiteralPath (Join-Path $targetRoot $entry.Link)
    if ($item.LinkType -ne 'Junction') { throw "Not a junction: $($entry.Link)" }
    if (-not (Test-Path -LiteralPath $entry.Target -PathType Container)) { throw "Missing target: $($entry.Target)" }
}
wsl.exe -d Ubuntu -- bash -lc 'for p in /mnt/d/EventPoseFinal /mnt/d/DHP19 /mnt/d/DHP19_preprocessed; do test -d "$p" || exit 2; done'
if ($LASTEXITCODE -ne 0) { throw 'One or more required WSL paths do not resolve.' }
Write-Output 'EXTERNAL_PATHS=OK'
```

Expected: `EXTERNAL_PATHS=OK`.

- [ ] **Step 4: Freshly rerun Windows and WSL diagnostics**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
& (Join-Path $targetRoot 'environment\windows\Test-OpenEB.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Windows OpenEB diagnostic failed.' }
wsl.exe -d Ubuntu -- bash /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh
if ($LASTEXITCODE -ne 0) { throw 'WSL core environment check failed.' }
```

Expected: OpenEB 5.2.0, 10-event EVT2 round trip, successful Stream import, explicit camera status, all three WSL paths present, and NumPy/PyTorch importable. Missing optional WSL packages are reported, not hidden.

- [ ] **Step 5: Audit Git status for forbidden content and accidental large files**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
$status = git -C $targetRoot status --short --untracked-files=all
$status
$forbidden = $status | Where-Object { $_ -match '(^|[ /])(DHP19|mmpose|openeb|rpg_vid2e|v2e_exps_public)([ /]|$)' -or $_ -match '\.(npy|aedat4?|h5|hdf5|pth|pt|ckpt|onnx)$' }
if ($forbidden) { $forbidden; throw 'Forbidden dataset, third-party, environment, or model content appears in Git status.' }

$gitDirectoryPrefix = (Join-Path $targetRoot '.git') + [System.IO.Path]::DirectorySeparatorChar
$unexpectedLarge = Get-ChildItem -LiteralPath $targetRoot -Recurse -File -Force -Attributes !ReparsePoint |
    Where-Object {
        -not $_.FullName.StartsWith($gitDirectoryPrefix, [System.StringComparison]::OrdinalIgnoreCase) -and
        $_.Length -gt 50MB -and
        $_.FullName -ne (Join-Path $targetRoot 'tests\fixtures\test_dummy.invalid.raw')
    }
if ($unexpectedLarge) { $unexpectedLarge | Select-Object FullName,Length; throw 'Unexpected file larger than 50 MB was copied into the project.' }
Write-Output 'GIT_BOUNDARY_AND_SIZE_AUDIT=OK'
```

Expected: organizational files appear as modified/untracked for review, junction contents do not appear, and `GIT_BOUNDARY_AND_SIZE_AUDIT=OK` prints. Nothing is staged by this task.

- [ ] **Step 6: Confirm the old source repository still has its original state**

Run:

```powershell
$sourceRoot = 'D:\Code\EventCamera'
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$expected = @{}
Get-Content -LiteralPath (Join-Path $migrationTemp 'repository.txt') |
    Where-Object { $_ -match '^[a-z_]+=' } |
    ForEach-Object { $key, $value = $_ -split '=', 2; $expected[$key] = $value }
if ((git -C $sourceRoot rev-parse HEAD) -ne $expected.head) { throw 'Source repository HEAD changed.' }
if ((git -C $sourceRoot rev-parse :README.md) -ne $expected.readme_index) { throw 'Source staged README changed.' }
if ((git -C $sourceRoot rev-parse :.gitignore) -ne $expected.gitignore_index) { throw 'Source staged .gitignore changed.' }
git -C $sourceRoot status --short --branch
Write-Output 'OLD_SOURCE_REPOSITORY=UNCHANGED'
```

Expected: `OLD_SOURCE_REPOSITORY=UNCHANGED` and the same source status recorded at preflight.

- [ ] **Step 7: Remove only the two known reproducible diagnostic directories**

Run:

```powershell
$migrationTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'EventPoseFinal-migration-20260729'
$cleanupTargets = @(
    $migrationTemp,
    'C:\Users\yanyuMestia\.codex\visualizations\2026\07\29\019fadb2-8d5c-77b3-879d-211af57fca94\openeb_check'
)
$allowedParents = @(
    [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()),
    [System.IO.Path]::GetFullPath('C:\Users\yanyuMestia\.codex\visualizations\2026\07\29\019fadb2-8d5c-77b3-879d-211af57fca94')
)
foreach ($cleanupTarget in $cleanupTargets) {
    if (-not (Test-Path -LiteralPath $cleanupTarget)) { continue }
    $resolved = [System.IO.Path]::GetFullPath($cleanupTarget)
    $allowed = $allowedParents | Where-Object { $resolved.StartsWith($_, [System.StringComparison]::OrdinalIgnoreCase) }
    if (-not $allowed) { throw "Refusing cleanup outside approved temporary parents: $resolved" }
    if ((Split-Path -Leaf $resolved) -notin @('EventPoseFinal-migration-20260729', 'openeb_check')) {
        throw "Refusing cleanup of unexpected directory name: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
    Write-Output "CLEANED=$resolved"
}
```

Expected: only the audit snapshot and earlier `openeb_check` fixture directory are removed. These files are reproducible. No path under `D:\Code`, `D:\DHP19`, `D:\Event_Project`, `D:\MMPose`, `D:\OpenEB_Dev`, `D:\RPG_vid2e`, or either vcpkg root is deleted.

- [ ] **Step 8: Present the uncommitted organization result for review**

Run:

```powershell
$targetRoot = 'D:\EventPoseFinal'
git -C $targetRoot status --short --branch
git -C $targetRoot diff --stat
git -C $targetRoot diff --cached --stat
Write-Output 'NO_PUSH_PERFORMED=True'
Write-Output 'MIGRATED_CODE_AND_DOCUMENTS_UNCOMMITTED_FOR_REVIEW=True'
```

Expected: the branch/remote/history are intact; the original staged blobs are still represented in the index; organization changes and recovered assets are visible for review; no datasets, third-party trees, environments, or generated experiments are listed; nothing has been pushed.

## Deferred Until a Separate Review

- Commit or push recovered project code and copied documents.
- Delete, move, or archive any old project folder, installer, dataset, environment, vcpkg tree, or experiment output.
- Refactor the recovered scripts or replace hard-coded paths.
- Correct DHP19 parsing, connect genuine pose labels, validate voxel outliers, or define train/validation splits.
- Rebuild OpenEB, resolve its HDF5 environment conflict, or test a physical camera.
- Create a stable isolated WSL GPU environment and install OpenCV, MMEngine, MMPose, ViTPose, or DINOv2.
- Implement models, training, evaluation, or experiment directories before those components exist.

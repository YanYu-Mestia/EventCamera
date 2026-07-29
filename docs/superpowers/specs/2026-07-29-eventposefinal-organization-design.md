# EventPoseFinal Project Organization Design

## 1. Objective

Create `D:\EventPoseFinal` as the single working entry point for the event-camera human-pose project while preserving every existing source, dataset, environment, Git change, and third-party checkout.

The first organization pass is non-destructive: copy and verify small project-owned files, keep large or path-sensitive assets in place, and expose them through local configuration and convenience links. It does not delete old files, rebuild OpenEB, push to GitHub, or move datasets.

## 2. Confirmed Decisions

- The Git repository at `D:\Code\EventCamera` becomes the source of the new root and retains its `.git` directory, branch, remote, commit history, and current staged changes.
- The new root is `D:\EventPoseFinal`.
- Windows is the OpenEB and future camera/RAW-ingestion environment.
- WSL Ubuntu is the PyTorch data-processing, training, and evaluation environment.
- Existing virtual environments, OpenEB build outputs, and vcpkg build products remain in place.
- DHP19 and other large datasets remain in place.
- The first pass copies files and verifies them; it does not remove or overwrite source files.

## 3. Asset Classification

### Project-owned code

The following files are copied byte-for-byte into a provenance-preserving legacy area before any refactoring:

- `D:\Code\event_camera\dhp19_dataset.py`
- `D:\OpenEB_Dev\openeb\event_to_voxel.py`
- `D:\OpenEB_Dev\openeb\generate_raw.py`
- `D:\OpenEB_Dev\openeb\test_camera.py`
- `D:\OpenEB_Dev\openeb\test_filter.py`
- `D:\OpenEB_Dev\openeb\view_npy.py`
- `D:\OpenEB_Dev\openeb\test_dummy.raw`

The two similarly named folders remain distinct:

- `D:\Code\EventCamera`: the Git repository.
- `D:\Code\event_camera`: loose project code and a downloaded Linux installer.

The Miniconda installer in `D:\Code\event_camera` is recorded in the inventory but is not copied into Git.

### Research and project documents

The supplied DOCX notes are copied into `docs\archive\ai_notes`. The project PDF, flowchart, project images, and research TXT are copied into `docs\research` where available. Original filenames are retained, and an index explains the origin and reliability of each item.

The AI-generated setup notes are historical records, not authoritative instructions. Verified setup guides are written separately under `docs\setup`.

### Large data

- `D:\DHP19`: raw DHP19 events, kept in place.
- `D:\DHP19_preprocessed`: generated voxel samples, kept in place.

They are referenced by an ignored local-path configuration. Windows convenience links may be created under `data`, but WSL scripts use explicit `/mnt/d/...` paths so they do not depend on Windows junction behavior.

### Third-party repositories and SDK sources

- `D:\OpenEB_Dev\openeb`
- `D:\MMPose\mmpose`
- `D:\Event_Project\v2e_exps_public`
- `D:\RPG_vid2e\rpg_vid2e`

These remain independent Git repositories and are never copied into the main repository history. Local convenience links live under ignored `third_party` entries.

### Existing environments and build products

- Windows OpenEB Python: `D:\OpenEB_Dev\openeb\py3venv`
- Windows OpenEB build: `D:\OpenEB_Dev\openeb\build`
- OpenEB dependency tree actually used by CMake: `D:\OpenEB_Dev\vcpkg-2024.11.16`
- WSL Conda base: `/home/mestia/miniconda3`

The separate `D:\vcpkg-2024.11.16` tree is recorded as an unused or unconfirmed duplicate. Neither vcpkg tree is deleted during this work.

## 4. Target Layout

```text
D:\EventPoseFinal
|-- .git\
|-- .gitignore
|-- README.md
|-- src\
|   `-- eventpose\
|       |-- data\
|       |-- preprocessing\
|       |-- models\
|       `-- evaluation\
|-- scripts\
|   |-- data\
|   |-- diagnostics\
|   |-- train\
|   |-- evaluate\
|   |-- windows\
|   `-- wsl\
|-- configs\
|   |-- paths.example.toml
|   `-- paths.local.toml       # ignored
|-- tests\
|-- docs\
|   |-- setup\
|   |-- research\
|   |-- archive\ai_notes\
|   |-- inventory\
|   `-- superpowers\specs\
|-- archive\
|   `-- legacy_code\source_key\
|-- experiments\
|   |-- logs\
|   |-- checkpoints\
|   `-- results\
|-- data\                     # local links/content ignored
|-- third_party\              # local links/content ignored
`-- environment\
    |-- windows\
    `-- wsl\
```

Empty runtime directories are represented with small README or `.gitkeep` files only where useful. Large outputs, local paths, caches, weights, datasets, and links are excluded from Git.

## 5. Windows and WSL Boundary

### Windows responsibility

Windows runs the existing OpenEB 5.2.0 build for:

- future camera discovery and recording;
- EVT RAW/DAT/HDF5 inspection;
- conversion from sensor formats to portable intermediate files;
- SDK diagnostics.

The existing OpenEB tree is not treated as the main project repository. Project-owned wrappers and launch scripts live in `EventPoseFinal`, and invoke the OpenEB installation by configured path.

### WSL responsibility

WSL runs:

- DHP19 parsing and label alignment;
- voxel generation and validation;
- PyTorch datasets, training, evaluation, and visualization;
- model checkpoints and experiment logs.

WSL accesses the shared repository as `/mnt/d/EventPoseFinal` and large datasets through `/mnt/d/DHP19` and `/mnt/d/DHP19_preprocessed`.

## 6. OpenEB Status and Guardrails

The Windows OpenEB build is usable but the current combined Python environment is not clean.

Verified working behavior:

- OpenEB reports version 5.2.0.
- C++ applications and plugins are present.
- An official EVT2 test file can be encoded and read back correctly by OpenEB command-line tools.
- Python can load the Metavision bindings and open a valid RAW file when DLL and plugin paths are configured correctly.

Known constraints:

- `MV_HAL_PLUGIN_PATH` must point to `D:\OpenEB_Dev\openeb\build\lib\metavision\hal\plugins`.
- `HDF5_PLUGIN_PATH` must point to `D:\OpenEB_Dev\openeb\build\lib\hdf5\plugin`.
- OpenEB was built against HDF5 1.14.2, while the current `h5py 3.16.0` package uses HDF5 2.0.0. Loading both in one Python process can cause DLL failures.
- The system path contains several Python, Anaconda, and native-library installations.
- `test_dummy.raw` is a custom byte stream, not a valid OpenEB RAW test fixture.

Therefore the first pass adds a deterministic Windows launcher and a diagnostic script, but does not rebuild or mutate the existing SDK environment. Windows ingestion should emit a portable intermediate format for WSL training rather than mixing OpenEB, `h5py`, and the training stack in one process.

## 7. Migration Procedure

1. Record a manifest of every in-scope source path, file size, modification time, Git state, and relevant environment version.
2. Copy `D:\Code\EventCamera` to a new, absent `D:\EventPoseFinal` path, including hidden `.git` data.
3. Verify branch, HEAD, remote, Git status, and the hashes of tracked working-tree files against the source repository.
4. Create the approved directory skeleton without overwriting existing repository files.
5. Copy legacy project-owned code into source-specific archive folders and verify SHA-256 hashes.
6. Copy research documents and notes, retaining original filenames and recording SHA-256 hashes.
7. Add ignored local path configuration and convenience links for datasets and third-party trees.
8. Export environment inventories and add verified Windows/WSL setup guides and diagnostics.
9. Promote only understood code into canonical `src` or `scripts` locations. Preserve the original archived copies.
10. Run acceptance checks and present the result before any cleanup, GitHub push, or deletion decision.

If `D:\EventPoseFinal` already exists at implementation time, migration stops for inspection rather than merging or overwriting it.

## 8. Git Safety

- Preserve the source repository's current staged `README.md` and `.gitignore` changes exactly.
- Do not stage unrelated user changes when committing migration documentation or scaffolding.
- Do not push to GitHub during organization.
- Ignore datasets, third-party links, environments, installers, build output, model weights, logs, caches, and local path configuration.
- Keep source provenance in the inventory so archived files can be traced back to their old locations.

## 9. Verification and Acceptance Criteria

The organization pass is accepted only when all of the following are freshly verified:

- `D:\EventPoseFinal` is a valid Git worktree with remote `https://github.com/YanYu-Mestia/EventCamera.git` and HEAD `49f505c` before new organization commits.
- The pre-existing staged changes are still present and content-identical.
- Every copied legacy code and document file matches its source SHA-256 hash.
- No source directory or source file was deleted or modified.
- DHP19 and third-party targets resolve from their recorded Windows and WSL paths.
- Windows diagnostics report OpenEB 5.2.0, load the production HAL plugin, and successfully inspect a valid generated EVT2 RAW fixture.
- WSL can import the chosen training environment's core packages or clearly reports the packages still needing installation.
- Git status contains no dataset, environment, build tree, link target, weight, or generated experiment output.
- The project README clearly identifies the current research stage and the one-command entry points for diagnostics and future training.

## 10. Explicitly Deferred Work

- Deleting or relocating any old directory.
- Rebuilding OpenEB or replacing its Python environment.
- Installing a final GPU-enabled WSL training environment.
- Correcting the DHP19 parser, attaching real pose labels, or fixing voxel outliers.
- Implementing ViTPose, DINOv2, training, or evaluation features.
- Committing migrated business code or pushing changes to GitHub without a separate review.

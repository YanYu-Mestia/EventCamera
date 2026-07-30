# DHP19 First-Sample Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an isolated WSL data-processing environment and convert the first 20 official constant-count frames of DHP19 `S1/session1/mov1` into verified event, pose, summary, and overlay artifacts.

**Architecture:** A focused AEDAT2 module owns decoding, synchronization, official filtering, and frame accumulation. A pose module owns MAT loading and camera projection. A small command module coordinates these units, writes official Python-facing HDF5 layouts atomically, and generates verification artifacts outside Git.

**Tech Stack:** WSL Ubuntu, Conda, Python 3.12, NumPy, SciPy, h5py, Matplotlib, Numba, pytest.

---

## File Map

| Path | Responsibility |
|---|---|
| `environment/wsl/dhp19-environment.yml` | Reproducible `eventpose-dhp19` Conda environment. |
| `environment/wsl/setup_dhp19_environment.sh` | Idempotent environment creation/update and import check. |
| `scripts/data/dhp19_aedat.py` | AEDAT2 decoding, synchronization, filters, normalization, and first-N frame accumulation. |
| `scripts/data/dhp19_pose.py` | Vicon MAT loading, frame label averaging, projection, and joint metadata. |
| `scripts/data/process_dhp19_sample.py` | CLI orchestration, atomic HDF5/JSON output, and overlay rendering. |
| `tests/data/test_dhp19_environment.py` | Environment definition contract. |
| `tests/data/test_dhp19_aedat.py` | Synthetic AEDAT, synchronization, filtering, and framing tests. |
| `tests/data/test_dhp19_pose.py` | MAT loading, label averaging, and projection tests. |
| `tests/data/test_process_dhp19_sample.py` | Atomic output and output-layout tests. |
| `docs/setup/dhp19-first-sample.md` | Exact setup, run, output, and inspection instructions. |
| `README.md` | One short link to the focused setup document; preserve all existing edits. |

Generated data goes only to `/mnt/d/DHP19_preprocessed/verification/S1_session1_mov1_20frames` and must not be staged.

### Task 1: Define and create the isolated WSL environment

**Files:**
- Create: `tests/data/test_dhp19_environment.py`
- Create: `environment/wsl/dhp19-environment.yml`
- Create: `environment/wsl/setup_dhp19_environment.sh`

- [ ] **Step 1: Write the failing environment-definition test**

```python
from pathlib import Path


def test_dhp19_environment_declares_required_runtime():
    root = Path(__file__).resolve().parents[2]
    text = (root / "environment/wsl/dhp19-environment.yml").read_text()
    assert "name: eventpose-dhp19" in text
    for requirement in (
        "python=3.12",
        "numpy=2.1",
        "scipy=1.15",
        "h5py=3.13",
        "matplotlib=3.10",
        "numba=0.61",
        "pytest=8.3",
    ):
        assert requirement in text
```

- [ ] **Step 2: Run the test and verify the expected failure**

Run:

```powershell
D:\Software\anaconda3\python.exe -m pytest tests/data/test_dhp19_environment.py -q
```

Expected: one failure because `environment/wsl/dhp19-environment.yml` does not exist.

- [ ] **Step 3: Add the environment definition**

```yaml
name: eventpose-dhp19
channels:
  - conda-forge
dependencies:
  - python=3.12
  - numpy=2.1
  - scipy=1.15
  - h5py=3.13
  - matplotlib=3.10
  - numba=0.61
  - pillow=11.1
  - pytest=8.3
```

- [ ] **Step 4: Add the idempotent setup script**

```bash
#!/usr/bin/env bash
set -euo pipefail

project_root="/mnt/d/EventPoseFinal"
conda_bin="/home/mestia/miniconda3/bin/conda"
environment_file="$project_root/environment/wsl/dhp19-environment.yml"

"$conda_bin" env update --name eventpose-dhp19 --file "$environment_file" --prune
"$conda_bin" run --name eventpose-dhp19 python - <<'PY'
import h5py
import matplotlib
import numba
import numpy
import pytest
import scipy

print("environment=ok eventpose-dhp19")
print(f"numpy={numpy.__version__}")
print(f"scipy={scipy.__version__}")
print(f"h5py={h5py.__version__}")
print(f"matplotlib={matplotlib.__version__}")
print(f"numba={numba.__version__}")
print(f"pytest={pytest.__version__}")
PY
```

- [ ] **Step 5: Run the definition test, create the environment, and verify imports**

Run:

```powershell
D:\Software\anaconda3\python.exe -m pytest tests/data/test_dhp19_environment.py -q
wsl.exe -d Ubuntu -- bash /mnt/d/EventPoseFinal/environment/wsl/setup_dhp19_environment.sh
```

Expected: the test passes and the setup script prints `environment=ok eventpose-dhp19`.

### Task 2: Implement tested AEDAT2 decoding and synchronization

**Files:**
- Create: `tests/data/test_dhp19_aedat.py`
- Create: `scripts/data/dhp19_aedat.py`

- [ ] **Step 1: Write failing tests for header handling and address decoding**

```python
from pathlib import Path
import struct

import numpy as np

from scripts.data.dhp19_aedat import decode_addresses, read_aedat2


def encode_polarity(*, x, y, camera, polarity):
    return (y << 22) | (x << 12) | (polarity << 11) | camera


def test_decode_addresses_preserves_four_camera_fields():
    addresses = np.array(
        [encode_polarity(x=12, y=34, camera=3, polarity=1)],
        dtype=np.uint32,
    )
    decoded = decode_addresses(addresses)
    assert decoded.x.tolist() == [12]
    assert decoded.y.tolist() == [34]
    assert decoded.camera.tolist() == [3]
    assert decoded.polarity.tolist() == [1]
    assert decoded.polarity_mask.tolist() == [True]


def test_read_aedat2_reads_big_endian_records_and_special_events(tmp_path: Path):
    path = tmp_path / "tiny.aedat"
    polarity = encode_polarity(x=4, y=5, camera=2, polarity=0)
    special = 0x400
    path.write_bytes(
        b"#!AER-DAT2.0\n#End of Preferences\n"
        + struct.pack(">IIII", polarity, 100, special, 200)
    )
    events = read_aedat2(path)
    assert events.timestamp.tolist() == [100]
    assert events.special_timestamp.tolist() == [200]
```

- [ ] **Step 2: Run the focused tests and verify import failure**

Run:

```bash
/home/mestia/miniconda3/bin/conda run -n eventpose-dhp19 pytest tests/data/test_dhp19_aedat.py -q
```

Expected: collection fails because `scripts.data.dhp19_aedat` does not exist.

- [ ] **Step 3: Implement the decoder API**

Create immutable `AddressFields` and `AedatEvents` dataclasses. Implement these exact masks from the official MATLAB reader:

```python
APS_OR_IMU_MASK = np.uint32(0x80000000)
IMU_OR_POLARITY_MASK = np.uint32(0x00000800)
SIGNAL_OR_SPECIAL_MASK = np.uint32(0x00000400)
Y_MASK = np.uint32(0x7FC00000)
X_MASK = np.uint32(0x003FF000)
CAMERA_MASK = np.uint32(0x0000000F)


def decode_addresses(addresses: np.ndarray) -> AddressFields:
    aps_or_imu = (addresses & APS_OR_IMU_MASK) != 0
    signal_or_special = (addresses & SIGNAL_OR_SPECIAL_MASK) != 0
    polarity_mask = (~aps_or_imu) & (~signal_or_special)
    special_mask = (~aps_or_imu) & signal_or_special
    return AddressFields(
        x=((addresses & X_MASK) >> 12).astype(np.uint16),
        y=((addresses & Y_MASK) >> 22).astype(np.uint16),
        camera=(addresses & CAMERA_MASK).astype(np.uint8),
        polarity=((addresses >> 11) & 1).astype(np.uint8),
        polarity_mask=polarity_mask,
        special_mask=special_mask,
    )
```

`read_aedat2` must find the binary offset without consuming the first record, reject a non-multiple-of-eight payload, read `>u4` address/timestamp pairs, and retain only decoded polarity and special timestamps.

- [ ] **Step 4: Add failing synchronization tests**

```python
from scripts.data.dhp19_aedat import synchronization_window


def test_three_special_events_use_first_and_last():
    start, stop = synchronization_window(
        event_timestamps=np.array([90, 250], dtype=np.uint32),
        special_timestamps=np.array([100, 101, 200], dtype=np.uint32),
        pose_samples=10,
    )
    assert (start, stop) == (100, 200)


def test_two_near_start_special_events_infer_stop_from_pose_length():
    start, stop = synchronization_window(
        event_timestamps=np.array([90, 120_000], dtype=np.uint32),
        special_timestamps=np.array([100, 101], dtype=np.uint32),
        pose_samples=10,
    )
    assert (start, stop) == (100, 100_100)
```

- [ ] **Step 5: Run red, implement the official 1/2/3/4/5-event branches, and run green**

Run the focused test before and after implementation. More than five special events must raise `ValueError`; zero special events may fall back to the first and last regular event only when both exist.

### Task 3: Implement official filtering and constant-count frames

**Files:**
- Modify: `tests/data/test_dhp19_aedat.py`
- Modify: `scripts/data/dhp19_aedat.py`

- [ ] **Step 1: Add failing tests for orientation, masks, and background support**

The tests must assert:

```python
global_x = (345 - raw_x) + camera * 346
oriented_y = 259 - raw_y
```

They must also prove that strict IR-mask boundaries are preserved and that an event is retained only when a neighboring pixel was updated no more than `70_000` microseconds earlier.

- [ ] **Step 2: Run the focused tests and verify expected failures**

Run:

```bash
/home/mestia/miniconda3/bin/conda run -n eventpose-dhp19 pytest tests/data/test_dhp19_aedat.py -q
```

- [ ] **Step 3: Implement filters with official constants**

Use these constants and order:

```python
CAMERAS = 4
WIDTH = 346
HEIGHT = 260
EVENTS_PER_CAMERA_FRAME = 7_500
EVENTS_PER_FRAME = 30_000
HOT_PIXEL_THRESHOLD = 10_000
BACKGROUND_DT_US = 70_000
IR_MASKS = ((780, 810, 115, 145), (1252, 1259, 136, 144))
```

Apply boundary rejection, orientation, hot-pixel removal, Numba-compiled background filtering, then both strict-region masks. The Numba loop must keep a `(4 * WIDTH, HEIGHT)` `int64` last-time map and update the eight neighboring cells for interior events, matching `BackgroundFilter.m`.

- [ ] **Step 4: Add failing normalization and framing tests**

Test a 30,000-event synthetic frame, per-camera normalization to `uint8`, exact output layout `(1, 260, 346, 4)`, and rejection when fewer than the requested complete frames remain.

- [ ] **Step 5: Implement `normalize_image_3sigma` and `accumulate_constant_count_frames`**

The accumulator returns:

```python
frames: np.ndarray        # (frame, height, width, camera), uint8
frame_end_ts: np.ndarray  # (frame,), uint32
frame_event_ranges: list[tuple[int, int]]
```

Stop immediately after the requested number of complete frames to keep this verification run bounded.

- [ ] **Step 6: Run all AEDAT tests**

Expected: all tests in `tests/data/test_dhp19_aedat.py` pass with no warnings.

### Task 4: Implement Vicon loading, label alignment, and projection

**Files:**
- Create: `tests/data/test_dhp19_pose.py`
- Create: `scripts/data/dhp19_pose.py`

- [ ] **Step 1: Write failing MAT-loading tests**

Use `scipy.io.savemat` to create a temporary `XYZPOS` structure containing the exact 13 joint names. Assert `load_vicon_pose` returns `(samples, 13, 3)` `float32` data in the official joint order and rejects missing fields or unequal sample counts.

- [ ] **Step 2: Run red and implement the MAT loader**

Define:

```python
JOINT_NAMES = (
    "head", "shoulderR", "shoulderL", "elbowR", "elbowL",
    "hipR", "hipL", "handR", "handL", "kneeR", "kneeL",
    "footR", "footL",
)
```

Load with `scipy.io.loadmat(..., squeeze_me=True, struct_as_record=False)`, validate every `(N, 3)` joint array, and stack on axis 1.

- [ ] **Step 3: Add failing tests for official frame-label averaging**

Test the MATLAB-compatible index rule:

```python
k_one_based = floor((frame_end_ts - start_ts) / 10_000) + 1
```

The next interval starts at the prior one-based `k`, preserving the official shared boundary sample. Use `np.nanmean`; raise if any complete joint coordinate remains non-finite.

- [ ] **Step 4: Implement and verify `mean_pose_per_frame`**

Return Python-facing label layout `(frame, 3, joint)` `float32` plus the one-based Vicon start/end index pairs used in the summary.

- [ ] **Step 5: Add failing projection tests**

Test homogeneous `3 x 4` projection, division by depth, official vertical flip `v = 260 - projected_y`, finite-depth validation, frame bounds, and channel mapping:

```python
CHANNEL_TO_MATRIX = ("P4.npy", "P1.npy", "P3.npy", "P2.npy")
```

- [ ] **Step 6: Implement projection and run all pose tests**

Expected: all tests in `tests/data/test_dhp19_pose.py` pass.

### Task 5: Implement atomic outputs and the verification command

**Files:**
- Create: `tests/data/test_process_dhp19_sample.py`
- Create: `scripts/data/process_dhp19_sample.py`

- [ ] **Step 1: Write failing output-layout tests**

Create small arrays and assert the writer produces:

```text
S1_session1_mov1_7500events_first20.h5:/DVS
S1_session1_mov1_7500events_first20_label.h5:/XYZ
summary.json
overlay_frame_0000.png
overlay_frame_0009.png
overlay_frame_0019.png
```

Assert `/DVS` is `(20, 260, 346, 4)` `uint8`, `/XYZ` is `(20, 3, 13)` `float32`, temporary files are gone, and replacing an existing verified output is atomic.

- [ ] **Step 2: Run red and implement HDF5/JSON writers**

Write `.tmp` siblings, reopen them to validate keys, shapes, dtypes, and finite labels, then use `os.replace`. Store source paths, source sizes, frame count, constants, sync bounds, filter counts, frame timestamp ranges, Vicon index ranges, projection in-frame counts, package versions, and official source commit in `summary.json`.

- [ ] **Step 3: Add failing overlay tests**

Generate a black four-camera frame and known projected joints. Save a 2-by-2 camera montage and use Pillow to assert the PNG is readable, has non-zero dimensions, and contains non-black pixels.

- [ ] **Step 4: Implement overlay rendering**

Use a non-interactive Matplotlib backend. Draw joint points and these skeleton edges:

```python
SKELETON_EDGES = (
    (0, 1), (0, 2), (1, 2),
    (1, 3), (3, 7), (2, 4), (4, 8),
    (1, 5), (2, 6), (5, 6),
    (5, 9), (9, 11), (6, 10), (10, 12),
)
```

Each panel must show channel/matrix identity, frame number, and timestamp range.

- [ ] **Step 5: Implement the CLI orchestration**

The command must expose explicit arguments with these defaults:

```text
--event /mnt/d/DHP19/DVS_movies/S1/session1/mov1.aedat
--label /mnt/d/DHP19/Vicon_data/S1_1_1.mat
--projection-dir /mnt/d/DHP19/P_matrices
--output-dir /mnt/d/DHP19_preprocessed/verification/S1_session1_mov1_20frames
--frames 20
```

It must validate all inputs before processing, print a short stage summary, and return non-zero on every validation failure.

- [ ] **Step 6: Run all unit tests**

Run:

```bash
/home/mestia/miniconda3/bin/conda run -n eventpose-dhp19 pytest tests/data -q
```

Expected: all tests pass with no failures or warnings.

### Task 6: Run the real 20-frame integration and document it

**Files:**
- Create: `docs/setup/dhp19-first-sample.md`
- Modify: `README.md` without reverting or staging unrelated existing edits

- [ ] **Step 1: Record source hashes before processing**

Run SHA-256 over the AEDAT, MAT, and five NPY calibration files and retain the values for the final post-run comparison.

- [ ] **Step 2: Run the real command**

```bash
/home/mestia/miniconda3/bin/conda run -n eventpose-dhp19 \
  python /mnt/d/EventPoseFinal/scripts/data/process_dhp19_sample.py
```

Expected: exit 0 and exactly 20 complete frames.

- [ ] **Step 3: Verify generated artifacts independently**

Run a separate Python check that opens both HDF5 files and asserts:

```python
dvs.shape == (20, 260, 346, 4)
dvs.dtype == np.uint8
xyz.shape == (20, 3, 13)
xyz.dtype == np.float32
np.isfinite(xyz).all()
np.count_nonzero(dvs, axis=(1, 2, 3)).min() > 0
```

Open all three PNGs with Pillow and assert they are nonblank. Inspect the three montages visually.

- [ ] **Step 4: Verify original inputs and Git boundaries**

Recompute the source hashes and compare them byte-for-byte with Step 1. Confirm no file under `D:\DHP19` changed and no output artifact appears in `git status --short`.

- [ ] **Step 5: Add focused setup documentation**

Document environment creation, the one-command verification run, output meanings, axis layouts, channel-to-projection mapping, and the fact that this is a 20-frame validation rather than training data. Add only a short link in the root README, preserving its existing dirty state.

- [ ] **Step 6: Run final verification**

Run fresh:

```bash
/home/mestia/miniconda3/bin/conda run -n eventpose-dhp19 pytest tests/data -q
/home/mestia/miniconda3/bin/conda run -n eventpose-dhp19 \
  python /mnt/d/EventPoseFinal/scripts/data/process_dhp19_sample.py
```

Then repeat the independent HDF5, PNG, source-hash, and Git-boundary checks. Report exact test counts, output paths, shapes, event statistics, and any remaining projection/alignment caveat.

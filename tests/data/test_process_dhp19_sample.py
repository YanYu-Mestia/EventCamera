import json
from pathlib import Path

import h5py
import numpy as np
from PIL import Image
import pytest

from scripts.data.process_dhp19_sample import (
    EVENT_FILENAME,
    LABEL_FILENAME,
    atomic_write_json,
    render_peak_alignment_montage,
    render_overlay_montage,
    write_hdf5_outputs,
)
from scripts.data.dhp19_aedat import FilteredEvents


def make_outputs():
    frames = np.zeros((20, 260, 346, 4), dtype=np.uint8)
    frames[:, 20, 10, :] = 255
    labels = np.ones((20, 3, 13), dtype=np.float32)
    return frames, labels


def test_hdf5_writer_preserves_official_python_layout(tmp_path: Path):
    frames, labels = make_outputs()

    event_path, label_path = write_hdf5_outputs(tmp_path, frames, labels)

    assert event_path.name == EVENT_FILENAME
    assert label_path.name == LABEL_FILENAME
    with h5py.File(event_path, "r") as event_file:
        dvs = event_file["DVS"]
        assert dvs.shape == (20, 260, 346, 4)
        assert dvs.dtype == np.dtype("uint8")
    with h5py.File(label_path, "r") as label_file:
        xyz = label_file["XYZ"]
        assert xyz.shape == (20, 3, 13)
        assert xyz.dtype == np.dtype("float32")
    assert not list(tmp_path.glob("*.tmp"))


def test_hdf5_writer_rejects_nonfinite_labels(tmp_path: Path):
    frames, labels = make_outputs()
    labels[0, 0, 0] = np.nan

    with pytest.raises(ValueError, match="finite"):
        write_hdf5_outputs(tmp_path, frames, labels)


def test_atomic_json_replaces_complete_document(tmp_path: Path):
    path = tmp_path / "summary.json"
    path.write_text("old")

    atomic_write_json(path, {"frames": 20})

    assert json.loads(path.read_text()) == {"frames": 20}
    assert not (tmp_path / "summary.json.tmp").exists()


def test_overlay_montage_is_readable_and_nonblank(tmp_path: Path):
    frames, labels = make_outputs()
    labels[0, 0, :] = 10.0
    labels[0, 1, :] = 20.0
    labels[0, 2, :] = 1.0
    projection = np.array(
        [[1.0, 0.0, 0.0, 0.0],
         [0.0, 1.0, 0.0, 0.0],
         [0.0, 0.0, 1.0, 0.0]],
        dtype=np.float64,
    )
    output = tmp_path / "overlay.png"

    counts = render_overlay_montage(
        output,
        frame=frames[0],
        pose=labels[0],
        projection_matrices=(projection,) * 4,
        frame_index=0,
        start_timestamp=100,
        end_timestamp=200,
    )

    with Image.open(output) as image:
        pixels = np.asarray(image.convert("RGB"))
        assert image.width > 0 and image.height > 0
        assert pixels.max() > pixels.min()
    assert counts == [13, 13, 13, 13]


def test_peak_alignment_montage_uses_same_time_window_for_events_and_pose(
    tmp_path: Path,
):
    events = FilteredEvents(
        global_x=np.array([10, 11, 12, 30, 31], dtype=np.int32),
        y=np.array([240, 240, 240, 200, 200], dtype=np.int32),
        camera=np.array([0, 0, 0, 0, 0], dtype=np.uint8),
        polarity=np.ones(5, dtype=np.uint8),
        timestamp=np.array([100, 110, 120, 300, 301], dtype=np.uint32),
    )
    pose = np.zeros((2, 13, 3), dtype=np.float32)
    pose[:, :, 0] = 10.0
    pose[:, :, 1] = 20.0
    pose[:, :, 2] = 1.0
    projection = np.array(
        [[1.0, 0.0, 0.0, 0.0],
         [0.0, 1.0, 0.0, 0.0],
         [0.0, 0.0, 1.0, 0.0]],
        dtype=np.float64,
    )
    output = tmp_path / "alignment.png"

    metadata = render_peak_alignment_montage(
        output,
        events=events,
        pose=pose,
        projection_matrices=(projection,) * 4,
        frame_index=0,
        frame_start_timestamp=90,
        frame_end_timestamp=400,
        synchronization_start=0,
        window_us=50,
    )

    with Image.open(output) as image:
        pixels = np.asarray(image.convert("RGB"))
        assert pixels.max() > pixels.min()
    assert metadata == {
        "start_timestamp_us": 100,
        "end_timestamp_us": 150,
        "event_count": 3,
        "vicon_sample_one_based": 1,
        "in_frame_joint_counts": [13, 13, 13, 13],
    }

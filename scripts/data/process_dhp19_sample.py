from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numba
import numpy as np
import scipy

from scripts.data.dhp19_aedat import (
    CAMERAS,
    EVENTS_PER_CAMERA_FRAME,
    FilteredEvents,
    HEIGHT,
    WIDTH,
    accumulate_constant_count_frames,
    filter_official_events,
    make_peak_time_window_frame,
    read_aedat2,
    synchronization_window,
)
from scripts.data.dhp19_pose import (
    CHANNEL_TO_MATRIX,
    JOINT_NAMES,
    load_projection_matrices,
    load_vicon_pose,
    mean_pose_per_frame,
    pose_at_timestamp,
    project_pose,
)


EVENT_FILENAME = "S1_session1_mov1_7500events_first20.h5"
LABEL_FILENAME = "S1_session1_mov1_7500events_first20_label.h5"
OFFICIAL_SOURCE_COMMIT = "12a3fe6bdb79cac7baf9981f215f3cf0c1f310b4"
ALIGNMENT_WINDOW_US = 100_000
SKELETON_EDGES = (
    (0, 1),
    (0, 2),
    (1, 2),
    (1, 3),
    (3, 7),
    (2, 4),
    (4, 8),
    (1, 5),
    (2, 6),
    (5, 6),
    (5, 9),
    (9, 11),
    (6, 10),
    (10, 12),
)


def _temporary_sibling(path: Path) -> Path:
    return path.with_name(path.name + ".tmp")


def write_hdf5_outputs(
    output_directory: str | Path,
    frames: np.ndarray,
    labels: np.ndarray,
) -> tuple[Path, Path]:
    output_directory = Path(output_directory)
    frames = np.asarray(frames)
    labels = np.asarray(labels)
    if frames.ndim != 4 or frames.shape[1:] != (HEIGHT, WIDTH, CAMERAS):
        raise ValueError(f"Invalid DVS output shape: {frames.shape}")
    if frames.dtype != np.uint8:
        raise ValueError(f"DVS output must be uint8, got {frames.dtype}")
    if labels.shape != (frames.shape[0], 3, len(JOINT_NAMES)):
        raise ValueError(f"Invalid XYZ output shape: {labels.shape}")
    if labels.dtype != np.float32:
        raise ValueError(f"XYZ output must be float32, got {labels.dtype}")
    if not np.isfinite(labels).all():
        raise ValueError("XYZ output must contain only finite values")

    output_directory.mkdir(parents=True, exist_ok=True)
    event_path = output_directory / EVENT_FILENAME
    label_path = output_directory / LABEL_FILENAME
    event_temporary = _temporary_sibling(event_path)
    label_temporary = _temporary_sibling(label_path)

    try:
        with h5py.File(event_temporary, "w") as handle:
            handle.create_dataset("DVS", data=frames)
        with h5py.File(label_temporary, "w") as handle:
            handle.create_dataset("XYZ", data=labels)

        with h5py.File(event_temporary, "r") as handle:
            dataset = handle["DVS"]
            if dataset.shape != frames.shape or dataset.dtype != np.dtype("uint8"):
                raise ValueError("Temporary DVS HDF5 validation failed")
        with h5py.File(label_temporary, "r") as handle:
            dataset = handle["XYZ"]
            if dataset.shape != labels.shape or dataset.dtype != np.dtype("float32"):
                raise ValueError("Temporary XYZ HDF5 validation failed")
            if not np.isfinite(dataset[...]).all():
                raise ValueError("Temporary XYZ HDF5 contains non-finite values")

        os.replace(event_temporary, event_path)
        os.replace(label_temporary, label_path)
    finally:
        event_temporary.unlink(missing_ok=True)
        label_temporary.unlink(missing_ok=True)

    return event_path, label_path


def atomic_write_json(path: str | Path, document: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_sibling(path)
    try:
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        json.loads(temporary.read_text(encoding="utf-8"))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def render_overlay_montage(
    output_path: str | Path,
    frame: np.ndarray,
    pose: np.ndarray,
    projection_matrices: tuple[np.ndarray, ...],
    frame_index: int,
    start_timestamp: int,
    end_timestamp: int,
    title_note: str | None = None,
) -> list[int]:
    output_path = Path(output_path)
    frame = np.asarray(frame)
    pose = np.asarray(pose)
    if frame.shape != (HEIGHT, WIDTH, CAMERAS):
        raise ValueError(f"Invalid overlay frame shape: {frame.shape}")
    if pose.shape != (3, len(JOINT_NAMES)):
        raise ValueError(f"Invalid overlay pose shape: {pose.shape}")
    if len(projection_matrices) != CAMERAS:
        raise ValueError("Four projection matrices are required")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_sibling(output_path)
    figure, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    in_frame_counts: list[int] = []
    try:
        for channel, axis in enumerate(axes.flat):
            projected = project_pose(pose, projection_matrices[channel])
            valid = projected.in_frame
            in_frame_counts.append(int(valid.sum()))
            axis.imshow(frame[:, :, channel], cmap="gray", vmin=0, vmax=255)
            for start_joint, end_joint in SKELETON_EDGES:
                if valid[start_joint] and valid[end_joint]:
                    axis.plot(
                        [projected.u[start_joint], projected.u[end_joint]],
                        [projected.v[start_joint], projected.v[end_joint]],
                        color="#00D4A6",
                        linewidth=1.5,
                    )
            axis.scatter(
                projected.u[valid],
                projected.v[valid],
                s=24,
                c="#FF3B30",
                edgecolors="white",
                linewidths=0.5,
            )
            axis.set_xlim(0, WIDTH)
            axis.set_ylim(HEIGHT, 0)
            axis.set_title(f"Channel {channel} / {CHANNEL_TO_MATRIX[channel]}")
            axis.axis("off")

        title = f"DHP19 frame {frame_index:04d} | {start_timestamp}-{end_timestamp} us"
        if title_note:
            title = f"{title} | {title_note}"
        figure.suptitle(title)
        figure.savefig(temporary, format="png", dpi=150)
        os.replace(temporary, output_path)
    finally:
        plt.close(figure)
        temporary.unlink(missing_ok=True)
    return in_frame_counts


def render_peak_alignment_montage(
    output_path: str | Path,
    events: FilteredEvents,
    pose: np.ndarray,
    projection_matrices: tuple[np.ndarray, ...],
    frame_index: int,
    frame_start_timestamp: int,
    frame_end_timestamp: int,
    synchronization_start: int,
    window_us: int = ALIGNMENT_WINDOW_US,
) -> dict:
    window = make_peak_time_window_frame(
        events,
        frame_start_timestamp=frame_start_timestamp,
        frame_end_timestamp=frame_end_timestamp,
        window_us=window_us,
    )
    center_timestamp = (window.start_timestamp + window.end_timestamp) // 2
    selected_pose, vicon_index = pose_at_timestamp(
        pose,
        timestamp=center_timestamp,
        synchronization_start=synchronization_start,
    )
    counts = render_overlay_montage(
        output_path,
        frame=window.frame,
        pose=selected_pose,
        projection_matrices=projection_matrices,
        frame_index=frame_index,
        start_timestamp=window.start_timestamp,
        end_timestamp=window.end_timestamp,
        title_note=f"peak {window.end_timestamp - window.start_timestamp} us",
    )
    return {
        "start_timestamp_us": window.start_timestamp,
        "end_timestamp_us": window.end_timestamp,
        "event_count": window.event_count,
        "vicon_sample_one_based": vicon_index,
        "in_frame_joint_counts": counts,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def process_sample(
    event_path: str | Path,
    label_path: str | Path,
    projection_directory: str | Path,
    output_directory: str | Path,
    frame_count: int = 20,
) -> dict:
    event_path = Path(event_path)
    label_path = Path(label_path)
    projection_directory = Path(projection_directory)
    output_directory = Path(output_directory)
    if not event_path.is_file():
        raise FileNotFoundError(event_path)
    if not label_path.is_file():
        raise FileNotFoundError(label_path)
    if frame_count <= 0:
        raise ValueError("frame_count must be positive")

    print(f"stage=labels path={label_path}", flush=True)
    pose = load_vicon_pose(label_path)
    projection_matrices = load_projection_matrices(projection_directory)

    print(f"stage=aedat path={event_path}", flush=True)
    events = read_aedat2(event_path)
    start_time, stop_time = synchronization_window(
        events.timestamp,
        events.special_timestamp,
        pose.shape[0],
    )

    print(f"stage=filter sync={start_time}:{stop_time}", flush=True)
    filtered, filter_stats = filter_official_events(
        events,
        start_time=start_time,
        stop_time=stop_time,
    )
    batch = accumulate_constant_count_frames(filtered, frame_count=frame_count)
    labels, vicon_ranges = mean_pose_per_frame(
        pose,
        batch.end_timestamps,
        synchronization_start=start_time,
    )

    print(f"stage=write output={output_directory}", flush=True)
    event_output, label_output = write_hdf5_outputs(
        output_directory,
        batch.frames,
        labels,
    )

    overlay_indices = sorted({0, min(9, frame_count - 1), frame_count - 1})
    overlay_counts: dict[str, list[int]] = {}
    overlay_paths: list[Path] = []
    alignment_metadata: dict[str, dict] = {}
    alignment_paths: list[Path] = []
    for frame_index in overlay_indices:
        overlay_path = output_directory / f"overlay_frame_{frame_index:04d}.png"
        counts = render_overlay_montage(
            overlay_path,
            frame=batch.frames[frame_index],
            pose=labels[frame_index],
            projection_matrices=projection_matrices,
            frame_index=frame_index,
            start_timestamp=int(batch.start_timestamps[frame_index]),
            end_timestamp=int(batch.end_timestamps[frame_index]),
            title_note="official full-frame mean pose",
        )
        overlay_counts[str(frame_index)] = counts
        overlay_paths.append(overlay_path)

        alignment_path = output_directory / (
            f"alignment_peak_{ALIGNMENT_WINDOW_US // 1000}ms_"
            f"frame_{frame_index:04d}.png"
        )
        alignment_metadata[str(frame_index)] = render_peak_alignment_montage(
            alignment_path,
            events=filtered,
            pose=pose,
            projection_matrices=projection_matrices,
            frame_index=frame_index,
            frame_start_timestamp=int(batch.start_timestamps[frame_index]),
            frame_end_timestamp=int(batch.end_timestamps[frame_index]),
            synchronization_start=start_time,
        )
        alignment_paths.append(alignment_path)

    source_files = [event_path, label_path] + [
        projection_directory / filename for filename in CHANNEL_TO_MATRIX
    ]
    summary = {
        "official_source_commit": OFFICIAL_SOURCE_COMMIT,
        "inputs": {
            str(path): {
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in source_files
        },
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "h5py": h5py.__version__,
            "matplotlib": matplotlib.__version__,
            "numba": numba.__version__,
        },
        "event_stream": {
            "polarity_events": int(events.timestamp.size),
            "special_events": int(events.special_timestamp.size),
            "synchronization_start_us": start_time,
            "synchronization_stop_us": stop_time,
            "filter": asdict(filter_stats),
        },
        "frames": {
            "count": frame_count,
            "events_per_camera": EVENTS_PER_CAMERA_FRAME,
            "events_per_full_frame": EVENTS_PER_CAMERA_FRAME * CAMERAS,
            "shape": list(batch.frames.shape),
            "start_timestamps_us": batch.start_timestamps.astype(int).tolist(),
            "end_timestamps_us": batch.end_timestamps.astype(int).tolist(),
            "event_ranges": [list(item) for item in batch.event_ranges],
        },
        "labels": {
            "source_samples": int(pose.shape[0]),
            "shape": list(labels.shape),
            "joint_names": list(JOINT_NAMES),
            "vicon_index_ranges_one_based": [list(item) for item in vicon_ranges],
        },
        "projection": {
            "channel_to_matrix": list(CHANNEL_TO_MATRIX),
            "in_frame_joint_counts": overlay_counts,
        },
        "alignment_diagnostics": {
            "selection": "densest event interval within each official frame",
            "window_us": ALIGNMENT_WINDOW_US,
            "frames": alignment_metadata,
        },
        "outputs": [
            str(event_output),
            str(label_output),
            *[str(path) for path in overlay_paths],
            *[str(path) for path in alignment_paths],
            str(output_directory / "summary.json"),
        ],
    }
    atomic_write_json(output_directory / "summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the first 20 aligned frames of DHP19 S1/session1/mov1."
    )
    parser.add_argument(
        "--event",
        type=Path,
        default=Path("/mnt/d/DHP19/DVS_movies/S1/session1/mov1.aedat"),
    )
    parser.add_argument(
        "--label",
        type=Path,
        default=Path("/mnt/d/DHP19/Vicon_data/S1_1_1.mat"),
    )
    parser.add_argument(
        "--projection-dir",
        type=Path,
        default=Path("/mnt/d/DHP19/P_matrices"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "/mnt/d/DHP19_preprocessed/verification/"
            "S1_session1_mov1_20frames"
        ),
    )
    parser.add_argument("--frames", type=int, default=20)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    summary = process_sample(
        event_path=arguments.event,
        label_path=arguments.label,
        projection_directory=arguments.projection_dir,
        output_directory=arguments.output_dir,
        frame_count=arguments.frames,
    )
    print(
        f"result=ok frames={summary['frames']['count']} "
        f"output={arguments.output_dir}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

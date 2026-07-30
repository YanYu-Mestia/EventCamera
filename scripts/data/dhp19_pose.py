from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import loadmat


JOINT_NAMES = (
    "head",
    "shoulderR",
    "shoulderL",
    "elbowR",
    "elbowL",
    "hipR",
    "hipL",
    "handR",
    "handL",
    "kneeR",
    "kneeL",
    "footR",
    "footL",
)

CHANNEL_TO_MATRIX = ("P4.npy", "P1.npy", "P3.npy", "P2.npy")


@dataclass(frozen=True)
class ProjectedPose:
    u: np.ndarray
    v: np.ndarray
    in_frame: np.ndarray


def load_vicon_pose(path: str | Path) -> np.ndarray:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    contents = loadmat(path, squeeze_me=True, struct_as_record=False)
    if "XYZPOS" not in contents:
        raise ValueError(f"Missing XYZPOS structure in {path}")
    xyzpos = contents["XYZPOS"]
    field_names = set(getattr(xyzpos, "_fieldnames", ()) or ())

    arrays: list[np.ndarray] = []
    sample_count: int | None = None
    for name in JOINT_NAMES:
        if name not in field_names:
            raise ValueError(f"Missing Vicon joint {name} in {path}")
        values = np.asarray(getattr(xyzpos, name), dtype=np.float32)
        if values.shape == (3,):
            values = values.reshape(1, 3)
        if values.ndim != 2 or values.shape[1] != 3:
            raise ValueError(f"Invalid Vicon shape for {name}: {values.shape}")
        if sample_count is None:
            sample_count = values.shape[0]
        elif values.shape[0] != sample_count:
            raise ValueError(f"Unequal Vicon sample count for {name}")
        arrays.append(values)

    return np.stack(arrays, axis=1).astype(np.float32, copy=False)


def mean_pose_per_frame(
    pose: np.ndarray,
    frame_end_timestamps: np.ndarray,
    synchronization_start: int,
) -> tuple[np.ndarray, tuple[tuple[int, int], ...]]:
    pose = np.asarray(pose, dtype=np.float32)
    frame_end_timestamps = np.asarray(frame_end_timestamps, dtype=np.uint32)
    if pose.ndim != 3 or pose.shape[1:] != (len(JOINT_NAMES), 3):
        raise ValueError(f"Expected Vicon pose shape (samples, 13, 3), got {pose.shape}")

    labels = np.empty(
        (frame_end_timestamps.size, 3, len(JOINT_NAMES)),
        dtype=np.float32,
    )
    ranges: list[tuple[int, int]] = []
    last_k_one_based = 1

    for frame_index, timestamp in enumerate(frame_end_timestamps):
        elapsed = int(timestamp) - int(synchronization_start)
        if elapsed < 0:
            raise ValueError("Frame timestamp precedes synchronization start")
        k_one_based = int(np.floor(elapsed * 0.0001)) + 1
        if k_one_based > pose.shape[0]:
            raise ValueError(
                f"Frame {frame_index} requires Vicon sample {k_one_based}, "
                f"but only {pose.shape[0]} exist"
            )
        if k_one_based < last_k_one_based:
            raise ValueError("Frame timestamps are not monotonic")

        window = pose[last_k_one_based - 1 : k_one_based]
        finite_count = np.sum(np.isfinite(window), axis=0)
        coordinate_sum = np.nansum(window, axis=0, dtype=np.float64)
        mean = np.full((len(JOINT_NAMES), 3), np.nan, dtype=np.float64)
        np.divide(
            coordinate_sum,
            finite_count,
            out=mean,
            where=finite_count > 0,
        )
        if not np.isfinite(mean).all():
            raise ValueError(
                f"Frame {frame_index} contains non-finite mean Vicon coordinates"
            )

        labels[frame_index] = mean.T.astype(np.float32)
        ranges.append((last_k_one_based, k_one_based))
        last_k_one_based = k_one_based

    return labels, tuple(ranges)


def pose_at_timestamp(
    pose: np.ndarray,
    timestamp: int,
    synchronization_start: int,
) -> tuple[np.ndarray, int]:
    pose = np.asarray(pose, dtype=np.float32)
    if pose.ndim != 3 or pose.shape[1:] != (len(JOINT_NAMES), 3):
        raise ValueError(f"Expected Vicon pose shape (samples, 13, 3), got {pose.shape}")

    elapsed = int(timestamp) - int(synchronization_start)
    if elapsed < 0:
        raise ValueError("Pose timestamp precedes synchronization start")
    index_one_based = elapsed // 10_000 + 1
    if index_one_based > pose.shape[0]:
        raise ValueError(
            f"Timestamp requires Vicon sample {index_one_based}, "
            f"but only {pose.shape[0]} exist"
        )

    selected = pose[index_one_based - 1].T.astype(np.float32, copy=False)
    if not np.isfinite(selected).all():
        raise ValueError(f"Vicon sample {index_one_based} contains non-finite values")
    return selected, index_one_based


def project_pose(
    pose_xyz: np.ndarray,
    projection_matrix: np.ndarray,
    width: int = 346,
    height: int = 260,
) -> ProjectedPose:
    pose_xyz = np.asarray(pose_xyz, dtype=np.float64)
    projection_matrix = np.asarray(projection_matrix, dtype=np.float64)
    if pose_xyz.shape != (3, len(JOINT_NAMES)):
        raise ValueError(f"Expected pose shape (3, 13), got {pose_xyz.shape}")
    if projection_matrix.shape != (3, 4):
        raise ValueError(
            f"Expected projection matrix shape (3, 4), got {projection_matrix.shape}"
        )

    homogeneous_pose = np.concatenate(
        [pose_xyz, np.ones((1, len(JOINT_NAMES)), dtype=np.float64)],
        axis=0,
    )
    projected = projection_matrix @ homogeneous_pose
    depth = projected[2]
    valid_depth = np.isfinite(depth) & (np.abs(depth) > np.finfo(float).eps)
    u = np.full(depth.shape, np.nan, dtype=np.float64)
    v = np.full(depth.shape, np.nan, dtype=np.float64)
    np.divide(projected[0], depth, out=u, where=valid_depth)
    projected_y = np.full(depth.shape, np.nan, dtype=np.float64)
    np.divide(projected[1], depth, out=projected_y, where=valid_depth)
    v[valid_depth] = height - projected_y[valid_depth]

    in_frame = (
        valid_depth
        & np.isfinite(u)
        & np.isfinite(v)
        & (u > 0)
        & (u <= width)
        & (v > 0)
        & (v <= height)
    )
    return ProjectedPose(u=u, v=v, in_frame=in_frame)


def load_projection_matrices(directory: str | Path) -> tuple[np.ndarray, ...]:
    directory = Path(directory)
    matrices: list[np.ndarray] = []
    for filename in CHANNEL_TO_MATRIX:
        path = directory / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        matrix = np.asarray(np.load(path), dtype=np.float64)
        if matrix.shape != (3, 4) or not np.isfinite(matrix).all():
            raise ValueError(f"Invalid projection matrix {path}: {matrix.shape}")
        matrices.append(matrix)
    return tuple(matrices)

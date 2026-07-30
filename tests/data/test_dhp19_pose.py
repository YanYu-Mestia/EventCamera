from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from scripts.data.dhp19_pose import (
    CHANNEL_TO_MATRIX,
    JOINT_NAMES,
    load_projection_matrices,
    load_vicon_pose,
    mean_pose_per_frame,
    pose_at_timestamp,
    project_pose,
)


def make_pose(samples: int = 6) -> np.ndarray:
    values = np.arange(samples, dtype=np.float32)[:, None, None]
    return np.broadcast_to(values, (samples, len(JOINT_NAMES), 3)).copy()


def write_pose(path: Path, pose: np.ndarray, missing_joint: str | None = None):
    xyzpos = {
        name: pose[:, index, :]
        for index, name in enumerate(JOINT_NAMES)
        if name != missing_joint
    }
    savemat(path, {"XYZPOS": xyzpos})


def test_load_vicon_pose_preserves_official_joint_order(tmp_path: Path):
    path = tmp_path / "pose.mat"
    expected = make_pose()
    for joint_index in range(len(JOINT_NAMES)):
        expected[:, joint_index, :] += joint_index * 100
    write_pose(path, expected)

    actual = load_vicon_pose(path)

    assert actual.shape == (6, 13, 3)
    assert actual.dtype == np.float32
    np.testing.assert_array_equal(actual, expected)


def test_load_vicon_pose_rejects_missing_joint(tmp_path: Path):
    path = tmp_path / "pose.mat"
    write_pose(path, make_pose(), missing_joint="footL")

    with pytest.raises(ValueError, match="footL"):
        load_vicon_pose(path)


def test_mean_pose_per_frame_matches_matlab_shared_boundary_rule():
    pose = make_pose()

    labels, ranges = mean_pose_per_frame(
        pose,
        frame_end_timestamps=np.array([20_100, 40_100], dtype=np.uint32),
        synchronization_start=100,
    )

    assert labels.shape == (2, 3, 13)
    np.testing.assert_allclose(labels[0], 1.0)
    np.testing.assert_allclose(labels[1], 3.0)
    assert ranges == ((1, 3), (3, 5))


def test_mean_pose_ignores_partial_nan_but_rejects_missing_coordinate():
    pose = make_pose()
    pose[0, 0, 0] = np.nan
    labels, _ = mean_pose_per_frame(
        pose,
        frame_end_timestamps=np.array([20_000], dtype=np.uint32),
        synchronization_start=0,
    )
    assert np.isfinite(labels).all()

    pose[:3, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        mean_pose_per_frame(
            pose,
            frame_end_timestamps=np.array([20_000], dtype=np.uint32),
            synchronization_start=0,
        )


def test_pose_at_timestamp_uses_matching_100hz_vicon_sample():
    pose = make_pose()

    selected, index_one_based = pose_at_timestamp(
        pose,
        timestamp=20_100,
        synchronization_start=100,
    )

    assert selected.shape == (3, 13)
    np.testing.assert_allclose(selected, 2.0)
    assert index_one_based == 3


def test_project_pose_uses_homogeneous_coordinates_and_vertical_flip():
    pose = np.zeros((3, 13), dtype=np.float32)
    pose[0, :] = 10.0
    pose[1, :] = 20.0
    pose[2, :] = 1.0
    matrix = np.array(
        [[1.0, 0.0, 0.0, 0.0],
         [0.0, 1.0, 0.0, 0.0],
         [0.0, 0.0, 1.0, 0.0]],
        dtype=np.float64,
    )

    projected = project_pose(pose, matrix)

    np.testing.assert_allclose(projected.u, 10.0)
    np.testing.assert_allclose(projected.v, 240.0)
    assert projected.in_frame.tolist() == [True] * 13


def test_projection_matrices_follow_official_channel_mapping(tmp_path: Path):
    for number in range(1, 5):
        np.save(tmp_path / f"P{number}.npy", np.full((3, 4), number, dtype=float))

    matrices = load_projection_matrices(tmp_path)

    assert CHANNEL_TO_MATRIX == ("P4.npy", "P1.npy", "P3.npy", "P2.npy")
    assert [int(matrix[0, 0]) for matrix in matrices] == [4, 1, 3, 2]

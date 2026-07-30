from pathlib import Path
import struct

import numpy as np
import pytest

from scripts.data.dhp19_aedat import (
    AedatEvents,
    FilteredEvents,
    accumulate_constant_count_frames,
    background_activity_mask,
    decode_addresses,
    filter_official_events,
    ir_region_keep_mask,
    make_peak_time_window_frame,
    normalize_image_3sigma,
    read_aedat2,
    synchronization_window,
)


def encode_polarity(*, x: int, y: int, camera: int, polarity: int) -> int:
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
    assert decoded.special_mask.tolist() == [False]


def test_read_aedat2_reads_big_endian_records_and_special_events(tmp_path: Path):
    path = tmp_path / "tiny.aedat"
    polarity = encode_polarity(x=4, y=5, camera=2, polarity=0)
    special = 0x400
    path.write_bytes(
        b"#!AER-DAT2.0\n#End of Preferences\n"
        + struct.pack(">IIII", polarity, 100, special, 200)
    )

    events = read_aedat2(path)

    assert events.x.tolist() == [4]
    assert events.y.tolist() == [5]
    assert events.camera.tolist() == [2]
    assert events.polarity.tolist() == [0]
    assert events.timestamp.tolist() == [100]
    assert events.special_timestamp.tolist() == [200]


def test_read_aedat2_rejects_partial_binary_record(tmp_path: Path):
    path = tmp_path / "broken.aedat"
    path.write_bytes(b"#!AER-DAT2.0\n#End of Preferences\n123")

    with pytest.raises(ValueError, match="multiple of 8"):
        read_aedat2(path)


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


def test_more_than_five_special_events_are_rejected():
    with pytest.raises(ValueError, match="corrupted"):
        synchronization_window(
            event_timestamps=np.array([90, 250], dtype=np.uint32),
            special_timestamps=np.arange(6, dtype=np.uint32),
            pose_samples=10,
        )


def test_official_filter_orients_coordinates_and_rejects_invalid_addresses():
    events = AedatEvents(
        x=np.array([0, 345, 346], dtype=np.uint16),
        y=np.array([0, 259, 10], dtype=np.uint16),
        camera=np.array([3, 0, 0], dtype=np.uint8),
        polarity=np.array([1, 0, 1], dtype=np.uint8),
        timestamp=np.array([100, 101, 102], dtype=np.uint32),
        special_timestamp=np.array([], dtype=np.uint32),
    )

    filtered, stats = filter_official_events(
        events,
        start_time=99,
        stop_time=103,
        hot_pixel_threshold=10,
        background_dt_us=1_000,
    )

    assert filtered.global_x.tolist() == [1383, 0]
    assert filtered.y.tolist() == [259, 0]
    assert filtered.camera.tolist() == [3, 0]
    assert stats.out_of_bounds == 1


def test_background_filter_requires_recent_neighbor_support():
    keep = background_activity_mask(
        global_x=np.array([10, 11, 20], dtype=np.int32),
        y=np.array([10, 10, 20], dtype=np.int32),
        timestamp=np.array([100_000, 100_010, 200_000], dtype=np.uint32),
        dt_us=70_000,
    )

    assert keep.tolist() == [False, True, False]


def test_ir_masks_use_strict_boundaries():
    keep = ir_region_keep_mask(
        global_x=np.array([780, 781, 809, 810, 1253], dtype=np.int32),
        y=np.array([120, 120, 120, 120, 140], dtype=np.int32),
    )

    assert keep.tolist() == [True, False, False, True, False]


def test_hot_pixels_are_removed_before_background_filtering():
    events = AedatEvents(
        x=np.array([100, 100, 100], dtype=np.uint16),
        y=np.array([100, 100, 100], dtype=np.uint16),
        camera=np.zeros(3, dtype=np.uint8),
        polarity=np.ones(3, dtype=np.uint8),
        timestamp=np.array([100_000, 100_001, 100_002], dtype=np.uint32),
        special_timestamp=np.array([], dtype=np.uint32),
    )

    filtered, stats = filter_official_events(
        events,
        start_time=99_999,
        stop_time=100_003,
        hot_pixel_threshold=3,
    )

    assert len(filtered.timestamp) == 0
    assert stats.hot_pixel_removed == 3


def test_normalization_and_constant_count_frames_use_python_official_layout():
    assert normalize_image_3sigma(np.zeros((3, 2))).dtype == np.uint8
    events = FilteredEvents(
        global_x=np.array([10, 10, 356, 356, 702, 702, 1048, 1048]),
        y=np.array([20, 20, 30, 30, 40, 40, 50, 50]),
        camera=np.array([0, 0, 1, 1, 2, 2, 3, 3], dtype=np.uint8),
        polarity=np.ones(8, dtype=np.uint8),
        timestamp=np.arange(1, 9, dtype=np.uint32),
    )

    batch = accumulate_constant_count_frames(
        events,
        frame_count=2,
        events_per_frame=4,
    )

    assert batch.frames.shape == (2, 260, 346, 4)
    assert batch.frames.dtype == np.uint8
    assert batch.start_timestamps.tolist() == [1, 5]
    assert batch.end_timestamps.tolist() == [4, 8]
    assert batch.event_ranges == ((0, 4), (4, 8))
    assert np.count_nonzero(batch.frames, axis=(1, 2, 3)).tolist() == [2, 2]


def test_accumulator_rejects_incomplete_requested_frames():
    events = FilteredEvents(
        global_x=np.array([10, 11, 12]),
        y=np.array([20, 20, 20]),
        camera=np.zeros(3, dtype=np.uint8),
        polarity=np.ones(3, dtype=np.uint8),
        timestamp=np.arange(1, 4, dtype=np.uint32),
    )

    with pytest.raises(ValueError, match="complete frames"):
        accumulate_constant_count_frames(events, frame_count=1, events_per_frame=4)


def test_peak_time_window_uses_densest_activity_and_preserves_layout():
    events = FilteredEvents(
        global_x=np.array([10, 11, 12, 356, 357], dtype=np.int32),
        y=np.array([20, 20, 20, 30, 30], dtype=np.int32),
        camera=np.array([0, 0, 0, 1, 1], dtype=np.uint8),
        polarity=np.ones(5, dtype=np.uint8),
        timestamp=np.array([100, 110, 120, 300, 301], dtype=np.uint32),
    )

    window = make_peak_time_window_frame(
        events,
        frame_start_timestamp=90,
        frame_end_timestamp=400,
        window_us=50,
    )

    assert window.start_timestamp == 100
    assert window.end_timestamp == 150
    assert window.event_count == 3
    assert window.frame.shape == (260, 346, 4)
    assert window.frame.dtype == np.uint8
    assert np.count_nonzero(window.frame[:, :, 0]) == 3
    assert np.count_nonzero(window.frame[:, :, 1:]) == 0


def test_peak_time_window_uses_full_frame_when_it_is_shorter_than_window():
    events = FilteredEvents(
        global_x=np.array([10, 11], dtype=np.int32),
        y=np.array([20, 20], dtype=np.int32),
        camera=np.zeros(2, dtype=np.uint8),
        polarity=np.ones(2, dtype=np.uint8),
        timestamp=np.array([100, 120], dtype=np.uint32),
    )

    window = make_peak_time_window_frame(
        events,
        frame_start_timestamp=90,
        frame_end_timestamp=140,
        window_us=100,
    )

    assert (window.start_timestamp, window.end_timestamp) == (90, 140)
    assert window.event_count == 2

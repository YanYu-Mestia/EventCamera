from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numba import njit


APS_OR_IMU_MASK = np.uint32(0x80000000)
SIGNAL_OR_SPECIAL_MASK = np.uint32(0x00000400)
Y_MASK = np.uint32(0x7FC00000)
X_MASK = np.uint32(0x003FF000)
CAMERA_MASK = np.uint32(0x0000000F)

CAMERAS = 4
WIDTH = 346
HEIGHT = 260
EVENTS_PER_CAMERA_FRAME = 7_500
EVENTS_PER_FRAME = EVENTS_PER_CAMERA_FRAME * CAMERAS
HOT_PIXEL_THRESHOLD = 10_000
BACKGROUND_DT_US = 70_000
IR_MASKS = ((780, 810, 115, 145), (1252, 1259, 136, 144))


@dataclass(frozen=True)
class AddressFields:
    x: np.ndarray
    y: np.ndarray
    camera: np.ndarray
    polarity: np.ndarray
    polarity_mask: np.ndarray
    special_mask: np.ndarray


@dataclass(frozen=True)
class AedatEvents:
    x: np.ndarray
    y: np.ndarray
    camera: np.ndarray
    polarity: np.ndarray
    timestamp: np.ndarray
    special_timestamp: np.ndarray


@dataclass(frozen=True)
class FilteredEvents:
    global_x: np.ndarray
    y: np.ndarray
    camera: np.ndarray
    polarity: np.ndarray
    timestamp: np.ndarray


@dataclass(frozen=True)
class FilterStats:
    input_events: int
    synchronized_events: int
    out_of_bounds: int
    hot_pixel_removed: int
    background_removed: int
    ir_mask_removed: int
    retained_events: int


@dataclass(frozen=True)
class FrameBatch:
    frames: np.ndarray
    start_timestamps: np.ndarray
    end_timestamps: np.ndarray
    event_ranges: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class PeakTimeWindowFrame:
    frame: np.ndarray
    start_timestamp: int
    end_timestamp: int
    event_count: int


def decode_addresses(addresses: np.ndarray) -> AddressFields:
    addresses = np.asarray(addresses, dtype=np.uint32)
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


def _aedat2_data_offset(path: Path) -> int:
    with path.open("rb") as stream:
        first_line = stream.readline()
        if not first_line.startswith(b"#!AER-DAT2.0"):
            raise ValueError(f"Not an AEDAT2 file: {path}")

        while True:
            position = stream.tell()
            first_byte = stream.read(1)
            if not first_byte:
                return position
            if first_byte != b"#":
                stream.seek(position)
                return position

            line = first_byte + stream.readline()
            if line.rstrip(b"\r\n") == b"#End of Preferences":
                return stream.tell()


def read_aedat2(path: str | Path) -> AedatEvents:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    offset = _aedat2_data_offset(path)
    payload_size = path.stat().st_size - offset
    if payload_size % 8:
        raise ValueError(
            f"AEDAT2 binary payload must be a multiple of 8 bytes: {path}"
        )

    record_dtype = np.dtype([("address", ">u4"), ("timestamp", ">u4")])
    record_count = payload_size // record_dtype.itemsize
    records = np.memmap(
        path,
        dtype=record_dtype,
        mode="r",
        offset=offset,
        shape=(record_count,),
    )
    addresses = np.asarray(records["address"], dtype=np.uint32)
    timestamps = np.asarray(records["timestamp"], dtype=np.uint32)
    decoded = decode_addresses(addresses)

    polarity_mask = decoded.polarity_mask
    special_mask = decoded.special_mask
    return AedatEvents(
        x=decoded.x[polarity_mask],
        y=decoded.y[polarity_mask],
        camera=decoded.camera[polarity_mask],
        polarity=decoded.polarity[polarity_mask],
        timestamp=timestamps[polarity_mask],
        special_timestamp=timestamps[special_mask],
    )


def synchronization_window(
    event_timestamps: np.ndarray,
    special_timestamps: np.ndarray,
    pose_samples: int,
) -> tuple[int, int]:
    events = np.asarray(event_timestamps, dtype=np.uint32)
    specials = np.asarray(special_timestamps, dtype=np.uint32)
    if events.size == 0:
        raise ValueError("Cannot synchronize an empty event stream")
    if pose_samples <= 0:
        raise ValueError("pose_samples must be positive")

    first_event = int(events[0])
    last_event = int(events[-1])
    pose_duration_us = int(pose_samples) * 10_000
    count = int(specials.size)

    if count == 0:
        start, stop = first_event, last_event
    elif count == 1:
        special = int(specials[0])
        if special - first_event > last_event - special:
            start, stop = special - pose_duration_us, special
        else:
            start, stop = special, special + pose_duration_us
    elif count in (2, 4):
        special = int(specials[0])
        if last_event < first_event:
            start, stop = special, int(events.max())
        elif special - first_event > last_event - special:
            start, stop = special - pose_duration_us, special
        else:
            start, stop = special, special + pose_duration_us
    elif count in (3, 5):
        start, stop = int(specials[0]), int(specials[-1])
    else:
        raise ValueError(
            f"Recording is corrupted: found {count} synchronization events"
        )

    if start < 0 or stop <= start:
        raise ValueError(f"Invalid synchronization window: {start}..{stop}")
    return start, stop


@njit(cache=True)
def _background_activity_mask_numba(
    global_x: np.ndarray,
    y: np.ndarray,
    timestamp: np.ndarray,
    dt_us: int,
    x_dimension: int,
    y_dimension: int,
) -> np.ndarray:
    last_times = np.zeros((x_dimension, y_dimension), dtype=np.int64)
    keep = np.ones(timestamp.size, dtype=np.bool_)

    for index in range(timestamp.size):
        ts = int(timestamp[index])
        x_value = int(global_x[index])
        y_value = int(y[index])
        if ts - last_times[x_value, y_value] > dt_us:
            keep[index] = False

        if (
            x_value != 0
            and x_value != x_dimension - 1
            and y_value != 0
            and y_value != y_dimension - 1
        ):
            last_times[x_value - 1, y_value] = ts
            last_times[x_value + 1, y_value] = ts
            last_times[x_value, y_value - 1] = ts
            last_times[x_value, y_value + 1] = ts
            last_times[x_value - 1, y_value - 1] = ts
            last_times[x_value + 1, y_value + 1] = ts
            last_times[x_value - 1, y_value + 1] = ts
            last_times[x_value + 1, y_value - 1] = ts

    return keep


def background_activity_mask(
    global_x: np.ndarray,
    y: np.ndarray,
    timestamp: np.ndarray,
    dt_us: int = BACKGROUND_DT_US,
) -> np.ndarray:
    global_x = np.ascontiguousarray(global_x, dtype=np.int32)
    y = np.ascontiguousarray(y, dtype=np.int32)
    timestamp = np.ascontiguousarray(timestamp, dtype=np.uint32)
    if not (global_x.shape == y.shape == timestamp.shape):
        raise ValueError("Background-filter arrays must have matching shapes")
    if np.any(global_x < 0) or np.any(global_x >= CAMERAS * WIDTH):
        raise ValueError("Global x coordinate outside DHP19 bounds")
    if np.any(y < 0) or np.any(y >= HEIGHT):
        raise ValueError("Y coordinate outside DHP19 bounds")
    return _background_activity_mask_numba(
        global_x,
        y,
        timestamp,
        int(dt_us),
        CAMERAS * WIDTH,
        HEIGHT,
    )


def ir_region_keep_mask(global_x: np.ndarray, y: np.ndarray) -> np.ndarray:
    global_x = np.asarray(global_x)
    y = np.asarray(y)
    keep = np.ones(global_x.shape, dtype=bool)
    for x_min, x_max, y_min, y_max in IR_MASKS:
        inside = (
            (global_x > x_min)
            & (global_x < x_max)
            & (y > y_min)
            & (y < y_max)
        )
        keep &= ~inside
    return keep


def _select_filtered(events: FilteredEvents, keep: np.ndarray) -> FilteredEvents:
    return FilteredEvents(
        global_x=events.global_x[keep],
        y=events.y[keep],
        camera=events.camera[keep],
        polarity=events.polarity[keep],
        timestamp=events.timestamp[keep],
    )


def filter_official_events(
    events: AedatEvents,
    start_time: int,
    stop_time: int,
    hot_pixel_threshold: int = HOT_PIXEL_THRESHOLD,
    background_dt_us: int = BACKGROUND_DT_US,
) -> tuple[FilteredEvents, FilterStats]:
    time_keep = (events.timestamp > start_time) & (events.timestamp < stop_time)
    raw_x = events.x[time_keep].astype(np.int32)
    raw_y = events.y[time_keep].astype(np.int32)
    camera = events.camera[time_keep]
    polarity = events.polarity[time_keep]
    timestamp = events.timestamp[time_keep]

    bounds_keep = (
        (raw_x >= 0)
        & (raw_x < WIDTH)
        & (raw_y >= 0)
        & (raw_y < HEIGHT)
        & (camera < CAMERAS)
    )
    synchronized_count = int(timestamp.size)
    raw_x = raw_x[bounds_keep]
    raw_y = raw_y[bounds_keep]
    camera = camera[bounds_keep]
    polarity = polarity[bounds_keep]
    timestamp = timestamp[bounds_keep]

    global_x = (WIDTH - 1 - raw_x) + camera.astype(np.int32) * WIDTH
    oriented_y = HEIGHT - 1 - raw_y
    filtered = FilteredEvents(
        global_x=global_x.astype(np.int32),
        y=oriented_y.astype(np.int32),
        camera=camera.astype(np.uint8),
        polarity=polarity.astype(np.uint8),
        timestamp=timestamp.astype(np.uint32),
    )

    if filtered.timestamp.size:
        flat_index = filtered.global_x * HEIGHT + filtered.y
        counts = np.bincount(flat_index, minlength=CAMERAS * WIDTH * HEIGHT)
        hot_keep = counts[flat_index] < int(hot_pixel_threshold)
    else:
        hot_keep = np.empty(0, dtype=bool)
    before_hot = len(filtered.timestamp)
    filtered = _select_filtered(filtered, hot_keep)

    background_keep = background_activity_mask(
        filtered.global_x,
        filtered.y,
        filtered.timestamp,
        dt_us=background_dt_us,
    )
    before_background = len(filtered.timestamp)
    filtered = _select_filtered(filtered, background_keep)

    ir_keep = ir_region_keep_mask(filtered.global_x, filtered.y)
    before_ir = len(filtered.timestamp)
    filtered = _select_filtered(filtered, ir_keep)

    stats = FilterStats(
        input_events=int(events.timestamp.size),
        synchronized_events=synchronized_count,
        out_of_bounds=synchronized_count - before_hot,
        hot_pixel_removed=before_hot - before_background,
        background_removed=before_background - before_ir,
        ir_mask_removed=before_ir - len(filtered.timestamp),
        retained_events=len(filtered.timestamp),
    )
    return filtered, stats


def normalize_image_3sigma(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image, dtype=np.float64)
    positive = image > 0
    output = np.zeros(image.shape, dtype=np.uint8)
    values = image[positive]
    if values.size == 0:
        return output

    sigma = float(np.std(values, ddof=1)) if values.size > 1 else 0.0
    sigma = max(sigma, 0.1 / 255.0)
    scaled = np.floor(np.clip(image[positive] * 255.0 / (3.0 * sigma), 0, 255))
    output[positive] = scaled.astype(np.uint8)
    return output


def make_peak_time_window_frame(
    events: FilteredEvents,
    frame_start_timestamp: int,
    frame_end_timestamp: int,
    window_us: int,
) -> PeakTimeWindowFrame:
    frame_start_timestamp = int(frame_start_timestamp)
    frame_end_timestamp = int(frame_end_timestamp)
    window_us = int(window_us)
    if frame_end_timestamp <= frame_start_timestamp:
        raise ValueError("Frame end timestamp must follow its start timestamp")
    if window_us <= 0:
        raise ValueError("window_us must be positive")

    in_frame = (
        (events.timestamp >= frame_start_timestamp)
        & (events.timestamp <= frame_end_timestamp)
    )
    timestamps = events.timestamp[in_frame]
    if timestamps.size == 0:
        raise ValueError("No filtered events in the requested frame interval")
    if np.any(timestamps[1:] < timestamps[:-1]):
        raise ValueError("Event timestamps must be monotonic")

    frame_duration = frame_end_timestamp - frame_start_timestamp
    actual_window_us = min(window_us, frame_duration)
    if actual_window_us == frame_duration:
        window_start = frame_start_timestamp
        window_end = frame_end_timestamp
    else:
        best_start_index = 0
        best_count = 0
        left = 0
        for right in range(timestamps.size):
            while int(timestamps[right]) - int(timestamps[left]) > actual_window_us:
                left += 1
            count = right - left + 1
            if count > best_count:
                best_start_index = left
                best_count = count

        latest_start = frame_end_timestamp - actual_window_us
        window_start = min(int(timestamps[best_start_index]), latest_start)
        window_start = max(window_start, frame_start_timestamp)
        window_end = window_start + actual_window_us

    in_window = in_frame & (
        (events.timestamp >= window_start) & (events.timestamp <= window_end)
    )
    image = np.zeros((CAMERAS * WIDTH, HEIGHT), dtype=np.uint32)
    np.add.at(
        image,
        (events.global_x[in_window], events.y[in_window]),
        1,
    )
    frame = np.zeros((HEIGHT, WIDTH, CAMERAS), dtype=np.uint8)
    for camera_index in range(CAMERAS):
        camera_image = image[
            camera_index * WIDTH : (camera_index + 1) * WIDTH,
            :,
        ]
        frame[:, :, camera_index] = normalize_image_3sigma(camera_image).T

    return PeakTimeWindowFrame(
        frame=frame,
        start_timestamp=window_start,
        end_timestamp=window_end,
        event_count=int(np.count_nonzero(in_window)),
    )


def accumulate_constant_count_frames(
    events: FilteredEvents,
    frame_count: int,
    events_per_frame: int = EVENTS_PER_FRAME,
) -> FrameBatch:
    if frame_count <= 0 or events_per_frame <= 0:
        raise ValueError("frame_count and events_per_frame must be positive")
    required_events = frame_count * events_per_frame
    if len(events.timestamp) < required_events:
        raise ValueError(
            f"Not enough retained events for {frame_count} complete frames: "
            f"need {required_events}, have {len(events.timestamp)}"
        )

    frames = np.zeros((frame_count, HEIGHT, WIDTH, CAMERAS), dtype=np.uint8)
    start_timestamps = np.empty(frame_count, dtype=np.uint32)
    end_timestamps = np.empty(frame_count, dtype=np.uint32)
    ranges: list[tuple[int, int]] = []

    for frame_index in range(frame_count):
        start = frame_index * events_per_frame
        stop = start + events_per_frame
        image = np.zeros((CAMERAS * WIDTH, HEIGHT), dtype=np.uint32)
        np.add.at(
            image,
            (events.global_x[start:stop], events.y[start:stop]),
            1,
        )
        for camera_index in range(CAMERAS):
            camera_image = image[
                camera_index * WIDTH : (camera_index + 1) * WIDTH,
                :,
            ]
            frames[frame_index, :, :, camera_index] = normalize_image_3sigma(
                camera_image
            ).T

        start_timestamps[frame_index] = events.timestamp[start]
        end_timestamps[frame_index] = events.timestamp[stop - 1]
        ranges.append((start, stop))

    return FrameBatch(
        frames=frames,
        start_timestamps=start_timestamps,
        end_timestamps=end_timestamps,
        event_ranges=tuple(ranges),
    )

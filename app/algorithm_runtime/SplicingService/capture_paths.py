import os
import time
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence

LINE_SCAN_TWO_D_DIR_NAMES = ("2d", "2D")
TWO_D_DIR_NAMES = (*LINE_SCAN_TWO_D_DIR_NAMES, "area")
THREE_D_DIR_NAMES = ("3D", "3d")
TWO_D_PATTERNS = ("*.bmp", "*.jpg")
DEFAULT_CAPTURE_SEQUENCE_GAP_SECONDS = float(
    os.getenv("LG3D_CAPTURE_SEQUENCE_GAP_SECONDS", "20.0"))
MAX_CAPTURE_START_SKEW_SLOTS = int(
    os.getenv("LG3D_MAX_CAPTURE_START_SKEW_SLOTS", "1"))
MAX_CAPTURE_MISSING_SLOTS = int(
    os.getenv("LG3D_MAX_CAPTURE_MISSING_SLOTS", "2"))
CAPTURE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S:%f"


def _numeric_stem_key(path: Path) -> tuple[int, str]:
    stem = path.name
    for suffix in reversed(path.suffixes):
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
    try:
        return int(stem), path.name
    except ValueError:
        return 10**12, path.name


def resolve_capture_dir(source: Path | str, coil_id: str | int,
                        dir_names: Iterable[str]) -> Path:
    coil_dir = Path(source) / str(coil_id)
    dir_names = tuple(dir_names)
    if coil_dir.exists():
        children = {
            path.name: path
            for path in coil_dir.iterdir() if path.is_dir()
        }
        for name in dir_names:
            if name in children:
                return children[name]
        lowered = {path.name.lower(): path for path in children.values()}
        for name in dir_names:
            match = lowered.get(name.lower())
            if match is not None:
                return match
    for name in dir_names:
        candidate = coil_dir / name
        if candidate.exists():
            return candidate
    return coil_dir / dir_names[0]


def sorted_indexed_files(folder: Path | str,
                         patterns: Iterable[str]) -> list[Path]:
    folder = Path(folder)
    files: dict[Path, Path] = {}
    for pattern in patterns:
        for path in folder.glob(pattern):
            if path.is_file():
                files[path.resolve()] = path
    return sorted(files.values(), key=_numeric_stem_key)


def _capture_wall_time_seconds(metadata: dict[str, Any]) -> float | None:
    capture_time = metadata.get("capTime")
    if capture_time:
        try:
            return datetime.strptime(str(capture_time),
                                     CAPTURE_TIME_FORMAT).timestamp()
        except (TypeError, ValueError, OverflowError):
            try:
                return datetime.fromisoformat(str(capture_time)).timestamp()
            except (TypeError, ValueError, OverflowError):
                pass
    return None


def _capture_device_time_seconds(metadata: dict[str, Any]) -> float | None:
    try:
        timestamp = float(metadata["timestamp"])
        frequency = float(metadata.get("timestamp_frequency", 1_000_000_000))
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    if frequency <= 0:
        return None
    return timestamp / frequency


def capture_frame_time_seconds(metadata: dict[str, Any]) -> float | None:
    """Return one frame's wall-clock time, or its device time as fallback."""
    wall_time = _capture_wall_time_seconds(metadata)
    if wall_time is not None:
        return wall_time
    return _capture_device_time_seconds(metadata)


def _capture_times_in_one_domain(
        metadata_items: Sequence[dict[str, Any]]) -> list[float] | None:
    """Choose one time domain for the complete comparison set."""
    wall_times = [_capture_wall_time_seconds(item) for item in metadata_items]
    if all(value is not None for value in wall_times):
        return [float(value) for value in wall_times]

    device_times = [
        _capture_device_time_seconds(item) for item in metadata_items
    ]
    if any(value is None for value in device_times):
        return None
    return [float(value) for value in device_times]


def select_capture_frame_sequence(
    records: Sequence[tuple[Path, dict[str, Any]]],
    gap_seconds: float = DEFAULT_CAPTURE_SEQUENCE_GAP_SECONDS,
) -> list[tuple[Path, dict[str, Any]]]:
    """Select one chronological acquisition sequence from indexed files.

    A repeated trigger can reset ``save_index`` and overwrite an early file while
    leaving the rest of the previous acquisition in place.  Numeric filename
    order then inserts that late frame at the beginning of a line-scan mosaic.
    Split records by capture-time gaps and keep the longest contiguous sequence;
    when lengths tie, prefer the newest sequence.
    """
    records = list(records)
    if len(records) < 2:
        return records

    capture_times = _capture_times_in_one_domain(
        [metadata for _, metadata in records])
    if capture_times is None:
        return records
    timed_records = list(zip(records, capture_times))

    timed_records.sort(key=lambda item: item[1])
    capture_gaps = [
        timed_records[index + 1][1] - timed_records[index][1]
        for index in range(len(timed_records) - 1)
        if timed_records[index + 1][1] > timed_records[index][1]
    ]
    max_gap = max(float(gap_seconds), 0.0)
    if len(capture_gaps) >= 2:
        shortest_half = sorted(capture_gaps)[:max(1, len(capture_gaps) // 2)]
        nominal_period = median(shortest_half)
        max_gap = min(max_gap, nominal_period * 5)

    sequences: list[list[tuple[tuple[Path, dict[str, Any]], float]]] = []
    current_sequence: list[tuple[tuple[Path, dict[str, Any]], float]] = []
    for record, capture_time in timed_records:
        if (current_sequence
                and capture_time - current_sequence[-1][1] > max_gap):
            sequences.append(current_sequence)
            current_sequence = []
        current_sequence.append((record, capture_time))
    if current_sequence:
        sequences.append(current_sequence)

    selected = max(sequences,
                   key=lambda sequence: (len(sequence), sequence[-1][1]))
    return [record for record, _ in selected]


def align_capture_frame_sequences(
    sequences: Sequence[Sequence[tuple[str, dict[str, Any]]]],
) -> list[list[str | None]]:
    """Map each camera sequence onto a shared line-scan time axis.

    Camera save indices are local and can diverge after a dropped frame or a
    resumed capture.  Host capture times provide the cross-camera contract.  A
    missing time slot is represented by ``None`` so callers can insert an empty
    image/depth block instead of collapsing the physical gap.
    """
    sequences = [list(sequence) for sequence in sequences]
    if not sequences:
        return []
    if any(not sequence for sequence in sequences):
        return [[stem for stem, _ in sequence] for sequence in sequences]

    flattened_metadata = [
        metadata for sequence in sequences for _, metadata in sequence
    ]
    capture_times = _capture_times_in_one_domain(flattened_metadata)
    if capture_times is None:
        raise ValueError(
            "capture timestamps are incomplete; physical frame slots cannot be aligned"
        )
    time_iterator = iter(capture_times)
    timed_sequences = [[(stem, next(time_iterator)) for stem, _ in sequence]
                       for sequence in sequences]

    positive_deltas = [
        sequence[index + 1][1] - sequence[index][1]
        for sequence in timed_sequences for index in range(len(sequence) - 1)
        if sequence[index + 1][1] > sequence[index][1]
    ]
    if not positive_deltas:
        raise ValueError(
            "capture timestamps do not contain a positive frame period")

    shortest_half = sorted(positive_deltas)[:max(1, len(positive_deltas) // 2)]
    nominal_period = float(median(shortest_half))
    first_capture_time = min(sequence[0][1] for sequence in timed_sequences)
    slotted_sequences = []
    max_slot = 0
    for sequence in timed_sequences:
        sequence_start = sequence[0][1]
        start_slot = int(
            round((sequence_start - first_capture_time) / nominal_period))
        if sequence_start - first_capture_time < nominal_period * 0.75:
            start_slot = 0
        if start_slot > MAX_CAPTURE_START_SKEW_SLOTS:
            raise ValueError(
                f"camera capture start skew is {start_slot} slots; "
                f"maximum is {MAX_CAPTURE_START_SKEW_SLOTS}")
        slotted = []
        previous_slot = start_slot - 1
        for stem, capture_time in sequence:
            local_slot = int(
                round((capture_time - sequence_start) / nominal_period))
            slot = max(start_slot + local_slot, previous_slot + 1)
            implied_missing_slots = slot - start_slot - len(slotted)
            if implied_missing_slots > MAX_CAPTURE_MISSING_SLOTS:
                raise ValueError(
                    f"camera capture has at least {implied_missing_slots} missing slots; "
                    f"maximum is {MAX_CAPTURE_MISSING_SLOTS}")
            slotted.append((slot, stem))
            previous_slot = slot
            max_slot = max(max_slot, slot)
        slotted_sequences.append(slotted)

    plans = []
    for slotted in slotted_sequences:
        plan: list[str | None] = [None] * (max_slot + 1)
        for slot, stem in slotted:
            plan[slot] = stem
        missing_slots = sum(stem is None for stem in plan)
        if missing_slots > MAX_CAPTURE_MISSING_SLOTS:
            raise ValueError(
                f"camera capture has {missing_slots} missing slots; "
                f"maximum is {MAX_CAPTURE_MISSING_SLOTS}")
        plans.append(plan)
    return plans


def capture_complete(source: Path | str,
                     coil_id: str | int,
                     quiet_seconds: float = 3.2,
                     min_files: int = 4,
                     dir_names: Iterable[str] = TWO_D_DIR_NAMES) -> bool:
    source2_d = resolve_capture_dir(source, coil_id, dir_names)
    if not source2_d.exists():
        return False

    image_files = sorted_indexed_files(source2_d, TWO_D_PATTERNS)
    if len(image_files) < min_files:
        return False

    now = time.time()
    return all(now - image_file.stat().st_mtime >= quiet_seconds
               for image_file in image_files)

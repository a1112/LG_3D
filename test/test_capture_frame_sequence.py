import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALGORITHM_ROOT = PROJECT_ROOT / "app" / "algorithm_runtime"
if str(ALGORITHM_ROOT) not in sys.path:
    sys.path.insert(0, str(ALGORITHM_ROOT))

from SplicingService.capture_paths import (  # noqa: E402
    align_capture_frame_sequences, capture_frame_time_seconds,
    select_capture_frame_sequence,
)


def _record(tmp_path, stem, capture_time):
    return (
        tmp_path / f"{stem}.json",
        {
            "capTime": capture_time,
            "timestamp": int(stem) * 1_000_000_000,
            "timestamp_frequency": 1_000_000_000,
        },
    )


def test_select_capture_sequence_discards_late_overwritten_zero_frame(
        tmp_path):
    records = [
        _record(tmp_path, "0", "2026-07-11 01:06:57:392412"),
        _record(tmp_path, "1", "2026-07-11 01:03:37:720022"),
        _record(tmp_path, "2", "2026-07-11 01:03:38:764673"),
        _record(tmp_path, "3", "2026-07-11 01:03:39:826924"),
        _record(tmp_path, "4", "2026-07-11 01:03:40:800457"),
    ]

    selected = select_capture_frame_sequence(records, gap_seconds=20)

    assert [path.stem for path, _ in selected] == ["1", "2", "3", "4"]


def test_select_capture_sequence_prefers_newest_when_lengths_tie(tmp_path):
    records = [
        _record(tmp_path, "0", "2026-07-11 01:00:00:000000"),
        _record(tmp_path, "1", "2026-07-11 01:00:01:000000"),
        _record(tmp_path, "8", "2026-07-11 01:02:00:000000"),
        _record(tmp_path, "9", "2026-07-11 01:02:01:000000"),
    ]

    selected = select_capture_frame_sequence(records, gap_seconds=20)

    assert [path.stem for path, _ in selected] == ["8", "9"]


def test_select_capture_sequence_preserves_numeric_fallback_without_times(
        tmp_path):
    records = [(tmp_path / "0.json", {}), (tmp_path / "1.json", {})]

    assert select_capture_frame_sequence(records) == records


def test_capture_frame_time_falls_back_to_camera_timestamp():
    metadata = {
        "timestamp": 2_500_000_000,
        "timestamp_frequency": 1_000_000_000,
    }

    assert capture_frame_time_seconds(metadata) == 2.5


def test_sequence_uses_one_time_domain_when_one_wall_clock_is_missing(
        tmp_path):
    records = [
        (tmp_path / "0.json", {
            "capTime": "2026-07-11 01:00:00:000000",
            "timestamp": 0,
            "timestamp_frequency": 1,
        }),
        (tmp_path / "1.json", {
            "timestamp": 1,
            "timestamp_frequency": 1,
        }),
        (tmp_path / "2.json", {
            "capTime": "2026-07-11 01:00:02:000000",
            "timestamp": 2,
            "timestamp_frequency": 1,
        }),
    ]

    selected = select_capture_frame_sequence(records)

    assert [path.stem for path, _ in selected] == ["0", "1", "2"]


def _frame(stem, second):
    return stem, {"capTime": f"2026-07-11 01:00:{second:02d}:000000"}


def test_align_capture_sequences_inserts_internal_missing_frame_slot():
    complete = [_frame(str(index), index) for index in range(8)]
    missing_four = [
        _frame(stem, second)
        for stem, second in [("1", 0), ("2", 1), ("3",
                                                  2), ("4",
                                                       3), ("5",
                                                            5), ("6",
                                                                 6), ("7", 7)]
    ]

    plans = align_capture_frame_sequences([complete, missing_four])

    assert plans[0] == [str(index) for index in range(8)]
    assert plans[1] == ["1", "2", "3", "4", None, "5", "6", "7"]


def test_align_capture_sequences_does_not_require_shared_file_indices():
    first = [_frame(str(index), index) for index in range(4)]
    resumed = [
        _frame(str(index), second)
        for index, second in zip(range(9, 13), range(4))
    ]

    plans = align_capture_frame_sequences([first, resumed])

    assert plans == [["0", "1", "2", "3"], ["9", "10", "11", "12"]]


def test_align_capture_sequences_rejects_unrelated_camera_epoch():
    reference = [_frame("0", 0), _frame("1", 1)]
    unrelated = [_frame("8", 5), _frame("9", 6)]

    with pytest.raises(ValueError, match="start skew"):
        align_capture_frame_sequences([reference, unrelated])


def test_align_capture_sequences_rejects_too_many_missing_slots():
    complete = [_frame(str(index), index) for index in range(6)]
    incomplete = [_frame("0", 0), _frame("4", 4), _frame("5", 5)]

    with pytest.raises(ValueError, match="missing slots"):
        align_capture_frame_sequences([complete, incomplete])


def test_align_rejects_extreme_slot_before_allocating_plan():
    reference = [_frame(str(index), index) for index in range(4)]
    corrupt = [_frame("0", 0), _frame("1", 1), _frame("2", 59)]

    with pytest.raises(ValueError, match="missing slots"):
        align_capture_frame_sequences([reference, corrupt])


def test_align_uses_device_time_for_all_frames_when_cap_time_is_partial():
    first = [(str(index), {
        "capTime": f"2026-07-11 01:00:0{index}:000000",
        "timestamp": index,
        "timestamp_frequency": 1,
    }) for index in range(3)]
    second = [("7", {
        "capTime": "2026-07-11 01:00:00:000000",
        "timestamp": 0,
        "timestamp_frequency": 1,
    }), ("8", {
        "timestamp": 1,
        "timestamp_frequency": 1,
    }),
              ("9", {
                  "capTime": "2026-07-11 01:00:02:000000",
                  "timestamp": 2,
                  "timestamp_frequency": 1,
              })]

    assert align_capture_frame_sequences([first, second]) == [["0", "1", "2"],
                                                              ["7", "8", "9"]]


def test_align_rejects_sequences_without_comparable_timestamps():
    with pytest.raises(ValueError, match="timestamps are incomplete"):
        align_capture_frame_sequences([[('0', {}), ('1', {})],
                                       [('0', {}), ('1', {})]])

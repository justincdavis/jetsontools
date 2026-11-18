# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Filtering and named windows over the timestamps of the recordings."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import pytest

from jetsontools import TegraData

if TYPE_CHECKING:
    from tests.logs._helpers import Recording


def _times(data: TegraData) -> list[float]:
    return [float(entry["timestamp"]) for entry in data.data]


def _swap(value: str) -> int:
    return int(value.split("/", maxsplit=1)[0])


def test_filter_everything(data: TegraData) -> None:
    """A range around the whole recording keeps every entry."""
    times = _times(data)
    data.filter([(times[0] - 1, times[-1] + 1)])
    assert data.filtered == data.data
    assert data.filtered_entries is not None
    assert len(data.filtered_entries) == 1


def test_filter_sub_range(data: TegraData) -> None:
    """Range bounds are inclusive and select the entries between them."""
    times = _times(data)
    low, high = len(times) // 4, len(times) // 2
    data.filter([(times[low], times[high])])
    assert data.filtered == data.data[low : high + 1]
    assert len(data) == len(times)


def test_filter_between_samples_is_empty(data: TegraData) -> None:
    """A range that falls between two samples selects nothing."""
    times = _times(data)
    middle = len(times) // 2
    gap = (times[middle] + 1e-6, times[middle + 1] - 1e-6)
    data.filter([gap])
    assert data.filtered == []


def test_filter_outside_is_empty(data: TegraData) -> None:
    """Ranges before the first and after the last sample select nothing."""
    times = _times(data)
    data.filter([(times[0] - 10, times[0] - 5), (times[-1] + 5, times[-1] + 10)])
    assert data.filtered == []
    assert data.filtered_entries is not None
    assert [entries for _, entries in data.filtered_entries] == [[], []]


def test_filter_no_ranges(data: TegraData) -> None:
    """No ranges selects nothing."""
    data.filter([])
    assert data.filtered == []
    assert data.filtered_entries == []


def test_filter_multiple_ranges(data: TegraData) -> None:
    """Overlapping ranges give each entry once, per-range entries stay separate."""
    times = _times(data)
    data.filter([(times[2], times[6]), (times[4], times[9]), (times[-3], times[-1])])
    assert data.filtered == data.data[2:10] + data.data[-3:]
    assert data.filtered_entries is not None
    assert [len(entries) for _, entries in data.filtered_entries] == [5, 6, 3]


def test_filter_changes_metrics(data: TegraData) -> None:
    """Metrics are computed from the filtered entries only."""
    times = _times(data)
    swap = data.parse(["SWAP"], _swap)["SWAP"].raw
    data.filter([(times[3], times[8])])
    assert data.parse(["SWAP"], _swap)["SWAP"].raw == swap[3:9]


def test_filter_replaced_by_next_filter(data: TegraData) -> None:
    """Filtering again replaces the previous filter."""
    times = _times(data)
    data.filter([(times[0], times[2])])
    data.filter([(times[5], times[6])])
    assert data.filtered == data.data[5:7]


def test_window_whole_recording_equals_data(data: TegraData) -> None:
    """A window covering the recording has the same entries and powerdraw."""
    times = _times(data)
    data.windows = {"all": (times[0] - 1, times[-1] + 1)}
    window = data.window("all")
    assert window.data == data.data
    assert len(window) == len(data)
    assert window.span == (times[0] - 1, times[-1] + 1)
    assert window.duration == pytest.approx(times[-1] - times[0] + 2)
    assert (
        window.parse(["SWAP"], _swap)["SWAP"].raw
        == data.parse(["SWAP"], _swap)["SWAP"].raw
    )


def test_window_sub_range(data: TegraData) -> None:
    """A window holds the entries between its start and stop."""
    times = _times(data)
    first, last = len(times) // 4, len(times) // 2
    data.windows = {"part": (times[first] - 1e-6, times[last] + 1e-6)}
    window = data.window("part")
    assert window.data == data.data[first : last + 1]
    assert len(window) == last - first + 1


def test_window_leaves_parent_unchanged(data: TegraData) -> None:
    """Taking a window neither alters the data nor its filter."""
    times = _times(data)
    before = copy.deepcopy(data.data)
    data.windows = {"part": (times[1], times[3])}
    data.filter([(times[5], times[7])])
    filtered = list(data.filtered or [])
    window = data.window("part")
    assert window.filtered is None
    assert data.data == before
    assert data.filtered == filtered
    assert data.span is None


def test_window_ignores_filter(data: TegraData) -> None:
    """A window uses all of the data, regardless of the filter."""
    times = _times(data)
    data.windows = {"part": (times[1], times[3])}
    data.filter([(times[8], times[9])])
    assert data.window("part").data == data.data[1:4]


def test_window_filter_within_window(data: TegraData) -> None:
    """Filtering a window narrows it further."""
    times = _times(data)
    data.windows = {"part": (times[1], times[8])}
    window = data.window("part")
    window.filter([(times[2], times[3])])
    assert window.filtered == data.data[2:4]
    assert len(window) == 8


def test_window_unknown_name(data: TegraData) -> None:
    """An unknown window raises KeyError naming the known windows."""
    data.windows = {"known": (0.0, 1.0)}
    with pytest.raises(KeyError, match="known"):
        data.window("unknown")


def test_window_without_entries(data: TegraData) -> None:
    """A window holding no samples raises ValueError."""
    times = _times(data)
    data.windows = {"gap": (times[2] + 1e-6, times[3] - 1e-6)}
    with pytest.raises(ValueError, match="gap"):
        data.window("gap")


def test_windows_from_constructor(recording: Recording) -> None:
    """Windows given on construction are used by window."""
    times = _times(TegraData(recording.path))
    windows = {"start": (times[0], times[4]), "end": (times[-5], times[-1])}
    data = TegraData(recording.path, windows=windows)
    assert data.windows == windows
    assert data.window("start").data == data.data[:5]
    assert data.window("end").data == data.data[-5:]

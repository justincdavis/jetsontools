# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Every recording parses, in order and without loss."""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING

import pytest

from jetsontools import TegraData, parse_tegrastats
from tests.logs._helpers import RECORDINGS_PER_BOARD, XAVIER_AGX

if TYPE_CHECKING:
    from tests.logs._helpers import Recording


def test_recordings_found() -> None:
    """Every board has both an all and a basic recording."""
    assert RECORDINGS_PER_BOARD
    for board, kinds in RECORDINGS_PER_BOARD.items():
        assert kinds == {"all", "basic"}, board


def test_parses_without_warnings(
    recording: Recording, caplog: pytest.LogCaptureFixture
) -> None:
    """Parsing logs nothing above debug and raises no warnings."""
    with warnings.catch_warnings(), caplog.at_level(logging.INFO):
        warnings.simplefilter("error")
        entries = parse_tegrastats(recording.path)
    assert entries
    assert not caplog.records


def test_entry_per_line(recording: Recording, data: TegraData) -> None:
    """No line is dropped and entries is the number of samples."""
    assert len(data) == data.entries == len(data.data) == recording.lines


def test_timestamps_increase(data: TegraData) -> None:
    """Python timestamps are floats and strictly increase."""
    timestamps = [float(entry["timestamp"]) for entry in data.data]
    assert all(later > earlier for earlier, later in zip(timestamps, timestamps[1:]))


def test_duration(data: TegraData) -> None:
    """Duration is the time between the first and last sample."""
    first, last = float(data.data[0]["timestamp"]), float(data.data[-1]["timestamp"])
    assert data.duration == pytest.approx(last - first)
    assert 0.5 < data.duration < 2.0


def test_values_are_strings(data: TegraData) -> None:
    """The general purpose parser keeps every value as a nonempty string."""
    for entry in data.data:
        assert all(isinstance(key, str) and key for key in entry)
        assert all(isinstance(value, str) and value for value in entry.values())


def test_date_and_time(recording: Recording, data: TegraData) -> None:
    """Entries have DATE as MM-DD-YYYY and TIME as HH:MM:SS, except on Xavier AGX."""
    for entry in data.data:
        if recording.board == XAVIER_AGX:
            assert "DATE" not in entry
            assert "TIME" not in entry
            continue
        month, day, year = entry["DATE"].split("-")
        assert (len(month), len(day), len(year)) == (2, 2, 4)
        hour, minute, second = entry["TIME"].split(":")
        assert 0 <= int(hour) < 24
        assert 0 <= int(minute) < 60
        assert 0 <= int(second) < 61


def test_same_fields_every_sample(data: TegraData) -> None:
    """Every sample of a recording has the same fields."""
    assert {tuple(entry) for entry in data.data} == {tuple(data.data[0])}


def test_parsing_twice_is_equal(recording: Recording, data: TegraData) -> None:
    """Parsing from a path, a string path and an open file gives the same entries."""
    with recording.path.open() as handle:
        from_file = TegraData(handle).data
    assert TegraData(str(recording.path)).data == data.data == from_file

# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Exporting the recordings to csv."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

import pytest

from jetsontools import TegraData

if TYPE_CHECKING:
    from pathlib import Path

    from tests.logs._helpers import Recording


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def test_csv_round_trip(
    data: TegraData,
    tmp_path: Path,
) -> None:
    """The csv holds a header of the fields and a row per sample, values unchanged."""
    data.save_as_csv(tmp_path / "out.csv")
    header, rows = _read(tmp_path / "out.csv")
    assert header == list(data.data[0])
    assert rows == data.data


def test_csv_accepts_str_path(
    data: TegraData,
    tmp_path: Path,
) -> None:
    """A str path writes the same csv as a Path."""
    data.save_as_csv(str(tmp_path / "str.csv"))
    data.save_as_csv(tmp_path / "path.csv")
    assert (tmp_path / "str.csv").read_bytes() == (tmp_path / "path.csv").read_bytes()


def test_csv_of_filtered_data(
    data: TegraData,
    tmp_path: Path,
) -> None:
    """Only the filtered samples are written."""
    times = [float(entry["timestamp"]) for entry in data.data]
    data.filter([(times[3], times[9])])
    data.save_as_csv(tmp_path / "filtered.csv")
    _, rows = _read(tmp_path / "filtered.csv")
    assert rows == data.data[3:10]


def test_csv_of_window(recording: Recording, tmp_path: Path) -> None:
    """A window writes only its own samples and re-parses to the same data."""
    full = TegraData(recording.path)
    times = [float(entry["timestamp"]) for entry in full.data]
    full.windows = {"part": (times[2], times[6])}
    full.window("part").save_as_csv(tmp_path / "window.csv")
    _, rows = _read(tmp_path / "window.csv")
    assert rows == full.data[2:7]


def test_csv_overwrites(
    data: TegraData,
    tmp_path: Path,
) -> None:
    """Saving over an existing file replaces it."""
    target = tmp_path / "out.csv"
    target.write_text("stale\n" * 1000)
    data.save_as_csv(target)
    header, rows = _read(target)
    assert header == list(data.data[0])
    assert len(rows) == len(data)


def test_csv_without_data_raises(data: TegraData, tmp_path: Path) -> None:
    """A filter which selects nothing has no data to save, so it raises."""
    times = [float(entry["timestamp"]) for entry in data.data]
    data.filter([(times[-1] + 5, times[-1] + 10)])
    with pytest.raises(ValueError, match="No data to save"):
        data.save_as_csv(tmp_path / "empty.csv")
    assert not (tmp_path / "empty.csv").exists()

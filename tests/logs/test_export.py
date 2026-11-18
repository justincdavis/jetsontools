# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Exporting the recordings to csv."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from jetsontools import TegraData
from tests.logs._helpers import UNSTABLE_KEYS, known_gap

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from tests.logs._helpers import Recording


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def test_csv_round_trip(
    request: pytest.FixtureRequest,
    recording: Recording,
    data: TegraData,
    tmp_path: Path,
) -> None:
    """The csv holds a header of the fields and a row per sample, values unchanged."""
    known_gap(request, recording, UNSTABLE_KEYS, kind="all")
    data.save_as_csv(tmp_path / "out.csv")
    header, rows = _read(tmp_path / "out.csv")
    assert header == list(data.data[0])
    assert rows == data.data


def test_csv_accepts_str_path(
    request: pytest.FixtureRequest,
    recording: Recording,
    data: TegraData,
    tmp_path: Path,
) -> None:
    """A str path writes the same csv as a Path."""
    known_gap(request, recording, UNSTABLE_KEYS, kind="all")
    data.save_as_csv(str(tmp_path / "str.csv"))
    data.save_as_csv(tmp_path / "path.csv")
    assert (tmp_path / "str.csv").read_bytes() == (tmp_path / "path.csv").read_bytes()


def test_csv_of_filtered_data(
    request: pytest.FixtureRequest,
    recording: Recording,
    data: TegraData,
    tmp_path: Path,
) -> None:
    """Only the filtered samples are written."""
    known_gap(request, recording, UNSTABLE_KEYS, kind="all")
    times = [float(entry["timestamp"]) for entry in data.data]
    data.filter([(times[3], times[9])])
    data.save_as_csv(tmp_path / "filtered.csv")
    _, rows = _read(tmp_path / "filtered.csv")
    assert rows == data.data[3:10]


def test_csv_of_window(
    request: pytest.FixtureRequest, recording: Recording, tmp_path: Path
) -> None:
    """A window writes only its own samples and re-parses to the same data."""
    known_gap(request, recording, UNSTABLE_KEYS, kind="all")
    full = TegraData(recording.path)
    times = [float(entry["timestamp"]) for entry in full.data]
    full.windows = {"part": (times[2], times[6])}
    full.window("part").save_as_csv(tmp_path / "window.csv")
    _, rows = _read(tmp_path / "window.csv")
    assert rows == full.data[2:7]


def test_csv_overwrites(
    request: pytest.FixtureRequest,
    recording: Recording,
    data: TegraData,
    tmp_path: Path,
) -> None:
    """Saving over an existing file replaces it."""
    known_gap(request, recording, UNSTABLE_KEYS, kind="all")
    target = tmp_path / "out.csv"
    target.write_text("stale\n" * 1000)
    data.save_as_csv(target)
    header, rows = _read(target)
    assert header == list(data.data[0])
    assert len(rows) == len(data)

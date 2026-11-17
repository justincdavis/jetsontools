# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""DLA utilization, which tegrastats only reports on Orin when run with sudo."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from jetsontools import get_dla_utilization
from tests.logs._helpers import load

if TYPE_CHECKING:
    from jetsontools import TegraData
    from tests.logs._helpers import Recording

DLA = re.compile(r"NVDLA\d+")


def _found(data: TegraData) -> list[str]:
    return sorted(name for name in data.data[0] if DLA.fullmatch(name))


def _has_dla(data: TegraData) -> bool:
    return bool(_found(data))


def test_dla_fields_only_in_orin_sudo(recording: Recording, data: TegraData) -> None:
    """NVDLA fields are only reported by Orin sudo recordings, as NVDLA0 and NVDLA1."""
    found = _found(data)
    if not (recording.orin and recording.sudo):
        assert found == []
    else:
        assert found in ([], ["NVDLA0", "NVDLA1"])


@pytest.mark.parametrize(
    ("name", "kind"), [("orinagx_64gb", "all"), ("orinnx_16gb", "all")]
)
def test_orin_sudo_reports_both_cores(name: str, kind: str) -> None:
    """The Orin AGX 64GB and Orin NX recordings have both DLA cores."""
    assert _found(load(name, kind)) == ["NVDLA0", "NVDLA1"]


def test_orin_agx_32gb_has_no_dla_fields() -> None:
    """The older Orin AGX 32GB tegrastats does not report NVDLA at all."""
    data = load("orinagx_32gb", "all")
    assert _found(data) == []
    assert data.dla_utilization == {}


def test_dla_utilization_keys(data: TegraData) -> None:
    """dla_utilization reports each NVDLA core in the data, and is empty without."""
    assert list(data.dla_utilization) == _found(data)
    assert data.dla_utilization.keys() == get_dla_utilization(data.data).keys()


def test_dla_utilization_values(data: TegraData) -> None:
    """Each core has a utilization percentage per sample."""
    if not _has_dla(data):
        pytest.skip("No DLA fields in this recording")
    for name, metric in data.dla_utilization.items():
        assert len(metric.raw) == len(data), name
        assert all(0 <= value <= 100 for value in metric.raw), name
        assert metric.min <= metric.mean <= metric.max


def test_off_is_zero_utilization(data: TegraData) -> None:
    """A core reported off has utilization 0, and a busy core its percentage."""
    if not _has_dla(data):
        pytest.skip("No DLA fields in this recording")
    for name, metric in data.dla_utilization.items():
        for entry, value in zip(data.data, metric.raw):
            raw = entry[name]
            expected = 0.0 if raw == "off" else float(raw.split("%")[0])
            assert value == expected


def test_dla_utilization_follows_filter_and_window(data: TegraData) -> None:
    """The metrics cover only the filtered entries or the window's entries."""
    if not _has_dla(data):
        pytest.skip("No DLA fields in this recording")
    times = [float(entry["timestamp"]) for entry in data.data]
    data.windows = {"part": (times[5], times[14])}
    assert all(len(m.raw) == 10 for m in data.window("part").dla_utilization.values())
    data.filter([(times[0], times[3])])
    assert all(len(m.raw) == 4 for m in data.dla_utilization.values())
    assert all(len(m.raw) == len(data) for m in get_dla_utilization(data.data).values())

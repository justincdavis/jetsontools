# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import io

import pytest

from jetsontools import TegraData, get_dla_utilization, parse_tegrastats
from tests.sysfs._helpers import LOGS, SUDO_LINE


def test_dla_utilization() -> None:
    lines = [
        SUDO_LINE.format(dla0="off", dla1="off"),
        SUDO_LINE.format(dla0="off", dla1="66%@1600"),
        SUDO_LINE.format(dla0="off", dla1="54%@1600"),
        SUDO_LINE.format(dla0="off", dla1="0%@1600"),
    ]
    utilization = get_dla_utilization(parse_tegrastats(io.StringIO("\n".join(lines))))
    assert list(utilization) == ["NVDLA0", "NVDLA1"]
    assert utilization["NVDLA0"].raw == [0.0, 0.0, 0.0, 0.0]
    assert utilization["NVDLA1"].raw == [0.0, 66.0, 54.0, 0.0]


def test_dla_utilization_window() -> None:
    lines = [
        f"{ts}::{SUDO_LINE.format(dla0=dla0, dla1='off')}"
        for ts, dla0 in (
            (1.0, "off"),
            (2.0, "40%@1600"),
            (3.0, "60%@1600"),
            (4.0, "off"),
        )
    ]
    data = TegraData(io.StringIO("\n".join(lines)), windows={"busy": (1.5, 3.5)})
    assert data.dla_utilization["NVDLA0"].mean == 25.0
    assert data.window("busy").dla_utilization["NVDLA0"].mean == 50.0
    data.filter([(1.5, 3.5)])
    assert data.dla_utilization["NVDLA0"].mean == 50.0


def test_dla_utilization_edge_cases() -> None:
    assert get_dla_utilization([]) == {}
    data = parse_tegrastats(io.StringIO(SUDO_LINE.format(dla0="1600", dla1="off")))
    with pytest.raises(ValueError, match="DLA utilization"):
        get_dla_utilization(data)
    recorded = TegraData(LOGS / "orinagx_64gb" / "all.tegrastats").dla_utilization
    assert sorted(recorded) == ["NVDLA0", "NVDLA1"]
    assert TegraData(LOGS / "orinagx_64gb" / "basic.tegrastats").dla_utilization == {}

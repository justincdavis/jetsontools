# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""The Xavier AGX format, which differs from the other boards."""

from __future__ import annotations

import io

import pytest

from jetsontools import TegraData, parse_tegrastats
from tests.logs._helpers import XAVIER_AGX, load

SAMPLE = (
    "RAM 2086/15825MB (lfb 2800x4MB) SWAP 0/7912MB (cached 0MB) "
    "CPU [0%@2265,33%@2265,0%@2265,0%@2265,0%@2265,0%@2265,0%@2265,0%@2265] "
    "EMC_FREQ 0%@2133 GR3D_FREQ 0%@905 APE 150 MTS fg 0% bg 3% AO@30C GPU@31C "
    "Tdiode@33C PMIC@50C AUX@30.5C CPU@32C thermal@30.95C Tboard@32C "
    "GPU 463/463 CPU 1236/1236 SOC 2318/2318 CV 0/0 VDDRQ 154/154 SYS5V 2934/2934"
)


def test_line_without_date_and_time() -> None:
    """The RAM field is parsed as RAM, and no DATE or TIME is made up."""
    entry = parse_tegrastats(io.StringIO(SAMPLE))[0]
    assert "DATE" not in entry
    assert "TIME" not in entry
    assert entry["RAM"] == "2086/15825MB"
    assert entry["LFB"] == "2800x4MB"


def test_timestamp_kept_without_date() -> None:
    """The Python timestamp is the only timestamp, and drives duration."""
    text = f"10.0::{SAMPLE}\n12.5::{SAMPLE}\n"
    data = TegraData(io.StringIO(text))
    assert [entry["timestamp"] for entry in data.data] == ["10.0", "12.5"]
    assert data.duration == pytest.approx(2.5)


def test_mts_has_stable_keys() -> None:
    """MTS fg and bg become MTS_FG and MTS_BG."""
    entry = parse_tegrastats(io.StringIO(SAMPLE))[0]
    assert entry["MTS_FG"] == "0%"
    assert entry["MTS_BG"] == "3%"
    assert "MTS" not in entry
    assert "0%" not in entry


def test_rails_keep_cpu_and_gpu_fields() -> None:
    """Rails in current/average form do not replace CPU cores or GR3D_FREQ."""
    entry = parse_tegrastats(io.StringIO(SAMPLE))[0]
    assert entry["CPU"].startswith("[")
    assert entry["GR3D_FREQ"] == "0%@905"
    assert entry["VDD_GPU"] == "463mW/463mW"
    assert entry["VDD_CPU"] == "1236mW/1236mW"
    assert entry["VDD_SOC"] == "2318mW/2318mW"
    assert entry["VDD_CV"] == "0mW/0mW"
    assert entry["VDDRQ"] == "154mW/154mW"
    assert entry["VIN_SYS5V"] == "2934mW/2934mW"
    assert entry["GPU_TEMP"] == "31C"
    assert entry["CPU_TEMP"] == "32C"


def test_recording_powerdraw() -> None:
    """Powerdraw includes every rail in mW, totals are plausible and consistent."""
    power = load(XAVIER_AGX, "all").powerdraw
    assert {"VDD_GPU", "VDD_CPU", "VDD_SOC", "VDD_CV", "VDDRQ", "VIN_SYS5V"} <= set(
        power
    )
    assert 1000 < power["VDD_TOTAL"].mean < 60000
    assert power["VIN_TOTAL"].raw == power["VIN_SYS5V"].raw
    assert power["VDD_SOC"].mean == pytest.approx(2318, rel=0.05)
    rails = ("VDD_GPU", "VDD_CPU", "VDD_SOC", "VDD_CV", "VDDRQ")
    for index, total in enumerate(power["VDD_TOTAL"].raw):
        assert total == sum(power[rail].raw[index] for rail in rails)


def test_recording_cpu_cores() -> None:
    """The Xavier AGX has eight cores, listed in CPU in every sample."""
    for kind in ("all", "basic"):
        for entry in load(XAVIER_AGX, kind).data:
            assert len(entry["CPU"][1:-1].split(",")) == 8

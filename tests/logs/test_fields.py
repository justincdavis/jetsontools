# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""The fields parsed from each recording, and their values."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from tests.logs._helpers import (
    TEMPERATURE,
    UNAVAILABLE_TEMPERATURE,
    load,
)

if TYPE_CHECKING:
    from jetsontools import TegraData
    from jetsontools._parsing import Metric
    from tests.logs._helpers import Recording

CORE_FIELDS = {"timestamp", "RAM", "LFB", "SWAP", "CACHED", "CPU", "GR3D_FREQ"}
RAILS = {
    "orinagx": {"VDD_GPU_SOC", "VDD_CPU_CV", "VIN_SYS_5V0", "VDDQ_VDD2_1V8AO"},
    "orinnx": {"VDD_IN", "VDD_CPU_GPU_CV", "VDD_SOC"},
    "xaviernx": {"VDD_IN", "VDD_CPU_GPU_CV", "VDD_SOC"},
    "xavieragx": {
        "VDD_GPU",
        "VDD_CPU",
        "VDD_SOC",
        "VDD_CV",
        "VDDRQ",
        "VIN_SYS5V",
    },
}
PERCENT = re.compile(r"(\d+)%")


def _percent(value: str) -> int:
    match = PERCENT.match(value)
    assert match, value
    return int(match.group(1))


def _consistent(metric: Metric) -> None:
    assert metric.min <= metric.median <= metric.max
    assert metric.min <= metric.mean <= metric.max
    assert metric.min == min(metric.raw)
    assert metric.max == max(metric.raw)


def test_core_fields(data: TegraData) -> None:
    """Every recording has the fields all tegrastats versions report."""
    assert set(data.data[0]) >= CORE_FIELDS
    assert "RAM" in data.data[0]


def test_sudo_has_more_fields(board: str) -> None:
    """The sudo recording of a board reports more fields than the basic one."""
    fields = {kind: set(load(board, kind).data[0]) for kind in ("all", "basic")}
    assert len(fields["all"]) > len(fields["basic"])


def test_rails_by_board(recording: Recording, data: TegraData) -> None:
    """Sudo recordings report the power rails of the board family."""
    family = recording.board.split("_")[0]
    if family not in RAILS:
        pytest.skip(f"No rails known for {family}")
    if not recording.sudo:
        pytest.skip("Rails are only reliably reported with sudo")
    assert RAILS[family] <= set(data.data[0])


def test_orin_and_xavier_rails_differ() -> None:
    """Orin AGX reports VIN_SYS_5V0, Orin NX and Xavier NX report VDD_IN."""
    agx, nx = load("orinagx_64gb", "all"), load("orinnx_16gb", "all")
    assert {"VIN_SYS_5V0", "VDD_GPU_SOC"} <= set(agx.data[0])
    assert "VDD_IN" not in agx.data[0]
    assert {"VDD_IN", "VDD_SOC"} <= set(nx.data[0])
    assert "VIN_SYS_5V0" not in nx.data[0]


def test_memory(data: TegraData) -> None:
    """RAM and SWAP are used/total in MB and used never exceeds total."""
    for entry in data.data:
        for name in ("RAM", "SWAP"):
            used, total = entry[name][:-2].split("/")
            assert 0 <= int(used) <= int(total) > 0
        assert re.fullmatch(r"\d+x4MB", entry["LFB"])
        assert re.fullmatch(r"\d+MB", entry["CACHED"])


def test_cpu(data: TegraData) -> None:
    """CPU is a bracketed list of per-core percentages, the same length each sample."""
    cores = set()
    for entry in data.data:
        value = entry["CPU"]
        assert value.startswith("[")
        assert value.endswith("]")
        utilization = [_percent(core) for core in value[1:-1].split(",")]
        assert all(0 <= percent <= 100 for percent in utilization)
        cores.add(len(utilization))
    assert len(cores) == 1
    assert cores.pop() >= 4


def test_gpu_and_emc_percent(data: TegraData) -> None:
    """GR3D_FREQ and EMC_FREQ lead with a utilization between 0 and 100."""
    for entry in data.data:
        for name in ("GR3D_FREQ", "EMC_FREQ"):
            if name in entry:
                assert 0 <= _percent(entry[name]) <= 100


def test_temperatures(data: TegraData) -> None:
    """Temperature fields are renamed to NAME_TEMP and hold plausible degrees C."""
    names = [name for name in data.data[0] if name.endswith("_TEMP")]
    assert {"CPU_TEMP", "GPU_TEMP"} <= set(names)
    for entry in data.data:
        for name in names:
            assert TEMPERATURE.fullmatch(entry[name]), (name, entry[name])
            degrees = float(entry[name][:-1])
            assert degrees == UNAVAILABLE_TEMPERATURE or 0 < degrees < 125


def test_parse_metric(data: TegraData) -> None:
    """Metrics from custom parse functions are consistent with their samples."""
    metrics = data.parse(
        ["SWAP", "CACHED"], lambda value: int(value.rstrip("MB").split("/")[0])
    )
    for metric in metrics.values():
        assert len(metric.raw) == len(data)
        _consistent(metric)


def test_powerdraw(recording: Recording, data: TegraData) -> None:
    """Power draw metrics are consistent, non-negative mW, and empty without rails."""
    rails = [name for name in data.data[0] if "VDD" in name or "VIN" in name]
    power = data.powerdraw
    if not rails:
        assert power == {}
        return
    assert set(rails) <= set(power)
    for metric in power.values():
        assert len(metric.raw) == len(data)
        assert metric.min >= 0
        _consistent(metric)
    if recording.sudo:
        assert power["VDD_TOTAL"].mean > 100


def test_powerdraw_totals(data: TegraData) -> None:
    """VDD_TOTAL and VIN_TOTAL are the per-sample sums of their rails."""
    power = data.powerdraw
    if "VDD_TOTAL" not in power:
        pytest.skip("No rails reported")
    vdd = [
        metric.raw
        for name, metric in power.items()
        if "VDD" in name and name != "VDD_IN" and not name.endswith("_TOTAL")
    ]
    assert power["VDD_TOTAL"].raw == [sum(sample) for sample in zip(*vdd)]
    if "VIN_TOTAL" in power:
        vin = [
            metric.raw
            for name, metric in power.items()
            if "VIN" in name and not name.endswith("_TOTAL")
        ]
        assert power["VIN_TOTAL"].raw == [sum(sample) for sample in zip(*vin)]


def test_known_sample() -> None:
    """The first sample of the Orin AGX 64GB sudo recording."""
    entry = load("orinagx_64gb", "all").data[0]
    assert entry["RAM"] == "25620/62841MB"
    assert entry["SWAP"] == "0/31421MB"
    assert entry["VDD_GPU_SOC"] == "5191mW/5191mW"

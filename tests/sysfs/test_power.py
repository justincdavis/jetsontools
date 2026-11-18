# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import io
import time
from pathlib import Path

import pytest

from jetsontools import TegraData, TegraStats
from jetsontools._sysfs import _flag_readers
from tests.sysfs._helpers import POWER_LOG, _fake_tegrastats, _ina3221, _tegrastats_log


def test_power_readers(tmp_path: Path) -> None:
    _ina3221(
        tmp_path,
        "1-0040",
        {
            "in1_label": "VDD_GPU_SOC",
            "in1_input": 19968,
            "curr1_input": 160,
            "in2_label": "VDD_CPU_CV",
            "in2_input": 19976,
            "curr2_input": 60,
            "in4_label": "",
            "in4_input": 320,
            "curr4_input": 300,
            "in7_label": "sum of shunt voltages",
            "in7_input": 520,
        },
    )
    _ina3221(
        tmp_path,
        "1-0041",
        {"in2_label": "VDDQ_VDD2_1V8AO", "in2_input": 5016, "curr2_input": 120},
    )
    readers = _flag_readers("power")
    assert [(r.name, Path(r.path).name, r.kind, r.interval) for r in readers] == [
        ("VDD_GPU_SOC.mV", "in1_input", "gauge", 50.0),
        ("VDD_GPU_SOC.mA", "curr1_input", "gauge", 50.0),
        ("VDD_CPU_CV.mV", "in2_input", "gauge", 50.0),
        ("VDD_CPU_CV.mA", "curr2_input", "gauge", 50.0),
        ("VDDQ_VDD2_1V8AO.mV", "in2_input", "gauge", 50.0),
        ("VDDQ_VDD2_1V8AO.mA", "curr2_input", "gauge", 50.0),
    ]


@pytest.mark.parametrize(
    ("rails", "tegrastats_interval", "expected"),
    [
        (4, 1000.0, 50.0),
        (6, 1000.0, 12000 / 188),
        (4, 100.0, 8000 / 120),
        (4, 50.0, 200.0),
        (4, 40.0, 1000.0),
    ],
)
def test_power_readers_rate_limit(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    rails: int,
    tegrastats_interval: float,
    expected: float,
) -> None:
    files: dict[str, object] = {}
    for channel in range(1, rails + 1):
        files.update(
            {
                f"in{channel}_label": f"RAIL{channel}",
                f"in{channel}_input": 5000,
                f"curr{channel}_input": 100,
            }
        )
    _ina3221(tmp_path, "1-0040", files)
    readers = _flag_readers("power", tegrastats_interval)
    assert len(readers) == 2 * rails
    assert [r.interval for r in readers] == pytest.approx([expected] * 2 * rails)
    reads = 2 * rails * 1000 * (1 / tegrastats_interval + 1 / expected)
    assert (reads <= 200.0 + 1e-9) == ("once per second" not in caplog.text)


def test_sysfs_energy() -> None:
    data = TegraData(
        io.StringIO(_tegrastats_log([1.0, 2.0, 3.0, 4.0])),
        windows={"middle": (1.5, 3.5)},
        sysfs=io.StringIO(POWER_LOG),
    )
    assert data.sysfs_energy == pytest.approx(
        {"VDD_GPU_SOC": 12000.0, "VIN_SYS_5V0": 3000.0, "TOTAL": 15000.0}
    )
    assert data.window("middle").sysfs_energy == pytest.approx(
        {"VDD_GPU_SOC": 8000.0, "VIN_SYS_5V0": 2000.0, "TOTAL": 10000.0}
    )
    data.filter([(1.0, 2.0), (3.0, 4.0)])
    assert data.sysfs_energy["VDD_GPU_SOC"] == pytest.approx(8000.0)
    assert data.sysfs_gauges["VDD_GPU_SOC.mA"].raw == [100.0, 100.0, 300.0, 300.0]


def test_sysfs_energy_voltage_alignment() -> None:
    log = (
        "#SYSFS R.mV gauge 1.0 /a\n#SYSFS R.mA gauge 1.0 /b\n"
        "0.5::R.mV 20000\n2.5::R.mV 10000\n"
        "1.0::R.mA 100\n2.0::R.mA 100\n3.0::R.mA 100\n"
    )
    data = TegraData(io.StringIO(_tegrastats_log([1.0, 3.0])), sysfs=io.StringIO(log))
    assert data.sysfs_energy == pytest.approx({"R": 3500.0, "TOTAL": 3500.0})


def test_tegrastats_read_sysfs_power(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_tegrastats(tmp_path, monkeypatch)
    _ina3221(
        tmp_path,
        "1-0040",
        {"in1_label": "VDD_GPU_SOC", "in1_input": 20000, "curr1_input": 100},
    )

    def no_probe(paths: list[str], _: float) -> list[float]:
        assert paths == []
        return []

    monkeypatch.setattr("jetsontools._sysfs._probe_intervals", no_probe)
    tegrastats = TegraStats(interval=50, read_sysfs_power=True)
    assert [(r.name, r.interval) for r in tegrastats.sysfs] == [
        ("VDD_GPU_SOC.mV", 50.0),
        ("VDD_GPU_SOC.mA", 50.0),
    ]
    with tegrastats:
        time.sleep(0.15)
        with tegrastats.window("w"):
            time.sleep(0.3)
        time.sleep(0.15)
    window = tegrastats.data.window("w")
    assert window.sysfs_energy["VDD_GPU_SOC"] == pytest.approx(
        2000.0 * window.duration, rel=1e-6
    )

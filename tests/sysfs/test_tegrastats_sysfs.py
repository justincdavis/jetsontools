# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import logging
import time
from pathlib import Path

import pytest

from jetsontools import SysfsReader, TegraData, TegraStats
from tests.sysfs._helpers import ACTIVE, _devices, _fake_tegrastats, _set


def test_tegrastats_sysfs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_tegrastats(tmp_path, monkeypatch)
    counter, gauge = tmp_path / "counter", tmp_path / "gauge"
    _set(counter, 100)
    _set(gauge, 5)
    output = tmp_path / "run.tegrastats"
    tegrastats = TegraStats(
        output=output,
        interval=50,
        sysfs=[
            SysfsReader("busy", str(counter), "counter"),
            SysfsReader("temp", str(gauge), interval=10),
        ],
    )
    assert [(r.name, r.interval) for r in tegrastats.sysfs] == [
        ("busy", 50.0),
        ("temp", 10.0),
    ]
    with tegrastats:
        with tegrastats.window("idle"):
            time.sleep(0.3)
        with tegrastats.window("busy"):
            for value in range(110, 410, 10):
                _set(counter, value)
                _set(gauge, value)
                time.sleep(0.01)
            time.sleep(0.05)
        time.sleep(0.1)
    data = tegrastats.data
    assert data.window("idle").sysfs_counters == {"busy": 0.0}
    assert data.window("busy").sysfs_counters == {"busy": 300.0}
    assert data.sysfs_counters == {"busy": 300.0}
    gauges = data.window("busy").sysfs_gauges["temp"]
    assert gauges.max == 400.0
    assert len(gauges.raw) > 5
    assert data.powerdraw["VDD_GPU_SOC"].mean == 4392.0

    saved = TegraData(output, windows=data.windows, sysfs=f"{output}.sysfs")
    assert saved.window("busy").sysfs_counters == {"busy": 300.0}
    csv = tmp_path / "run.csv"
    saved.save_as_csv(csv)
    assert "VDD_GPU_SOC" in csv.read_text()


def test_tegrastats_read_sysfs_dla(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_tegrastats(tmp_path, monkeypatch)
    _devices(tmp_path, {"15880000.nvdla0": ACTIVE, "158c0000.nvdla1": ACTIVE})
    counter = tmp_path / "devices" / "158c0000.nvdla1" / ACTIVE
    _set(counter, 200)
    tegrastats = TegraStats(interval=50, read_sysfs_dla=True)
    assert [r.name for r in tegrastats.sysfs] == ["nvdla0", "nvdla1"]
    with tegrastats, tegrastats.window("dla1"):
        for value in range(220, 520, 20):
            _set(counter, value)
            time.sleep(0.01)
    window = tegrastats.data.window("dla1")
    assert window.sysfs_counters == {"nvdla0": 0.0, "nvdla1": 300.0}


def test_tegrastats_sysfs_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _fake_tegrastats(tmp_path, monkeypatch)
    with caplog.at_level(logging.WARNING):
        tegrastats = TegraStats(
            interval=50,
            read_sysfs_dla=True,
            read_sysfs_media=True,
            sysfs=[SysfsReader("gone", str(tmp_path / "gone"))],
        )
    for name in ("read_sysfs_dla", "read_sysfs_media", "gone"):
        assert name in caplog.text
    assert tegrastats.sysfs == []
    with tegrastats, tegrastats.window("w"):
        time.sleep(0.3)
    data = tegrastats.data
    assert data.entries > 0
    assert data.window("w").sysfs_counters == {}


def test_tegrastats_sysfs_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_tegrastats(tmp_path, monkeypatch)

    def fail(*_: object) -> None:
        raise AssertionError

    monkeypatch.setattr("jetsontools._sysfs._read", fail)
    monkeypatch.setattr("jetsontools._tegrastats._flag_readers", fail)
    output = tmp_path / "run.tegrastats"
    tegrastats = TegraStats(output=output, interval=50)
    with tegrastats, tegrastats.window("w"):
        time.sleep(0.3)
    assert not Path(f"{output}.sysfs").exists()
    data = tegrastats.data
    assert data.entries > 0
    assert data.sysfs_counters == {}


def test_tegrastats_sysfs_unique_names(tmp_path: Path) -> None:
    (tmp_path / "a").write_text("1\n")
    reader = SysfsReader("a", str(tmp_path / "a"), interval=10)
    with pytest.raises(ValueError, match="unique"):
        TegraStats(sysfs=[reader, reader])


def test_tegrastats_sysfs_tempfile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_tegrastats(tmp_path, monkeypatch)
    counter = tmp_path / "counter"
    _set(counter, 0)
    tegrastats = TegraStats(
        interval=50, sysfs=[SysfsReader("c", str(counter), "counter", interval=5)]
    )
    with tegrastats, tegrastats.window("w"):
        _set(counter, 42)
        time.sleep(0.1)
    assert tegrastats.data.window("w").sysfs_counters == {"c": 42.0}

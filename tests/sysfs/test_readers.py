# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import logging
import multiprocessing as mp
import time
import types
from typing import TYPE_CHECKING

import pytest

from jetsontools import SysfsReader, get_dla_active_time
from jetsontools._sysfs import (
    _flag_readers,
    _parse_sysfs,
    _probe_intervals,
    _resolve,
    _sample,
)
from tests.sysfs._helpers import ACTIVE, _devices, _set

if TYPE_CHECKING:
    from pathlib import Path


def test_reader_validation() -> None:
    with pytest.raises(ValueError, match="name"):
        SysfsReader("bad name", "/sys/x")
    with pytest.raises(ValueError, match="kind"):
        SysfsReader("x", "/sys/x", "rate")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="interval"):
        SysfsReader("x", "/sys/x", interval=0)


def test_flag_readers(tmp_path: Path) -> None:
    _devices(
        tmp_path,
        {
            "15880000.nvdla0": ACTIVE,
            "158c0000.nvdla1": ACTIVE,
            "17000000.gpu": ACTIVE,
            "16000000.pva0": ACTIVE,
            "15340000.vic": ACTIVE,
            "154c0000.nvenc": ACTIVE,
            "15480000.nvdec": ACTIVE,
            "15380000.nvjpg": ACTIVE,
            "15540000.nvjpg": ACTIVE,
            "15a50000.ofa": ACTIVE,
            "15480000.nvdec:ctx0": ACTIVE,
        },
    )
    names = {
        flag: [(r.name, r.kind) for r in _flag_readers(flag)]
        for flag in ("dla", "gpu", "pva", "media")
    }
    assert names == {
        "dla": [("nvdla0", "counter"), ("nvdla1", "counter")],
        "gpu": [("gpu", "counter")],
        "pva": [("pva0", "counter")],
        "media": [
            ("vic", "counter"),
            ("nvenc", "counter"),
            ("nvdec", "counter"),
            ("nvjpg", "counter"),
            ("nvjpg1", "counter"),
            ("ofa", "counter"),
        ],
    }
    assert _flag_readers("gpu")[0].path.endswith("17000000.gpu/" + ACTIVE)


def test_no_devices() -> None:
    for flag in ("dla", "gpu", "pva", "media", "power"):
        assert _flag_readers(flag) == []
    assert get_dla_active_time() == {}


def test_get_dla_active_time(tmp_path: Path) -> None:
    _devices(tmp_path, {"15880000.nvdla0": ACTIVE, "158c0000.nvdla1": ACTIVE})
    _set(tmp_path / "devices" / "158c0000.nvdla1" / ACTIVE, 200)
    assert get_dla_active_time() == {"nvdla0": 100, "nvdla1": 200}
    (tmp_path / "devices" / "15880000.nvdla0" / ACTIVE).write_text("x")
    assert get_dla_active_time() == {"nvdla1": 200}


def test_probe_intervals(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]

    def perf_counter() -> float:
        clock[0] += 0.0001
        return clock[0]

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    values = {
        "static": lambda: "5",
        "every_10ms": lambda: str(int(clock[0] / 0.01)),
        "every_25ms": lambda: str(int(clock[0] / 0.025)),
        "every_read": lambda: str(clock[0]),
    }
    monkeypatch.setattr(
        "jetsontools._sysfs.time",
        types.SimpleNamespace(perf_counter=perf_counter, sleep=sleep),
    )
    monkeypatch.setattr("jetsontools._sysfs._read", lambda path: values[path]())
    static, every_10ms, every_25ms, every_read = _probe_intervals(list(values), 1000.0)
    assert static == 1000.0
    assert every_10ms == pytest.approx(10.0, abs=1.5)
    assert every_25ms == pytest.approx(25.0, abs=1.5)
    assert 1.0 <= every_read <= 2.0
    assert _probe_intervals(["every_25ms"], 20.0) == [20.0]
    start = clock[0]
    assert _probe_intervals([], 20.0) == []
    assert clock[0] == start


def test_resolve(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").write_text("1\n")
    (tmp_path / "b").write_text("2\n")
    (tmp_path / "text").write_text("on\n")
    probed: list[list[str]] = []

    def probe(paths: list[str], ceiling: float) -> list[float]:
        probed.append(paths)
        return [min(3.0, ceiling)] * len(paths)

    monkeypatch.setattr("jetsontools._sysfs._probe_intervals", probe)
    readers = [
        SysfsReader("one", str(tmp_path / "a"), interval=7.0),
        SysfsReader("glob", str(tmp_path / "[b]"), "counter"),
        SysfsReader("gauge", str(tmp_path / "a")),
        SysfsReader("many", str(tmp_path / "[ab]")),
        SysfsReader("missing", str(tmp_path / "missing")),
        SysfsReader("text", str(tmp_path / "text")),
    ]
    with caplog.at_level(logging.WARNING):
        resolved = _resolve(readers, 25.0)
    assert [(r.name, r.path, r.kind, r.interval) for r in resolved] == [
        ("one", str(tmp_path / "a"), "gauge", 7.0),
        ("glob", str(tmp_path / "b"), "counter", 25.0),
        ("gauge", str(tmp_path / "a"), "gauge", 3.0),
    ]
    assert probed == [[str(tmp_path / "a")]]
    for name in ("many", "missing", "text"):
        assert name in caplog.text


def test_sample(tmp_path: Path) -> None:
    fast, slow = tmp_path / "fast", tmp_path / "slow"
    _set(fast, 1)
    _set(slow, 2)
    readers = [
        SysfsReader("fast", str(fast), "counter", interval=5.0),
        SysfsReader("slow", str(slow), interval=50.0),
    ]
    output = tmp_path / "samples.sysfs"
    output.write_text("")
    context = mp.get_context("fork")
    ready, stop = context.Event(), context.Event()
    process = context.Process(target=_sample, args=(readers, output, ready, stop))
    process.start()
    assert ready.wait(5)
    time.sleep(0.3)
    _set(fast, 3)
    time.sleep(0.05)
    stop.set()
    process.join(5)
    assert process.exitcode == 0
    _, series = _parse_sysfs(output)
    times, values = series["fast"]
    assert 20 <= len(times) <= 120
    assert values[0] == 1.0
    assert values[-1] == 3.0
    assert 3 <= len(series["slow"][0]) <= 15
    assert times == sorted(times)

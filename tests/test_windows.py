# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import io
import os
import time
from typing import TYPE_CHECKING

import pytest

from jetsontools import TegraData, TegraStats

if TYPE_CHECKING:
    from pathlib import Path

LINE = (
    "11-15-2026 23:40:40 GR3D_FREQ {util}% gpu@42.25C VDD_GPU_SOC {gpu}mW/{gpu}mW "
    "VDD_CPU_CV 2000mW/2000mW VIN_SYS_5V0 4000mW/4000mW"
)
SAMPLES = {
    1.0: (0, 3000),
    1.5: (0, 3000),
    2.0: (0, 3000),
    3.0: (99, 9000),
    3.5: (99, 11000),
    4.0: (99, 10000),
}
WINDOWS = {"idle": (0.5, 2.5), "load": (2.5, 4.5), "empty": (2.1, 2.9)}

FAKE_TEGRASTATS = """#!/bin/sh
[ "$1" = --stop ] && exit 0
i=0
while echo "11-16-2026 00:01:18 VDD_GPU_SOC ${i}mW/${i}mW"; do i=$((i + 1)); sleep 0.05; done
"""


def _data() -> TegraData:
    log = "\n".join(
        f"{t}::{LINE.format(util=util, gpu=gpu)}" for t, (util, gpu) in SAMPLES.items()
    )
    return TegraData(io.StringIO(log), windows=WINDOWS)


def test_window() -> None:
    data = _data()
    idle, load = data.window("idle"), data.window("load")
    assert (idle.entries, idle.duration) == (3, 2.0)
    assert idle.powerdraw["VDD_GPU_SOC"].raw == [3000.0, 3000.0, 3000.0]
    assert idle.powerdraw["VDD_TOTAL"].mean == 5000.0
    assert load.entries == 3
    assert load.powerdraw["VDD_GPU_SOC"].mean == 10000.0
    gpu_util = load.parse(["GR3D_FREQ"], lambda value: float(value[:-1]))
    assert gpu_util["GR3D_FREQ"].mean == 99.0
    assert load.windows == data.windows


def test_window_leaves_data_unchanged() -> None:
    data = _data()
    data.filter([(0.5, 2.5)])
    load = data.window("load")
    assert load.filtered is None
    assert load.powerdraw["VDD_GPU_SOC"].mean == 10000.0
    load.filter([(3.2, 4.5)])
    load.windows["extra"] = (0.0, 1.0)
    assert load.powerdraw["VDD_GPU_SOC"].mean == 10500.0
    assert (data.entries, data.duration) == (len(SAMPLES), 3.0)
    assert data.powerdraw["VDD_GPU_SOC"].mean == 3000.0
    assert "extra" not in data.windows


def test_window_errors() -> None:
    data = _data()
    with pytest.raises(KeyError, match="missing"):
        data.window("missing")
    with pytest.raises(ValueError, match="empty"):
        data.window("empty")


def test_duration_without_timestamps() -> None:
    assert TegraData(io.StringIO("")).duration == 0.0
    assert TegraData(io.StringIO(LINE.format(util=0, gpu=0))).duration == 0.0


def test_tegrastats_window_names() -> None:
    tegrastats = TegraStats()
    with tegrastats.window("block"):
        pass
    with pytest.raises(RuntimeError), tegrastats.window("raises"):
        raise RuntimeError
    first = tegrastats.data.windows["block"]
    with tegrastats.window("block"):
        pass
    windows = tegrastats.data.windows
    assert set(windows) == {"block", "raises"}
    assert windows["block"][0] >= first[1]


def test_tegrastats_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "tegrastats"
    fake.write_text(FAKE_TEGRASTATS)
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path), prepend=os.pathsep)

    tegrastats = TegraStats(interval=50)
    with tegrastats:
        with tegrastats.window("first"):
            time.sleep(0.3)
        with tegrastats.window("second"):
            time.sleep(0.3)
    data = tegrastats.data
    first, second = data.window("first"), data.window("second")
    assert first.duration >= 0.3
    assert first.entries + second.entries <= data.entries
    first_mw = first.powerdraw["VDD_GPU_SOC"].raw
    second_mw = second.powerdraw["VDD_GPU_SOC"].raw
    assert max(first_mw) < min(second_mw)

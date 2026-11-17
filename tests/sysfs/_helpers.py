# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import TYPE_CHECKING

from jetsontools import TegraData

if TYPE_CHECKING:
    import pytest

LOGS = Path(__file__).parent.parent.parent / "data" / "logs"

SUDO_LINE = (
    "11-15-2026 23:41:33 RAM 16574/62841MB (lfb 40x4MB) SWAP 1039/31421MB (cached 2MB) "
    "CPU [2%@729,2%@729,0%@729,2%@729,65%@2031,2%@1881,0%@1881,0%@1881,0%@729,36%@729,15%@729,0%@729] "
    "EMC_FREQ 0%@3199 GR3D_FREQ 1%@[1300,1300] NVENC off NVDEC off NVJPG off NVJPG1 off VIC off OFA off "
    "NVDLA0 {dla0} NVDLA1 {dla1} PVA0_FREQ off APE 174 cpu@48.156C tboard@37.375C soc2@44.093C "
    "tdiode@37.75C soc0@45.187C tj@48.656C soc1@44.625C VDD_GPU_SOC 7587mW/3555mW VDD_CPU_CV 2397mW/698mW "
    "VIN_SYS_5V0 6229mW/4198mW VDDQ_VDD2_1V8AO 1906mW/485mW"
)
LINE = "11-16-2026 00:01:18 GR3D_FREQ 0% VDD_GPU_SOC {mw}mW/{mw}mW"
SYSFS_LOG = """#SYSFS nvdla0 counter 50.0 /sys/bus/platform/devices/15880000.nvdla0/power/runtime_active_time
#SYSFS temp gauge 20.0 /sys/class/thermal/thermal_zone0/temp
1.0::nvdla0 100
1.0::temp 100
2.0::nvdla0 400
2.0::temp 200
3.0::nvdla0 700
3.0::temp 300
3.5::nvdla0 750
4.0::nvdla0 900
4.0::temp 400
4.5::nvdla0 truncated
"""
FAKE_TEGRASTATS = """#!/bin/sh
[ "$1" = --stop ] && exit 0
while echo "11-16-2026 00:01:18 VDD_GPU_SOC 4392mW/4392mW"; do sleep 0.05; done
"""


def _tegrastats_log(times: list[float]) -> str:
    return "\n".join(f"{t}::{LINE.format(mw=1000)}" for t in times)


def _data(windows: dict[str, tuple[float, float]] | None = None) -> TegraData:
    return TegraData(
        io.StringIO(_tegrastats_log([1.0, 2.0, 3.0, 4.0])),
        windows=windows or {},
        sysfs=io.StringIO(SYSFS_LOG),
    )


def _fake_tegrastats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "bin" / "tegrastats"
    fake.parent.mkdir()
    fake.write_text(FAKE_TEGRASTATS)
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake.parent), prepend=os.pathsep)


def _set(path: Path, value: int) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(f"{value}\n")
    tmp.replace(path)


def _devices(root: Path, names: dict[str, str]) -> None:
    for device, file in names.items():
        path = root / "devices" / device / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("100\n")


ACTIVE = "power/runtime_active_time"

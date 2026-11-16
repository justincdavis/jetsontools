# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import pytest

from jetsontools import TegraStats

if TYPE_CHECKING:
    from pathlib import Path

LINE = (
    "11-16-2026 00:01:18 RAM 14948/62841MB (lfb 40x4MB) SWAP 1039/31421MB (cached 2MB) "
    "CPU [0%@729,0%@729,0%@729,0%@729,0%@729,0%@729,0%@729,0%@729,100%@2201,0%@2201,0%@2201,0%@2201] "
    "GR3D_FREQ 0% cpu@49.625C tboard@39.25C soc2@45.718C tdiode@39.625C soc0@46.656C gpu@45.25C "
    "tj@49.625C soc1@46.5C VDD_GPU_SOC 4392mW/4392mW VDD_CPU_CV 3196mW/3196mW "
    "VIN_SYS_5V0 4815mW/4815mW VDDQ_VDD2_1V8AO 802mW/802mW"
)
FAKE_TEGRASTATS = f"""#!/bin/sh
if [ "$1" = "--stop" ]; then
    kill "$(cat "$0.pid")" 2>/dev/null
    exit 0
fi
echo $$ > "$0.pid"
while true; do
    echo "{LINE}"
    sleep 0.05
done
"""


@pytest.mark.parametrize("output", [None, "log.tegrastats"])
def test_tegrastats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str | None
) -> None:
    fake = tmp_path / "tegrastats"
    fake.write_text(FAKE_TEGRASTATS)
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    tegrastats = TegraStats(output=tmp_path / output if output else None, interval=50)
    with tegrastats:
        time.sleep(0.3)
    data = tegrastats.data
    assert data.entries > 0
    assert data.powerdraw["VDD_GPU_SOC"].mean == 4392.0

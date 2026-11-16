# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from jetsontools import TegraStats

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

FAKE_TEGRASTATS = """#!/bin/sh
[ "$1" = --stop ] && exit 0
while echo "11-16-2026 00:01:18 VDD_GPU_SOC 4392mW/4392mW"; do sleep 0.05; done
"""


def test_tegrastats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "tegrastats"
    fake.write_text(FAKE_TEGRASTATS)
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path), prepend=os.pathsep)

    tegrastats = TegraStats(interval=50)
    with tegrastats:
        time.sleep(0.3)
    data = tegrastats.data
    assert data.entries > 0
    assert data.powerdraw["VDD_GPU_SOC"].mean == 4392.0

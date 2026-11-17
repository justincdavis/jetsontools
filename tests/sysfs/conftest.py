# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _no_real_sysfs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("jetsontools._sysfs._DEVICES", str(tmp_path / "devices"))
    monkeypatch.setattr("jetsontools._sysfs._INA3221", str(tmp_path / "ina3221"))

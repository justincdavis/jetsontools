# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Fixtures over the recordings, and a guard against running tegrastats."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from jetsontools import TegraData
from tests.logs._helpers import RECORDINGS_PER_BOARD, Recording, discover

if TYPE_CHECKING:
    from pathlib import Path

RECORDINGS = discover()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Run tests using the recording or board fixture over every recording or board."""
    if "board" in metafunc.fixturenames:
        metafunc.parametrize("board", sorted(RECORDINGS_PER_BOARD))
    if "recording" in metafunc.fixturenames:
        metafunc.parametrize(
            "recording", RECORDINGS, ids=[recording.id for recording in RECORDINGS]
        )


@pytest.fixture(autouse=True)
def _no_hardware(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        err_msg = f"Tests on recordings must not spawn processes: {args}, {kwargs}"
        raise AssertionError(err_msg)

    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr("jetsontools._sysfs._DEVICES", str(tmp_path / "devices"))


@pytest.fixture
def data(recording: Recording) -> TegraData:
    """Parse the recording into a new TegraData."""
    return TegraData(recording.path)

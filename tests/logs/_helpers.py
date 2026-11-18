# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Discovery of the recordings in data/logs and the parsers' known gaps."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from jetsontools import TegraData

if TYPE_CHECKING:
    from typing_extensions import Self

LOGS = Path(__file__).parent.parent.parent / "data" / "logs"

XAVIER_AGX = "xavieragx_16gb"
NO_DATE_TIME = (
    "Xavier AGX recordings have no DATE/TIME columns, so the parser takes RAM "
    "and its value as DATE and TIME"
)
UNSTABLE_KEYS = (
    "Xavier AGX 'MTS fg 0% bg 3%' is parsed as pairs, so keys change per sample"
)
NAME_COLLISION = (
    "Xavier AGX rails named GPU, CPU and SOC overwrite the CPU and GPU fields"
)
NO_POWER_UNITS = (
    "Xavier AGX rails are reported as 'GPU 463/463' without mW, "
    "so powerdraw does not find them"
)

TEMPERATURE = re.compile(r"-?\d+(\.\d+)?C")
UNAVAILABLE_TEMPERATURE = -256.0


@dataclass(frozen=True)
class Recording:
    """One tegrastats recording from data/logs/<board>/<kind>.tegrastats."""

    board: str
    kind: str
    path: Path

    @property
    def id(self: Self) -> str:
        """The pytest id of the recording."""
        return f"{self.board}-{self.kind}"

    @property
    def orin(self: Self) -> bool:
        """Whether the board is an Orin."""
        return self.board.startswith("orin")

    @property
    def sudo(self: Self) -> bool:
        """Whether the recording was made with --readall --sudo."""
        return self.kind == "all"

    @property
    def lines(self: Self) -> int:
        """The number of lines in the recording."""
        return len(self.path.read_text(encoding="ascii").splitlines())


def discover() -> list[Recording]:
    """Find every recording under data/logs."""
    return [
        Recording(path.parent.name, path.stem, path)
        for path in sorted(LOGS.glob("*/*.tegrastats"))
    ]


def load(board: str, kind: str) -> TegraData:
    """Parse the recording of the board and kind."""
    return TegraData(LOGS / board / f"{kind}.tegrastats")


RECORDINGS_PER_BOARD: dict[str, set[str]] = {}
for _recording in discover():
    RECORDINGS_PER_BOARD.setdefault(_recording.board, set()).add(_recording.kind)


def known_gap(
    request: pytest.FixtureRequest,
    recording: Recording,
    reason: str,
    kind: str | None = None,
) -> None:
    """Mark the test as an expected failure on the Xavier AGX recordings."""
    if recording.board == XAVIER_AGX and kind in (None, recording.kind):
        request.applymarker(pytest.mark.xfail(reason=reason, strict=True))

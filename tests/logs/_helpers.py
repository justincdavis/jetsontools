# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Discovery of the recordings in data/logs and the parsers' known gaps."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from jetsontools import TegraData

if TYPE_CHECKING:
    from typing_extensions import Self

LOGS = Path(__file__).parent.parent.parent / "data" / "logs"

XAVIER_AGX = "xavieragx_16gb"
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

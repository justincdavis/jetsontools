# Copyright (c) 2025 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ._parsing import Metric, filter_data, get_data, get_powerdraw, parse_tegrastats

if TYPE_CHECKING:
    import io
    from collections.abc import Callable

    from typing_extensions import Self


@dataclass
class TegraData:
    """Container for tegrastats data with parsing and filtering capabilities."""

    file: io.TextIOBase = field(init=True, repr=True)
    data: list[dict[str, str]] = field(init=False, repr=False)
    entries: int = field(default=0, init=False, repr=True)
    filtered: list[dict[str, str]] | None = field(default=None, init=False, repr=False)
    filtered_entries: list[tuple[tuple[float, float], list[dict[str, str]]]] | None = (
        field(default=None, init=False, repr=False)
    )

    def __post_init__(self: Self) -> None:
        """Initialize parsed data and entry count after object creation."""
        self.data = parse_tegrastats(self.file)
        self.entries = len(self.data)

    def __len__(self: Self) -> int:
        return self.entries

    @property
    def powerdraw(self: Self) -> dict[str, Metric]:
        """
        Get power draw metrics from the data.

        Returns
        -------
        dict[str, Metric]
            Power draw metrics by component.

        """
        if self.filtered is None:
            return get_powerdraw(self.data)
        return get_powerdraw(self.filtered)

    def filter(self: Self, timestamps: list[tuple[float, float]]) -> None:
        """
        Filter the data by timestamp ranges.

        Parameters
        ----------
        timestamps : list[tuple[float, float]]
            List of (start, end) timestamp tuples to filter by.

        """
        self.filtered, self.filtered_entries = filter_data(self.data, timestamps)

    def parse(
        self: Self, names: list[str], parsefunc: Callable[[str], float | int]
    ) -> dict[str, Metric]:
        """
        Parse specific metrics from the data using a custom parsing function.

        Parameters
        ----------
        names : list[str]
            List of metric names to parse.
        parsefunc : Callable[[str], float | int]
            Function to parse string values to numeric types.

        Returns
        -------
        dict[str, Metric]
            Parsed metrics by name.

        """
        if self.filtered is None:
            return get_data(self.data, names, parsefunc)
        return get_data(self.filtered, names, parsefunc)

    def save_as_csv(self: Self, file: Path | str) -> None:
        """
        Save the tegrastats data to a csv file.

        Parameters
        ----------
        file : Path, str
            The path to the csv file to save the data to.

        """
        file = Path(file)
        data = self.filtered if self.filtered is not None else self.data
        with file.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

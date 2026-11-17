# Copyright (c) 2025 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import copy
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ._parsing import (
    Metric,
    filter_data,
    get_data,
    get_dla_utilization,
    get_powerdraw,
    parse_tegrastats,
)
from ._sysfs import _counters, _gauges, _parse_sysfs

if TYPE_CHECKING:
    import io
    from collections.abc import Callable

    from typing_extensions import Self


@dataclass
class TegraData:
    """
    Container for tegrastats data with parsing and filtering capabilities.

    Attributes
    ----------
    windows : dict[str, tuple[float, float]]
        The (start, stop) time.time() timestamps of named windows, by name.
    duration : float
        The seconds covered by the data, regardless of filter.
        For data from window, the length of the window.
        Otherwise, the time between the first and last entry.
    span : tuple[float, float] | None
        For data from window, the (start, stop) timestamps of the window.
    sysfs : Path | str | io.TextIOBase | None
        The sysfs samples written by TegraStats, if any.

    """

    file: Path | str | io.TextIOBase = field(init=True, repr=True)
    windows: dict[str, tuple[float, float]] = field(
        default_factory=dict, init=True, repr=False
    )
    sysfs: Path | str | io.TextIOBase | None = field(
        default=None, init=True, repr=False
    )
    data: list[dict[str, str]] = field(init=False, repr=False)
    entries: int = field(default=0, init=False, repr=True)
    duration: float = field(default=0.0, init=False, repr=True)
    filtered: list[dict[str, str]] | None = field(default=None, init=False, repr=False)
    filtered_entries: list[tuple[tuple[float, float], list[dict[str, str]]]] | None = (
        field(default=None, init=False, repr=False)
    )
    span: tuple[float, float] | None = field(default=None, init=False, repr=False)
    sysfs_kinds: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    sysfs_series: dict[str, tuple[list[float], list[float]]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self: Self) -> None:
        """Initialize parsed data and entry count after object creation."""
        if isinstance(self.file, (str, Path)):
            with Path(self.file).open("r", encoding="ascii") as fh:
                self.data = parse_tegrastats(fh)
        else:
            self.data = parse_tegrastats(self.file)
        self.entries = len(self.data)
        if self.sysfs is not None:
            self.sysfs_kinds, self.sysfs_series = _parse_sysfs(self.sysfs)
        if self.data and "timestamp" in self.data[0]:
            self.duration = float(self.data[-1]["timestamp"]) - float(
                self.data[0]["timestamp"]
            )

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

    @property
    def dla_utilization(self: Self) -> dict[str, Metric]:
        """
        DLA utilization metrics from the data.

        tegrastats only reports the DLA cores when run with sudo.

        Returns
        -------
        dict[str, Metric]
            Utilization (%) metrics by DLA core name (NVDLA0, ...).
            Empty if the data has no DLA entries.

        """
        if self.filtered is None:
            return get_dla_utilization(self.data)
        return get_dla_utilization(self.filtered)

    @property
    def sysfs_counters(self: Self) -> dict[str, float]:
        """
        Change of each sysfs counter over the data.

        Measured between the first and last sample within the data,
        or within each timestamp range given to filter, summed over the ranges.
        Windows from TegraStats.window have samples at both edges.

        Returns
        -------
        dict[str, float]
            The change of each counter, by reader name.
            Readers without samples in the data are not included.

        """
        return _counters(self.sysfs_kinds, self.sysfs_series, self._sysfs_ranges())

    @property
    def sysfs_gauges(self: Self) -> dict[str, Metric]:
        """
        Samples of each sysfs gauge over the data.

        Returns
        -------
        dict[str, Metric]
            The metrics of each gauge, by reader name.
            Readers without samples in the data are not included.

        """
        return _gauges(self.sysfs_kinds, self.sysfs_series, self._sysfs_ranges())

    def _sysfs_ranges(self: Self) -> list[tuple[float, float]] | None:
        ranges = None
        if self.filtered_entries is not None:
            ranges = [timestamps for timestamps, _ in self.filtered_entries]
        if self.span is None:
            return ranges
        if ranges is None:
            return [self.span]
        low, high = self.span
        return [
            (max(start, low), min(stop, high))
            for start, stop in ranges
            if max(start, low) <= min(stop, high)
        ]

    def filter(self: Self, timestamps: list[tuple[float, float]]) -> None:
        """
        Filter the data by timestamp ranges.

        Parameters
        ----------
        timestamps : list[tuple[float, float]]
            List of (start, end) timestamp tuples to filter by.

        """
        self.filtered, self.filtered_entries = filter_data(self.data, timestamps)

    def window(self: Self, name: str) -> TegraData:
        """
        Get the data collected during a named window.

        Uses all of the data, regardless of filter.
        Returns a new TegraData, this TegraData is unchanged.

        Parameters
        ----------
        name : str
            The name of the window, from TegraStats.window or the windows field.

        Returns
        -------
        TegraData
            The data containing only the entries within the window.

        Raises
        ------
        KeyError
            If there is no window with the name.
        ValueError
            If no entries are within the window.

        """
        if name not in self.windows:
            err_msg = f"No window named: {name}, windows are: {list(self.windows)}"
            raise KeyError(err_msg)
        start, stop = self.windows[name]
        entries, _ = filter_data(self.data, [(start, stop)])
        if not entries:
            err_msg = f"No tegrastats entries within window: {name}, use a longer window or shorter interval"
            raise ValueError(err_msg)
        window = copy.copy(self)
        window.data = entries
        window.entries = len(entries)
        window.filtered = None
        window.filtered_entries = None
        window.windows = dict(self.windows)
        window.duration = stop - start
        window.span = (start, stop)
        return window

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

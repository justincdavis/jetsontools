# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import dataclasses
import glob
import logging
import re
import threading
import time
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import TYPE_CHECKING

from ._parsing import Metric

if TYPE_CHECKING:
    import io
    import multiprocessing as mp
    from collections.abc import Iterable, Sequence
    from typing import Literal

    from typing_extensions import Self

    Series = tuple[list[float], list[float]]

_log = logging.getLogger(__name__)

_DEVICES = "/sys/bus/platform/devices"
_ACTIVE_TIME = "power/runtime_active_time"
_FLAGS: dict[str, tuple[str, ...]] = {
    "dla": ("*.nvdla[0-9]*",),
    "gpu": ("*.gpu",),
    "pva": ("*.pva[0-9]*",),
    "media": ("*.vic", "*.nvenc*", "*.nvdec*", "*.nvjpg*", "*.ofa"),
}
_DEVICE = re.compile(r"[0-9a-f]+\.([a-z]+[0-9]*)")
_NAME = re.compile(r"[A-Za-z0-9_.-]+")
_HEADER = "#SYSFS"
_PROBE_SECONDS = 0.2
_MIN_INTERVAL = 1.0


@dataclass(frozen=True)
class SysfsReader:
    """
    A sysfs file sampled in the background while TegraStats runs.

    Attributes
    ----------
    name : str
        The name of the data, made of letters, digits, '_', '.' and '-'.
    path : str
        The path of the file, or a glob pattern matching exactly one file.
    kind : Literal["counter", "gauge"]
        A counter holds a cumulative value, reported as its change over the data.
        A gauge holds an instantaneous value, reported as a Metric.
        By default, a gauge
    interval : float, optional
        The milliseconds between samples, at least 1 ms.
        If None, a counter is sampled at the tegrastats interval, and for a
        gauge TegraStats measures the median time between changes of the value
        when created, polling the file at up to 1 kHz for 0.2 seconds, and
        samples at that rate, between 1 ms and the tegrastats interval.
        By default, None

    """

    name: str
    path: str
    kind: Literal["counter", "gauge"] = "gauge"
    interval: float | None = None

    def __post_init__(self: Self) -> None:
        """
        Validate the reader.

        Raises
        ------
        ValueError
            If the name, kind or interval is not valid.

        """
        if not _NAME.fullmatch(self.name):
            err_msg = f"Invalid sysfs reader name: {self.name}"
            raise ValueError(err_msg)
        if self.kind not in ("counter", "gauge"):
            err_msg = f"Sysfs reader kind must be counter or gauge, got: {self.kind}"
            raise ValueError(err_msg)
        if self.interval is not None and self.interval <= 0:
            err_msg = f"Sysfs reader interval must be positive, got: {self.interval}"
            raise ValueError(err_msg)


def _read_text(path: Path | str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read(path: str) -> str | None:
    value = _read_text(path)
    if value is None:
        return None
    try:
        float(value)
    except ValueError:
        return None
    return value


def _flag_readers(flag: str) -> list[SysfsReader]:
    readers: list[SysfsReader] = []
    for pattern in _FLAGS[flag]:
        seen: dict[str, int] = {}
        for device in sorted(Path(_DEVICES).glob(pattern)):
            match = _DEVICE.fullmatch(device.name)
            if match is None:
                continue
            base = match.group(1)
            count = seen.get(base, 0)
            seen[base] = count + 1
            path = device / _ACTIVE_TIME
            if path.is_file():
                name = f"{base}{count}" if count else base
                readers.append(SysfsReader(name, str(path), "counter"))
    return readers


def _probe_intervals(paths: list[str], ceiling: float) -> list[float]:
    if not paths:
        return []
    last = [_read(path) for path in paths]
    changed: list[float | None] = [None] * len(paths)
    gaps: list[list[float]] = [[] for _ in paths]
    end = time.perf_counter() + _PROBE_SECONDS
    while time.perf_counter() < end:
        for index, path in enumerate(paths):
            value = _read(path)
            now = time.perf_counter()
            if value == last[index]:
                continue
            previous = changed[index]
            if previous is not None:
                gaps[index].append(now - previous)
            changed[index], last[index] = now, value
        time.sleep(_MIN_INTERVAL / 1000)
    return [
        min(max(median(gap) * 1000, _MIN_INTERVAL), ceiling) if gap else ceiling
        for gap in gaps
    ]


def _resolve(readers: Sequence[SysfsReader], ceiling: float) -> list[SysfsReader]:
    resolved: list[SysfsReader] = []
    for reader in readers:
        matches = sorted(glob.glob(reader.path))  # noqa: PTH207
        if len(matches) != 1 or _read(matches[0]) is None:
            _log.warning(
                f"Sysfs reader {reader.name} needs one readable file, found: {matches}"
            )
            continue
        resolved.append(dataclasses.replace(reader, path=matches[0]))

    probe = [r for r in resolved if r.interval is None and r.kind == "gauge"]
    probed = dict(
        zip(
            [reader.name for reader in probe],
            _probe_intervals([reader.path for reader in probe], ceiling),
        )
    )
    return [
        dataclasses.replace(
            reader,
            interval=probed.get(
                reader.name, ceiling if reader.interval is None else reader.interval
            ),
        )
        for reader in resolved
    ]


def _header(readers: Iterable[SysfsReader]) -> str:
    return "".join(
        f"{_HEADER} {r.name} {r.kind} {r.interval} {r.path}\n" for r in readers
    )


def _read_now(readers: Iterable[SysfsReader], timestamp: float) -> str:
    samples = ((r.name, _read(r.path)) for r in readers)
    return "".join(
        f"{timestamp}::{name} {value}\n" for name, value in samples if value is not None
    )


def _poll(
    reader: SysfsReader,
    file: io.TextIOBase,
    lock: threading.Lock,
    done: threading.Event,
) -> None:
    interval = max(reader.interval or _MIN_INTERVAL, _MIN_INTERVAL) / 1000
    deadline = time.perf_counter() + interval
    while not done.wait(max(0.0, deadline - time.perf_counter())):
        line = _read_now([reader], time.time())
        with lock:
            file.write(line)
            file.flush()
        deadline = max(deadline + interval, time.perf_counter())


def _sample(
    readers: list[SysfsReader],
    output: Path | io.TextIOBase,
    ready: mp.synchronize.Event,
    stop: mp.synchronize.Event,
) -> None:
    file = output.open("a", encoding="utf-8") if isinstance(output, Path) else output
    lock = threading.Lock()
    done = threading.Event()
    file.write(_read_now(readers, time.time()))
    file.flush()
    threads = [
        threading.Thread(target=_poll, args=(r, file, lock, done), daemon=True)
        for r in readers
    ]
    for thread in threads:
        thread.start()
    ready.set()
    stop.wait()
    done.set()
    for thread in threads:
        thread.join()
    if isinstance(output, Path):
        file.close()


def _parse_line(line: str) -> tuple[str, float, float] | None:
    timestamp, sep, rest = line.partition("::")
    name, _, value = rest.strip().partition(" ")
    if not sep:
        return None
    try:
        return name, float(timestamp), float(value)
    except ValueError:
        return None


def _parse_sysfs(
    file: Path | str | io.TextIOBase,
) -> tuple[dict[str, str], dict[str, Series]]:
    if isinstance(file, (str, Path)):
        with Path(file).open("r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = [str(line) for line in file.readlines()]

    kinds: dict[str, str] = {}
    samples: dict[str, list[tuple[float, float]]] = {}
    for line in lines:
        if line.startswith(f"{_HEADER} "):
            fields = line.split(" ", 4)
            if len(fields) == 5:
                kinds[fields[1]] = fields[2]
            continue
        parsed = _parse_line(line)
        if parsed is not None:
            name, timestamp, value = parsed
            samples.setdefault(name, []).append((timestamp, value))

    series: dict[str, Series] = {}
    for name, points in samples.items():
        points.sort()
        series[name] = ([t for t, _ in points], [v for _, v in points])
    return kinds, series


def _select(
    series: Series, ranges: list[tuple[float, float]] | None
) -> list[list[float]]:
    times, values = series
    if ranges is None:
        return [values]
    return [
        values[bisect_left(times, start) : bisect_right(times, stop)]
        for start, stop in ranges
    ]


def _counters(
    kinds: dict[str, str],
    series: dict[str, Series],
    ranges: list[tuple[float, float]] | None,
) -> dict[str, float]:
    counters: dict[str, float] = {}
    for name, kind in kinds.items():
        if kind != "counter" or name not in series:
            continue
        selections = _select(series[name], ranges)
        changes = [values[-1] - values[0] for values in selections if values]
        if changes:
            counters[name] = sum(changes)
    return counters


def _gauges(
    kinds: dict[str, str],
    series: dict[str, Series],
    ranges: list[tuple[float, float]] | None,
) -> dict[str, Metric]:
    gauges: dict[str, Metric] = {}
    for name, kind in kinds.items():
        if kind != "gauge" or name not in series:
            continue
        values = [v for values in _select(series[name], ranges) for v in values]
        if values:
            gauges[name] = Metric(raw=values)
    return gauges


def get_dla_active_time() -> dict[str, int]:
    """
    Get the total time each DLA core has been active.

    Reads the runtime power management counter (runtime_active_time)
    of each DLA device, the milliseconds it has been powered since boot.
    Does not require sudo or tegrastats, so the difference of two calls
    is a lightweight measure of which DLA cores ran work.

    Returns
    -------
    dict[str, int]
        The active time in milliseconds of each DLA core, by name (nvdla0, ...).
        Empty if the device has no DLA cores.

    """
    values = {r.name: _read(r.path) for r in _flag_readers("dla")}
    return {name: int(value) for name, value in values.items() if value is not None}

# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# ruff: noqa: S404, S603, SIM115
from __future__ import annotations

import contextlib
import logging
import multiprocessing as mp
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from jetsontools._sysfs import (
    SysfsReader,
    _flag_readers,
    _header,
    _read_now,
    _resolve,
    _sample,
)
from jetsontools._tegradata import TegraData

if TYPE_CHECKING:
    import io
    from collections.abc import Generator, Sequence
    from types import TracebackType

    from typing_extensions import Self

_log = logging.getLogger(__name__)


class TegraStats:
    """Runs tegrastats in a seperate process and stores output in a file."""

    def __init__(
        self: Self,
        output: Path | str | None = None,
        interval: int = 1000,
        *,
        readall: bool | None = None,
        sudo: bool | None = None,
        sysfs: Sequence[SysfsReader] | None = None,
        read_sysfs_dla: bool | None = None,
        read_sysfs_gpu: bool | None = None,
        read_sysfs_pva: bool | None = None,
        read_sysfs_media: bool | None = None,
        read_sysfs_power: bool | None = None,
    ) -> None:
        """
        Create an instance of tegrastats with outputs to a file.

        Parameters
        ----------
        output : Path | str, optional
            The path to the output file, by default None
            If None, will write to a temporary file
        interval : int, optional
            The interval to run tegrastats in milliseconds, by default 1000
        readall : bool, optional
            Optionally, read all possible information through tegrastats.
            Additional information varies by board.
            Can consume additional CPU resources.
            By default, will NOT readall
        sudo : bool, optional
            Optionally, run the command with sudo.
            By default, will NOT run with sudo
        sysfs : Sequence[SysfsReader], optional
            Optionally, sysfs files to sample in a separate process,
            see TegraData.sysfs_counters and TegraData.sysfs_gauges.
            Samples are written to output with the suffix .sysfs,
            or to a temporary file.
            By default, will NOT sample sysfs
        read_sysfs_dla : bool, optional
            Optionally, sample the time (ms) each DLA core was powered as the
            counters nvdla0 and nvdla1. A core stays powered about 0.5 to 0.6
            seconds after its last task, and about 110 ms of each power up is
            not counted.
            By default, will NOT sample the DLA cores
        read_sysfs_gpu : bool, optional
            Optionally, sample the time (ms) the GPU was powered as the counter
            gpu. Powered is not busy: the GPU stays powered until it rail gates,
            about 1.6 seconds after its last work on Orin, even with a CUDA
            context open.
            By default, will NOT sample the GPU
        read_sysfs_pva : bool, optional
            Optionally, sample the time (ms) each PVA was powered as counters
            (pva0, ...). Powered is not busy, and may include idle time while
            an application holds the PVA.
            By default, will NOT sample the PVA
        read_sysfs_media : bool, optional
            Optionally, sample the time (ms) the VIC, NVENC, NVDEC, NVJPG and
            OFA engines were powered as counters (vic, nvenc, nvdec, nvjpg,
            nvjpg1, ofa, ...). Each stays powered for its autosuspend delay
            after its last task.
            By default, will NOT sample the media engines
        read_sysfs_power : bool, optional
            Optionally, sample the voltage (mV) and current (mA) of each INA3221
            power rail as the gauges <rail>.mV and <rail>.mA, see
            TegraData.sysfs_energy. Each read is an I2C transfer, so the rails
            are sampled every 50 ms, or less often with more than 5 rails so
            that all of them take at most 200 reads per second.
            By default, will NOT sample the power rails

        Raises
        ------
        ValueError
            If two sysfs readers have the same name.

        """
        # constructor args
        self._output: Path | None = Path(output) if output is not None else None
        self._interval = interval
        self._readall = readall
        self._sudo = sudo
        self._windows: dict[str, tuple[float, float]] = {}

        readers = list(sysfs or [])
        flags = {
            "dla": read_sysfs_dla,
            "gpu": read_sysfs_gpu,
            "pva": read_sysfs_pva,
            "media": read_sysfs_media,
            "power": read_sysfs_power,
        }
        for flag, enabled in flags.items():
            if enabled:
                found = _flag_readers(flag)
                if not found:
                    _log.warning(f"No sysfs files found for read_sysfs_{flag}")
                readers.extend(found)
        names = [reader.name for reader in readers]
        if len(set(names)) != len(names):
            err_msg = f"Sysfs reader names must be unique, got: {names}"
            raise ValueError(err_msg)
        self._sysfs = _resolve(readers, float(interval))
        self._sysfs_output: Path | io.TextIOBase | None = None
        if self._sysfs:
            if self._output is not None:
                self._sysfs_output = Path(f"{self._output}.sysfs")
                self._sysfs_output.write_text(_header(self._sysfs), encoding="utf-8")
            else:
                self._sysfs_output = tempfile.TemporaryFile(mode="a+", encoding="utf-8")
                self._sysfs_output.write(_header(self._sysfs))
                self._sysfs_output.flush()

        # create a tempfile and open in the constructor
        # allows to access the file after the context manager is exited
        # will be closed during garbage collection
        self._tempfile: io.TextIOBase = tempfile.TemporaryFile(
            mode="w+", encoding="ascii"
        )

        # handle the tegrastats process
        self._mp_context = mp.get_context("fork")
        self._start_flag: mp.synchronize.Event = self._mp_context.Event()
        self._process = self._mp_context.Process(
            target=self._run,
            args=(self._output, self._tempfile, self._interval, self._start_flag),
            kwargs={"readall": self._readall, "sudo": self._sudo},
            daemon=True,
        )
        self._sysfs_ready: mp.synchronize.Event = self._mp_context.Event()
        self._sysfs_stop: mp.synchronize.Event = self._mp_context.Event()
        self._sysfs_process = self._make_sysfs_process()

    def __del__(self: Self) -> None:
        with contextlib.suppress(AttributeError):
            self._tempfile.close()
        with contextlib.suppress(AttributeError):
            if self._sysfs_output is not None and not isinstance(
                self._sysfs_output, Path
            ):
                self._sysfs_output.close()

    def __enter__(self: Self) -> Self:
        self.start()
        return self

    def __exit__(
        self: Self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

    @property
    def data(self: Self) -> TegraData:
        """
        Get the data from the tegrastats process.

        Returns
        -------
        TegraData
            The tegrastats data

        """
        f: io.TextIOBase
        if self._output is not None:
            f = self._output.open("r")
        else:
            # For tempfile, seek to beginning before reading
            self._tempfile.seek(0)
            f = self._tempfile
        sysfs = self._sysfs_output
        if sysfs is not None and not isinstance(sysfs, Path):
            sysfs.seek(0)
        return TegraData(f, windows=dict(self._windows), sysfs=sysfs)

    @property
    def sysfs(self: Self) -> list[SysfsReader]:
        """
        The sysfs readers being sampled.

        Returns
        -------
        list[SysfsReader]
            The readers with their resolved path and interval (ms).
            Readers without a readable file are not included.

        """
        return list(self._sysfs)

    @contextlib.contextmanager
    def window(self: Self, name: str) -> Generator[None, None, None]:
        """
        Mark a block of code as a named window.

        The data collected during the block can then be found with
        TegraData.window. Reusing a name replaces the window.
        Sysfs counters are read when the block starts and ends,
        so their change over the window is exact. An engine stays powered
        for a while after its last task, which is counted in the next window
        when the gap between the windows is shorter than that.

        Parameters
        ----------
        name : str
            The name of the window.

        Yields
        ------
        None
            Runs the block of code inside the window.

        Examples
        --------
        >>> with TegraStats(interval=50) as tegrastats:
        ...     with tegrastats.window("inference"):
        ...         run_model()
        >>> inference = tegrastats.data.window("inference")
        >>> inference.powerdraw["VDD_GPU_SOC"].mean

        """
        start = time.time()
        self._write_counters(start)
        try:
            yield
        finally:
            stop = time.time()
            self._write_counters(stop)
            self._windows[name] = (start, stop)

    def start(self: Self) -> None:
        """Start running Tegrastats."""
        # start the process
        self._process.start()

        # need to wait for Flag
        self._start_flag.wait()

        if self._sysfs_process is not None:
            self._sysfs_process.start()
            self._sysfs_ready.wait()

    def stop(self: Self) -> None:
        """Stop running Tegrastats."""
        _log.debug("Stopping tegrastats")
        self._process.terminate()
        command = ["tegrastats", "--stop"]
        subprocess.run(
            command,
            check=True,
        )
        if self._sysfs_process is not None:
            self._sysfs_stop.set()
            self._sysfs_process.join(timeout=5)
            if self._sysfs_process.is_alive():
                self._sysfs_process.terminate()

    def reset(self: Self) -> None:
        """Reset the Tegrastats process and data file."""
        self.stop()
        self._process = self._mp_context.Process(
            target=self._run,
            args=(self._output, self._tempfile, self._interval, self._start_flag),
            kwargs={"readall": self._readall, "sudo": self._sudo},
            daemon=True,
        )
        self._sysfs_ready.clear()
        self._sysfs_stop.clear()
        self._sysfs_process = self._make_sysfs_process()
        self.start()

    def _make_sysfs_process(self: Self) -> mp.process.BaseProcess | None:
        if self._sysfs_output is None:
            return None
        return self._mp_context.Process(
            target=_sample,
            args=(self._sysfs, self._sysfs_output, self._sysfs_ready, self._sysfs_stop),
            daemon=True,
        )

    def _write_counters(self: Self, timestamp: float) -> None:
        counters = [reader for reader in self._sysfs if reader.kind == "counter"]
        if not counters or self._sysfs_output is None:
            return
        lines = _read_now(counters, timestamp)
        if isinstance(self._sysfs_output, Path):
            with self._sysfs_output.open("a", encoding="utf-8") as f:
                f.write(lines)
        else:
            self._sysfs_output.write(lines)
            self._sysfs_output.flush()

    @staticmethod
    def _run(
        output: Path | None,
        tempfile: io.TextIOBase,
        interval: int,
        flag: mp.synchronize.Event,
        *,
        readall: bool | None = None,
        sudo: bool | None = None,
    ) -> None:
        """
        Target function for process running tegrastats.

        Parameters
        ----------
        output : Path | None
            The path to the output file.
            If None, will write to a temporary file
        tempfile : io.TextIOBase
            The temporary file to write to.
        interval : int
            The interval to update tegrastats info (ms).
        flag : mp.synchronize.Event
            The event to signal that the process is started.
        readall : bool, optional
            Optionally, read all possible information through tegrastats.
            Additional information varies by board.
            Can consume additional CPU resources.
            By default, will NOT readall
        sudo : bool, optional
            Optionally, run the command with sudo.
            By default, will NOT run with sudo

        Raises
        ------
        RuntimeError
            If the process created by Popen does not have stdout/stderr
        CalledProcessError
            If the process has any stderr output

        """
        # maintain the file in open state
        _log.debug(f"Open file {output} for writing")
        f = output.open("w+") if output is not None else tempfile

        # create the command and run the Popen call
        command = ["tegrastats", "--interval", str(interval)]
        if sudo:
            command.insert(0, "sudo")
        if readall:
            command.append("--readall")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        _log.debug(f"Ran tegrastats with command: {command}")

        # ensure stdout/stderr streams exist
        if process.stdout is None or process.stderr is None:
            err_msg = "Cannot access stdout or stderr streams in Tegrastat process."
            raise RuntimeError(err_msg)

        _log.debug("No errors from process found")

        # read output while it exists
        # this will be stopped by the __exit__ call
        # which will call tegrastats --stop
        # resulting in the lines to cease
        while True:
            line = process.stdout.readline()

            # send signal once first line is acquired
            if not flag.is_set():
                flag.set()

            if not line:
                break
            f.write(f"{time.time()}::{line}")
            f.flush()

        _log.debug("Stopped reading from tegrastats process")

        # check for any errors
        stderr_output = process.stderr.read()
        if stderr_output:
            raise subprocess.CalledProcessError(
                process.returncode,
                process.args,
                stderr=stderr_output,
            )

        # close the file IF AND ONLY IF it was specified via the output flag
        if output is not None:
            f.close()

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

from jetsontools._tegradata import TegraData

if TYPE_CHECKING:
    import io
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

        """
        # constructor args
        self._output: Path | None = Path(output) if output is not None else None
        self._interval = interval
        self._readall = readall
        self._sudo = sudo

        # create a tempfile and open in the constructor
        # allows to access the file after the context manager is exited
        # will be closed during garbage collection
        self._tempfile: io.TextIOBase = tempfile.TemporaryFile(
            mode="w+", encoding="ascii"
        )

        # handle the tegrastats process
        self._start_flag: mp.synchronize.Event = mp.Event()
        self._process = mp.Process(
            target=self._run,
            args=(self._output, self._tempfile, self._interval, self._start_flag),
            kwargs={"readall": self._readall, "sudo": self._sudo},
            daemon=True,
        )

    def __del__(self: Self) -> None:
        with contextlib.suppress(AttributeError):
            self._tempfile.close()

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
        return TegraData(f)

    def start(self: Self) -> None:
        """Start running Tegrastats."""
        # start the process
        self._process.start()

        # need to wait for Flag
        self._start_flag.wait()

    def stop(self: Self) -> None:
        """Stop running Tegrastats."""
        _log.debug("Stopping tegrastats")
        self._process.terminate()
        command = ["tegrastats", "--stop"]
        subprocess.run(
            command,
            check=True,
        )

    def reset(self: Self) -> None:
        """Reset the Tegrastats process and data file."""
        self.stop()
        self._process = mp.Process(
            target=self._run,
            args=(self._output, self._tempfile, self._interval, self._start_flag),
            kwargs={"readall": self._readall, "sudo": self._sudo},
            daemon=True,
        )
        self.start()

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

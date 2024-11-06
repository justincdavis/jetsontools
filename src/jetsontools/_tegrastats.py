# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# ruff: noqa: S404, S603
from __future__ import annotations

import logging
import multiprocessing as mp
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self

_log = logging.getLogger(__name__)


class Tegrastats:
    """Runs tegrastats in a seperate process and stores output in a file."""

    def __init__(
        self: Self,
        output: Path | str,
        interval: int = 1000,
        *,
        readall: bool | None = None,
    ) -> None:
        """
        Create an instance of tegrastats with outputs to a file.

        Parameters
        ----------
        output : Path | str
            The path to the output file
        interval : int, optional
            The interval to run tegrastats in milliseconds, by default 1000
        readall : bool, optional
            Optionally, read all possible information through tegrastats.
            Additional information varies by board.
            Can consume additional CPU resources.
            By default, will NOT readall

        """
        self._output = Path(output)
        self._interval = interval
        self._readall = readall

        self._start_flag = mp.Event()
        self._process = mp.Process(
            target=self._run,
            args=(self._output, self._interval),
            daemon=True,
        )

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
            args=(self._output, self._interval),
            daemon=True,
        )
        self.start()

    def _run(
        self: Self,
        output: Path,
        interval: int,
    ) -> None:
        """
        Target function for process running tegrastats.

        Parameters
        ----------
        output : Path
            The path to the output file.
        interval : int
            The interval to update tegrastats info (ms).

        Raises
        ------
        RuntimeError
            If the process created by Popen does not have stdout/stderr
        CalledProcessError
            If the process has any stderr output

        """
        # maintain the file in open state
        with output.open("w+") as f:
            _log.debug(f"Open file {output} for writing")

            # create the command and run the Popen call
            command = ["tegrastats", "--interval", str(interval)]
            if self._readall:
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

            # signal that the process is opened
            self._start_flag.set()

            # read output while it exists
            # this will be stopped by the __exit__ call
            # which will call tegrastats --stop
            # resulting in the lines to cease
            while True:
                line = process.stdout.readline()
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

# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# ruff: noqa: E402, I001
"""
Package for bounding boxes and their operations.

Functions
---------
set_log_level
    Set the log level for the jetsontools package.
enable_jit
    Enable just-in-time compilation using Numba for some functions.
"""

from __future__ import annotations

# setup the logger before importing anything else
import logging
import os
import sys


# Created from answer by Dennis at:
# https://stackoverflow.com/questions/7621897/python-logging-module-globally
def _setup_logger(level: str | None = None) -> None:
    if level is not None:
        level = level.upper()
    level_map: dict[str | None, int] = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        None: logging.WARNING,
    }
    try:
        log_level = level_map[level]
    except KeyError:
        log_level = logging.WARNING

    # create logger
    logger = logging.getLogger(__package__)
    logger.setLevel(log_level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)


def set_log_level(level: str) -> None:
    """
    Set the log level for the jetsontools package.

    Parameters
    ----------
    level : str
        The log level to set. One of "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".

    Raises
    ------
    ValueError
        If the level is not one of the allowed values.

    """
    if level.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        err_msg = f"Invalid log level: {level}"
        raise ValueError(err_msg)
    _setup_logger(level)


level = os.getenv("jetsontools_LOG_LEVEL")
_setup_logger(level)
_log = logging.getLogger(__name__)
if level is not None and level.upper() not in [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]:
    _log.warning(f"Invalid log level: {level}. Using default log level: WARNING")


from dataclasses import dataclass


@dataclass
class _FLAGS:
    """
    Class for storing flags for jetsontools.

    Attributes
    ----------
    USEJIT : bool
        Whether or not to use jit.
    PARALLEL : bool
        Whether or not to use parallel compilation in the jit.

    """

    USEJIT: bool = False
    PARALLEL: bool = False


_FLAGSOBJ = _FLAGS()


def enable_jit(*, on: bool | None = None, parallel: bool | None = None) -> None:
    """
    Enable just-in-time compilation using Numba for some functions.

    Parameters
    ----------
    on : bool | None
        If True, enable jit. If False, disable jit. If None, enable jit.
    parallel : bool | None
        If True, enable parallel jit. If False, disable parallel jit. If None, disable parallel jit.


    """
    if on is None:
        on = True
    if parallel is None:
        parallel = False
    _FLAGSOBJ.USEJIT = on
    _FLAGSOBJ.PARALLEL = parallel
    _log.info(f"JIT is {'enabled' if on else 'disabled'}; parallel: {parallel}.")


__all__ = [
    "_FLAGSOBJ",
    "enable_jit",
    "set_log_level",
]
__version__ = "0.0.1"

_log.info(f"Initialized jetsontools with version {__version__}")

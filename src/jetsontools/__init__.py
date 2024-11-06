# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# ruff: noqa: E402, I001
"""
Package for bounding boxes and their operations.

Submodules
----------
info
    Tools for getting information about the Jetson device.

Classes
-------
Tegrastats
    Runs tegrastats in a separate process and stores output in a file.

Functions
---------
get_info
    Get information about the Jetson device.
get_data
    Parse the output of parse_tegrastats further to get specfic data.
get_powerdraw
    Parse the output of parse_tegrastats to get all energy information.
filter_data
    Filter the Tegrastats output by selections of timestamps.
set_log_level
    Set the log level for the jetsontools package.
parse_tegrastats
    Parse a file written by Tegrastats/tegrastats

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


level = os.getenv("JETSONTOOLS_LOG_LEVEL")
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

from . import info
from .info import get_info
from ._tegrastats import Tegrastats
from ._parsing import parse_tegrastats, get_data, get_powerdraw, filter_data

__all__ = [
    "Tegrastats",
    "filter_data",
    "get_data",
    "get_info",
    "get_powerdraw",
    "info",
    "parse_tegrastats",
    "set_log_level",
]
__version__ = "0.0.4"

_log.info(f"Initialized jetsontools with version {__version__}")

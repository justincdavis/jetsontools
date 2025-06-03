# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# ruff: noqa: E402, I001
"""
Package for bounding boxes and their operations.

Classes
-------
TegraStats
    Runs tegrastats in a separate process and stores output in a file.
TegraData
    Container for tegrastats data with parsing and filtering capabilities.
JetsonInfo
    Tools for getting information about the Jetson device.

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

# setup the logger first
from ._log import LOG as _LOG
from ._log import set_log_level

# then we can continue with the rest
from ._info import JetsonInfo, get_info
from ._tegradata import TegraData
from ._tegrastats import TegraStats
from ._parsing import parse_tegrastats, get_data, get_powerdraw, filter_data

__all__ = [
    "_LOG",
    "JetsonInfo",
    "TegraData",
    "TegraStats",
    "filter_data",
    "get_data",
    "get_info",
    "get_powerdraw",
    "parse_tegrastats",
    "set_log_level",
]
__version__ = "0.1.0"

_LOG.info(f"Initialized jetsontools with version {__version__}")

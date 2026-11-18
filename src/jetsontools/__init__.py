# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# ruff: noqa: I001
"""
Package for bounding boxes and their operations.

Classes
-------
:class:`TegraStats`
    Runs tegrastats in a separate process and stores output in a file.
:class:`TegraData`
    Container for tegrastats data with parsing and filtering capabilities.
:class:`SysfsReader`
    A sysfs file sampled in the background while TegraStats runs.
:class:`JetsonInfo`
    Tools for getting information about the Jetson device.

Functions
---------
:func:`get_info`
    Get information about the Jetson device.
:func:`get_data`
    Parse the output of parse_tegrastats further to get specfic data.
:func:`get_powerdraw`
    Parse the output of parse_tegrastats to get all energy information.
:func:`get_dla_utilization`
    Parse the output of parse_tegrastats to get DLA utilization.
:func:`get_dla_active_time`
    Get the total time each DLA core has been active.
:func:`filter_data`
    Filter the Tegrastats output by selections of timestamps.
:func:`set_log_level`
    Set the log level for the jetsontools package.
:func:`parse_tegrastats`
    Parse a file written by Tegrastats/tegrastats

"""

from __future__ import annotations

import importlib.metadata

# setup the logger first
from ._log import LOG as _LOG
from ._log import set_log_level

# then we can continue with the rest
from ._sysfs import SysfsReader, get_dla_active_time
from ._info import JetsonInfo, get_info
from ._tegradata import TegraData
from ._tegrastats import TegraStats
from ._parsing import (
    parse_tegrastats,
    get_data,
    get_powerdraw,
    get_dla_utilization,
    filter_data,
)

__all__ = [
    "_LOG",
    "JetsonInfo",
    "SysfsReader",
    "TegraData",
    "TegraStats",
    "filter_data",
    "get_data",
    "get_dla_active_time",
    "get_dla_utilization",
    "get_info",
    "get_powerdraw",
    "parse_tegrastats",
    "set_log_level",
]
try:
    __version__ = importlib.metadata.version("jetsontools")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

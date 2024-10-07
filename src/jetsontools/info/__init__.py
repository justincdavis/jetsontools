# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""
Tools for getting information about the Jetson device.

Classes
-------
JetsonInfo
    Class to store information about the Jetson device.

Functions
---------
get_info
    Get information about the Jetson device.

"""

from __future__ import annotations

from ._info import JetsonInfo, get_info

__all__ = ["JetsonInfo", "get_info"]

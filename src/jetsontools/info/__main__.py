# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Print information about the Jetson device."""

from __future__ import annotations

from ._info import get_info

if __name__ == "__main__":
    _ = get_info(verbose=True)

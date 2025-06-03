# Copyright (c) 2025 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Main CLI for jetsontools."""

from __future__ import annotations

import argparse

from ._info import get_info
from ._log import set_log_level


def _info(args: argparse.Namespace) -> None:  # noqa: ARG001
    get_info(verbose=True)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Utilities for Jetson devices.")

    # create the parent parser
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    # create subparser for each command
    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="command",
        required=True,
    )

    # info command
    info_parser = subparsers.add_parser(
        "info",
        help="Get information about the Jetson device.",
        parents=[parent_parser],
    )
    info_parser.set_defaults(func=_info)

    # parse args and call the function
    args, _ = parser.parse_known_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    set_log_level("INFO")
    _main()

# Copyright (c) 2025 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# ruff: noqa: S404, S603
"""Main CLI for jetsontools."""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

from ._info import get_info
from ._log import set_log_level
from ._tegrastats import TegraStats


def _info(args: argparse.Namespace) -> None:  # noqa: ARG001
    get_info(verbose=True)


def _profile(args: argparse.Namespace) -> None:
    output_path = Path(args.output) if args.output else None
    cmd_args = list(args.command or [])

    if not cmd_args:
        err_msg = "No command provided to run under profiling. Use --command followed by the command and its arguments."
        raise ValueError(err_msg)

    with TegraStats(
        output=output_path, interval=args.interval, readall=args.readall, sudo=args.sudo
    ):
        if args.spinup:
            time.sleep(args.spinup)

        subprocess.run(cmd_args, check=True)

        if args.cooldown:
            time.sleep(args.cooldown)


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

    # profile command
    profile_parser = subparsers.add_parser(
        "profile",
        help="Profile the a command.",
        parents=[parent_parser],
    )
    profile_parser.add_argument(
        "--output",
        type=str,
        help="The output file to save the profile data to.",
    )
    profile_parser.add_argument(
        "--interval",
        type=int,
        default=1,
        help="The interval to wait between samples in milliseconds.",
    )
    profile_parser.add_argument(
        "--spinup",
        type=int,
        help="The spinup time in seconds to wait before collecting data.",
    )
    profile_parser.add_argument(
        "--cooldown",
        type=int,
        help="The cooldown time in seconds to collect after the command is run.",
    )
    profile_parser.add_argument(
        "--readall",
        action="store_true",
        help="Read all data from tegrastats.",
    )
    profile_parser.add_argument(
        "--sudo",
        action="store_true",
        help="Run tegrastats with sudo.",
    )
    profile_parser.add_argument(
        "--command",
        nargs=argparse.REMAINDER,
        help="The command to execute while profiling.",
    )
    profile_parser.set_defaults(func=_profile)

    # parse args and call the function
    args, _ = parser.parse_known_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    set_log_level("INFO")
    _main()

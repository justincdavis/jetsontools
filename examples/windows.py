# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Showcase of named windows with Tegrastats."""

from __future__ import annotations

import argparse
import time

from jetsontools import TegraStats


def main() -> None:
    """Showcase power draw and energy of named windows."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=50)
    parser.add_argument("--duration", type=float, default=2.0)
    args = parser.parse_args()

    tegrastats = TegraStats(interval=args.interval)
    with tegrastats:
        with tegrastats.window("idle"):
            time.sleep(args.duration)
        with tegrastats.window("busy"):
            end = time.time() + args.duration
            while time.time() < end:
                pass

    data = tegrastats.data
    for name in ("idle", "busy"):
        window = data.window(name)
        print(f"{name}: {window.entries} entries in {window.duration:.2f} s")
        for rail, metric in window.powerdraw.items():
            watts = metric.mean / 1000
            print(f"  {rail}: {watts:.2f} W, {watts * window.duration:.2f} J")


if __name__ == "__main__":
    main()

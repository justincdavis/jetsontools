# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
"""Showcase of basic usage of Tegrastats and parsing output."""

from __future__ import annotations

import argparse
import time

from jetsontools import TegraData, TegraStats


def main() -> None:
    """Showcase basic usage of Tegrastats."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    tegrastats = TegraStats(output=args.output, interval=args.interval)

    t0 = time.time()
    with tegrastats:
        time.sleep(args.duration)
    t1 = time.time()
    total = t1 - t0

    print(f"Execution took: {round(total, 3)} for 5 seconds measured.")
    print("This is due to waiting for tegrastats process to open.")

    # should be roughly 1000 / interval * duration entries
    tegradata: TegraData = tegrastats.data

    print(
        f"Total of: {len(tegradata)} entries found, compared to {1000 / args.interval * args.duration}.",
    )
    print("Loss is expected.")

    # parse the energy
    power_data = tegradata.powerdraw
    for mname, metric in power_data.items():
        print(f"{mname}: {metric.mean} mW")


if __name__ == "__main__":
    main()

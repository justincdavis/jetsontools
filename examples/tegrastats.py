# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import time
from pathlib import Path

from jetsontools import Tegrastats, parse_tegrastats


def main() -> None:
    """Example showcasing Tegrastats."""
    example_path = Path(__file__).parent / "output.txt"

    interval = 5  # sample every 5 ms
    duration = 5  # 5 seconds of sampling

    t0 = time.time()
    with Tegrastats(example_path, interval):
        time.sleep(duration)
    t1 = time.time()
    total = t1 - t0

    print(f"Execution took: {round(total, 3)} for 5 seconds measured.")
    print("This is due to waiting for tegrastats process to open.")

    # should be roughly 1000 / interval * duration entries
    with example_path.open("r") as f:
        lines = f.readlines()

        print(f"Total of: {len(lines)} entries found, compared to {1000 / interval * duration}.")
        print("Loss is expected.")

    # parse the output
    output = parse_tegrastats(example_path)
    for entry in output:
        print(entry)


if __name__ == "__main__":
    main()

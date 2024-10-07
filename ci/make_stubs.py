# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import subprocess


def pyright_stubs():
    for module in ["numba"]:
        print(f"Making stubs for {module}")
        subprocess.run(["pyright", "--createstub", module])

def main():
    pyright_stubs()

if __name__ == "__main__":
    main()

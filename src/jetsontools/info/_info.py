# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# Adapted from: https://github.com/jetsonhacks/jetsonUtilities/blob/master/jetsonInfo.py
# ruff: noqa: S404, S603, T201
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path


class _Terminalcolors(Enum):
    """Terminal colors for printing."""

    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"


@dataclass
class JetsonInfo:
    """Class to store information about the Jetson device."""

    model: str
    l4t: str
    jetpack: str
    ubuntu: str | None
    kernel: str | None
    cuda: str
    cuda_arch: str
    opencv: str
    opencv_cuda: str
    cudnn: str
    tensorrt: str
    visionworks: str
    vpi: str
    vulkan: str


@lru_cache(maxsize=None)
def get_info(*, verbose: bool | None = None) -> JetsonInfo:
    """
    Get information about the Jetson device.

    Parameters
    ----------
    verbose : bool, optional
        If True, print additional information, by default None

    Returns
    -------
    dict[str, str]
        The information about the Jetson device.

    Raises
    ------
    RuntimeError
        If the subprocess stdout streams cannot be opened.

    """
    environment_vars: dict[str, str] = {}
    output: dict[str, str] = {}

    path0 = Path(__file__).parent.parent / "_scripts" / "jetson_variables.sh"
    path0 = path0.resolve()
    command0 = ["bash", "-c", f"source {path0} && env"]

    proc = subprocess.Popen(command0, stdout=subprocess.PIPE)
    if proc.stdout is None:
        err_msg = f"Cannot open subprocess: {command0}"
        raise RuntimeError(err_msg)
    for c0_line in proc.stdout:
        (key, _, value) = c0_line.partition(b"=")
        environment_vars[key.decode()] = value.decode()

    proc.communicate()

    # Jetson Model
    output["model"] = environment_vars["JETSON_MODEL"].strip()
    if verbose:
        print("NVIDIA " + output["model"])

    # L4T Version
    output["l4t"] = environment_vars["JETSON_L4T"].strip()
    output["jetpack"] = environment_vars["JETSON_JETPACK"].strip()
    if verbose:
        print(
            " L4T " + output["l4t"] + " [ JetPack " + output["jetpack"] + " ]",
        )
    # Ubuntu version
    output["ubuntu"] = "UNKNOWN"
    ubuntu_version_path = Path("/etc/os-release")
    if ubuntu_version_path.exists():
        with ubuntu_version_path.open("r") as ubuntu_version_file:
            ubuntu_version_file_text = ubuntu_version_file.read()
        for uvft_line in ubuntu_version_file_text.splitlines():
            if "PRETTY_NAME" in uvft_line:
                # PRETTY_NAME="Ubuntu 16.04 LTS"
                ubuntu_release = uvft_line.split('"')[1]
                output["ubuntu"] = ubuntu_release
                if verbose:
                    print("   " + ubuntu_release)
    else:
        if verbose:
            print(
                _Terminalcolors.FAIL.value
                + "Error: Unable to find Ubuntu Version"
                + _Terminalcolors.ENDC.value,
            )
            print("Reason: Unable to find file /etc/os-release")

    # Kernel Release
    output["kernel"] = "UNKNOWN"
    kernel_release_path = Path("/proc/version")
    if kernel_release_path.exists():
        with kernel_release_path.open("r") as version_file:
            version_file_text = version_file.read()
        kernel_release_array = version_file_text.split(" ")
        output["kernel"] = kernel_release_array[2]
        if verbose:
            print("   Kernel Version: " + kernel_release_array[2])
    else:
        if verbose:
            print(
                _Terminalcolors.FAIL.value
                + "Error: Unable to find Linux kernel version"
                + _Terminalcolors.ENDC.value,
            )
            print("Reason: Unable to find file /proc/version")

    path1 = Path(__file__).parent.parent / "_scripts" / "jetson_libraries.sh"
    path1 = path1.resolve()
    command1 = ["bash", "-c", f"source {path1} && env"]

    proc1 = subprocess.Popen(command1, stdout=subprocess.PIPE)
    if proc1.stdout is None:
        err_msg = f"Cannot open subprocess: {command1}"
        raise RuntimeError(err_msg)
    for c1_line in proc1.stdout:
        (key, _, value) = c1_line.partition(b"=")
        environment_vars[key.decode()] = value.decode()

    output["cuda"] = environment_vars["JETSON_CUDA"].strip()
    output["cuda_arch"] = environment_vars["JETSON_CUDA_ARCH_BIN"].strip()
    output["opencv"] = environment_vars["JETSON_OPENCV"].strip()
    output["opencv_cuda"] = environment_vars["JETSON_OPENCV_CUDA"].strip()
    output["cudnn"] = environment_vars["JETSON_CUDNN"].strip()
    output["tensorrt"] = environment_vars["JETSON_TENSORRT"].strip()
    output["visionworks"] = environment_vars["JETSON_VISIONWORKS"].strip()
    output["vpi"] = environment_vars["JETSON_VPI"].strip()
    output["vulkan"] = environment_vars["JETSON_VULKAN_INFO"].strip()

    if verbose:
        print(f" CUDA: {output['cuda']}")
        print(f" \tCUDA Arch: {output['cuda_arch']}")
        print(f" OpenCV: {output['opencv']}")
        print(f" \tOpenCV CUDA: {output['opencv_cuda']}")
        print(f" cuDNN: {output['cudnn']}")
        print(f" TensorRT: {output['tensorrt']}")
        print(f" Vision Works: {output['visionworks']}")
        print(f" VPI: {output['vpi']}")
        print(f" Vulcan: {output['vulkan']}")

    return JetsonInfo(
        model=output["model"],
        l4t=output["l4t"],
        jetpack=output["jetpack"],
        ubuntu=output["ubuntu"],
        kernel=output["kernel"],
        cuda=output["cuda"],
        cuda_arch=output["cuda_arch"],
        opencv=output["opencv"],
        opencv_cuda=output["opencv_cuda"],
        cudnn=output["cudnn"],
        tensorrt=output["tensorrt"],
        visionworks=output["visionworks"],
        vpi=output["vpi"],
        vulkan=output["vulkan"],
    )

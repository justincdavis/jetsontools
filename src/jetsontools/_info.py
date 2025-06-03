# Copyright (c) 2025 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# ruff: noqa: S404, S603, S607, T201, PLC0415
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from ._log import LOG

# source: https://developer.nvidia.com/embedded/jetpack-archive
L4T_TO_JETPACK: dict[str, str] = {
    # Jetpack 6.x
    "36.4.3": "6.2",
    "36.4.2": "6.2",
    "36.4.1": "6.1",
    "36.4.0": "6.1",
    "36.4": "6.1",
    "36.3.0": "6.0",
    "36.3": "6.0",
    "36.2.0": "6.0 DP",
    "36.2": "6.0 DP",
    # Jetpack 5.x
    "35.6.1": "5.1.5",
    "35.6.0": "5.1.4",
    "35.5.0": "5.1.3",
    "35.4.1": "5.1.2",
    "35.3.1": "5.1.1",
    "35.2.1": "5.1",
    "35.1.0": "5.0.2",
    "35.1": "5.0.2",
    "34.1.1": "5.0.1 DP",
    "34.1.0": "5.0 DP",
    "34.1": "5.0 DP",
    # Jetpack 4.x
    "32.7.6": "4.6.6",
    "32.7.5": "4.6.5",
    "32.7.4": "4.6.4",
    "32.7.3": "4.6.3",
    "32.7.2": "4.6.2",
    "32.7.1": "4.6.1",
    "32.6.1": "4.6",
    "32.5.1": "4.5.1",
    "32.5.0": "4.5",
    "32.5": "4.5",
    "32.4.4": "4.4.1",
    "32.4.3": "4.4",
    "32.4.2": "4.4 DP",
    "32.3.1": "4.3",
    "32.2.1": "4.2.3",
    "32.2": "4.2.1",
    "32.1": "4.2",
    "31.1": "4.1.1 DP",
    # Jetpack 3.x
    "28.5": "3.3.4",
    "28.4": "3.3.3",
    "28.3.2": "3.3.2",
    "28.3.1": "3.3.1",
    "28.2.1": "3.3",
    "28.2": "3.3",
    "28.1": "3.1",
    "27.1": "3.0",
    # Jetpack 2.x
    "24.2.1": "2.3.1",
    "24.2": "2.3",
    "24.1": "2.2.1",
    "23.2": "2.1",
    "23.1": "2.0",
}


def _run(cmd: list[str], *, strip: bool = True) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
        return out.strip() if strip else out
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def _dpkg_grep(pattern: str) -> str:
    out = _run(["dpkg", "-l"])
    for line in out.splitlines():
        if re.search(pattern, line):
            parts = line.split()
            if len(parts) >= 3:
                return parts[2].split("-")[0]
    return "FALSE"


def _read(path: str) -> str:
    try:
        data = Path(path).read_bytes().decode(errors="ignore")
        return data.replace("\x00", "").strip()
    except FileNotFoundError:
        return ""


def _dpkg_query(pkg: str) -> str:
    try:
        return subprocess.check_output(
            ["dpkg-query", "--showformat=${Version}", "--show", pkg],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def _cuda_version() -> str:
    ver_file = Path("/usr/local/cuda/version.txt")
    if ver_file.is_file():
        txt = ver_file.read_text().strip()
        return txt.replace("CUDA Version ", "")
    nvcc = Path("/usr/local/cuda/bin/nvcc")
    if nvcc.is_file():
        out = _run([str(nvcc), "--version"])
        m = re.search(r"V(\d+\.\d+\.\d+)", out)
        if m:
            return m.group(1)
    return "FALSE"


def _opencv_version_and_cuda() -> tuple[str, str]:
    try:
        import cv2  # type: ignore[import-untyped, import-not-found]
    except ImportError:
        return "FALSE", "FALSE"

    ver = cv2.__version__
    build_info = cv2.getBuildInformation()
    has_cuda = "TRUE" if re.search(r"Use Cuda\s*:\s*Yes", build_info) else "FALSE"
    return ver, has_cuda


def _cudnn_version() -> str:
    return _dpkg_grep(r"libcudnn[0-9]")


def _tensorrt_version() -> str:
    return _dpkg_grep(r"\stensorrt\s")


def _visionworks_version() -> str:
    return _dpkg_grep(r"libvisionworks")


def _vpi_version() -> str:
    return _dpkg_grep(r"\bvpi[0-9]\b")


def _vulkan_version() -> str:
    vkinfo = _run(["which", "vulkaninfo"])
    if vkinfo:
        out = _run(["vulkaninfo"])
        m = re.search(r"Vulkan Instance Version:\s*([^\s]+)", out)
        if m:
            return m.group(1)
    return "FALSE"


def _jetson_model() -> str:
    return _read("/sys/firmware/devicetree/base/model") or "UNKNOWN"


def _jetson_chip_id() -> str:
    return _read("/sys/module/tegra_fuse/parameters/tegra_chip_id")


def _jetson_soc() -> str:
    comp = _read("/proc/device-tree/compatible")
    return comp.split(",")[-1] if comp else ""


def _jetson_boardids() -> str:
    return _read("/proc/device-tree/nvidia,boardids")


def _codename_dts_module_carrier() -> tuple[str, str, str]:
    dtsfile = _read("/proc/device-tree/nvidia,dtsfilename")
    if not dtsfile:
        return "", "UNKNOWN", "UNKNOWN"

    try:
        codename = dtsfile.split("/hardware/nvidia/platform/")[1].split("/")[1]
    except (IndexError, ValueError):
        codename = ""

    # dts_base = os.path.basename(dtsfile)
    dts_base = Path(dtsfile).name
    boards = [
        f"P{m.group(1).rstrip('-')}" for m in re.finditer(r"p([0-9-]+)", dts_base)
    ]
    module = boards[0] if boards else "UNKNOWN"
    carrier = boards[1] if len(boards) > 1 else "UNKNOWN"
    return codename, module, carrier


def _cuda_arch_bin(model: str) -> str:
    if "Orin" in model:
        return "8.7"
    if "Xavier" in model:
        return "7.2"
    if "TX2" in model:
        return "6.2"
    if any(x in model for x in ("TX1", "Nano")):
        return "5.3"
    if "TK1" in model:
        return "3.2"
    return "NONE"


def _serial_number() -> str:
    return _read("/sys/firmware/devicetree/base/serial-number")


def _l4t_from_nv_tegra() -> tuple[str, str]:
    line = _read("/etc/nv_tegra_release")
    if not line:
        return "", ""
    rel = re.search(r"\bR(\d+)", line)
    rev = re.search(r"REVISION:\s*([0-9.]+)", line)
    return (rel.group(1) if rel else "", rev.group(1) if rev else "")


def _l4t_from_dpkg() -> tuple[str, str]:
    ver = _dpkg_query("nvidia-l4t-core")
    if not ver:
        return "", ""
    main = ver.split("-")[0]
    rel, _, rev = main.partition(".")
    return rel, rev


def _jetson_l4t() -> tuple[str, str, str]:
    rel, rev = _l4t_from_nv_tegra()
    if not rel:
        rel, rev = _l4t_from_dpkg()
    if not rel:
        rel, rev = "N", "N.N"
    return rel, rev, f"{rel}.{rev}"


def _jetson_jetpack(l4t: str) -> str:
    return L4T_TO_JETPACK.get(l4t, "UNKNOWN")


@dataclass
class JetsonInfo:
    """Class to store information about the Jetson device."""

    # core hardware info
    model: str = field(repr=True)
    jetpack: str = field(repr=True)
    l4t: str = field(repr=True)
    cuda_arch: str = field(repr=True)

    # software info
    cuda: str = field(repr=True)
    cudnn: str = field(repr=True)
    tensorrt: str = field(repr=True)
    visionworks: str = field(repr=True)
    vpi: str = field(repr=True)
    opencv: str = field(repr=True)
    opencv_cuda: str = field(repr=True)
    vulkan: str = field(repr=True)

    # board info
    chip_id: str = field(repr=False)
    soc: str = field(repr=False)
    boardids: str = field(repr=False)
    codename: str = field(repr=False)
    module: str = field(repr=False)
    carrier: str = field(repr=False)
    serial_number: str = field(repr=False)


@lru_cache(maxsize=1)
def _get_info() -> JetsonInfo:
    cuda_version = _cuda_version()
    opencv_version, opencv_has_cuda = _opencv_version_and_cuda()
    cudnn_version = _cudnn_version()
    tensorrt_version = _tensorrt_version()
    visionworks_version = _visionworks_version()
    vpi_version = _vpi_version()
    vulkan_version = _vulkan_version()
    jetson_model = _jetson_model()
    jetson_chip_id = _jetson_chip_id()
    jetson_soc = _jetson_soc()
    jetson_boardids = _jetson_boardids()
    codename, module, carrier = _codename_dts_module_carrier()
    cuda_arch = _cuda_arch_bin(jetson_model)
    serial_number = _serial_number()
    _, _, l4t = _jetson_l4t()
    jetpack = _jetson_jetpack(l4t)

    return JetsonInfo(
        model=jetson_model,
        jetpack=jetpack,
        l4t=l4t,
        cuda=cuda_version,
        cuda_arch=cuda_arch,
        cudnn=cudnn_version,
        tensorrt=tensorrt_version,
        visionworks=visionworks_version,
        vpi=vpi_version,
        opencv=opencv_version,
        opencv_cuda=opencv_has_cuda,
        vulkan=vulkan_version,
        chip_id=jetson_chip_id,
        soc=jetson_soc,
        boardids=jetson_boardids,
        codename=codename,
        module=module,
        carrier=carrier,
        serial_number=serial_number,
    )


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
    jetson_info = _get_info()

    if verbose:
        LOG.info(f"Jetson model: {jetson_info.model}")
        LOG.info(f"Jetpack: {jetson_info.jetpack}")
        LOG.info(f"L4T: {jetson_info.l4t}")
        LOG.info(f"CUDA: {jetson_info.cuda}")
        LOG.info(f"CUDA arch: {jetson_info.cuda_arch}")
        LOG.info(f"CUDNN: {jetson_info.cudnn}")
        LOG.info(f"TensorRT: {jetson_info.tensorrt}")
        LOG.info(f"VisionWorks: {jetson_info.visionworks}")
        LOG.info(f"VPI: {jetson_info.vpi}")
        LOG.info(f"OpenCV: {jetson_info.opencv}")
        LOG.info(f"OpenCV CUDA: {jetson_info.opencv_cuda}")
        LOG.info(f"Vulkan: {jetson_info.vulkan}")
        LOG.info(f"Chip ID: {jetson_info.chip_id}")
        LOG.info(f"SOC: {jetson_info.soc}")
        LOG.info(f"Board IDs: {jetson_info.boardids}")
        LOG.info(f"Codename: {jetson_info.codename}")
        LOG.info(f"Module: {jetson_info.module}")
        LOG.info(f"Carrier: {jetson_info.carrier}")
        LOG.info(f"Serial number: {jetson_info.serial_number}")

    return jetson_info

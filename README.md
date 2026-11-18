# jetsontools

[![](https://img.shields.io/pypi/pyversions/jetsontools.svg)](https://pypi.org/pypi/jetsontools/)
![PyPI](https://img.shields.io/pypi/v/jetsontools.svg?style=plastic)
[![CodeFactor](https://www.codefactor.io/repository/github/justincdavis/jetsontools/badge)](https://www.codefactor.io/repository/github/justincdavis/jetsontools)

![MyPy](https://github.com/justincdavis/jetsontools/actions/workflows/mypy.yaml/badge.svg?branch=main)
![Ruff](https://github.com/justincdavis/jetsontools/actions/workflows/ruff.yaml/badge.svg?branch=main)
![PyPI Build](https://github.com/justincdavis/jetsontools/actions/workflows/build-check.yaml/badge.svg?branch=main)
[![Docs](https://github.com/justincdavis/jetsontools/actions/workflows/docs.yaml/badge.svg?branch=main)](https://justincdavis.github.io/jetsontools/)

Tools for measuring and inspecting NVIDIA Jetson devices. jetsontools runs `tegrastats` in the background while your code runs, parses its output into power, utilization and other metrics, samples sysfs counters and the INA3221 power rails without sudo, and reports the board and software versions.

## Features

- `TegraStats` runs `tegrastats` in a separate process and writes its output to a file, or a temporary file
- `TegraData` parses the log into power draw (`powerdraw`), DLA utilization (`dla_utilization`) and any other field (`parse`), with timestamp filtering and CSV export
- Named windows: `TegraStats.window` marks a block of code, `TegraData.window` returns the data collected in it, with its `duration` and `span`
- Sysfs readers, sampled without sudo: time each DLA core, the GPU, the PVA and the media engines were powered (`read_sysfs_dla`, `read_sysfs_gpu`, `read_sysfs_pva`, `read_sysfs_media`), and any sysfs file with `SysfsReader`
- INA3221 power rails (`read_sysfs_power`), sampled within an I2C read budget shared with tegrastats, and integrated into energy per rail with `TegraData.sysfs_energy`
- `get_dla_active_time` reads how long each DLA core has been powered, without tegrastats or sudo
- Parses logs from Orin AGX, Orin NX, Xavier AGX and Xavier NX
- `get_info` and `python3 -m jetsontools info` report the board, JetPack, L4T, CUDA, cuDNN, TensorRT and other versions
- `python3 -m jetsontools profile` records tegrastats while another command runs

## Installation

```bash
pip install jetsontools
```

Or the latest from git:

```bash
pip install "git+https://github.com/justincdavis/jetsontools.git"
```

Supported versions:

- Python 3.8 to 3.15
- Recording needs a Jetson with `tegrastats` (part of JetPack). Parsing logs works on any machine

Additional extras:

```bash
# pytest, for the mocked test suite
pip install "jetsontools[test]"

# Sphinx and the furo theme, to build the documentation
pip install "jetsontools[docs]"

# Development
pip install "jetsontools[dev]"
```

## Quick Start

### Recording tegrastats with windows

`TegraStats` records tegrastats while the context is open. `window` marks named blocks of code, and `TegraData.window` returns the data collected during one:

```python
import time

from jetsontools import TegraStats

with TegraStats(interval=50) as tegrastats:
    with tegrastats.window("idle"):
        time.sleep(2)
    with tegrastats.window("inference"):
        run_model()

data = tegrastats.data
inference = data.window("inference")
print(f"{inference.entries} entries in {inference.duration:.2f} s")
for rail, metric in inference.powerdraw.items():
    watts = metric.mean / 1000
    print(f"{rail}: {watts:.2f} W, {watts * inference.duration:.2f} J")
```

Pass `output="run.log"` to keep the log; `TegraData("run.log")` parses it again later, on any machine.

### Sysfs counters, power and energy

The `read_sysfs_*` flags sample sysfs in a separate process, without sudo. Counters are read at the edges of each window, so their change over a window is exact:

```python
from jetsontools import TegraStats, get_dla_active_time

with TegraStats(interval=100, read_sysfs_dla=True, read_sysfs_power=True) as tegrastats:
    with tegrastats.window("inference"):
        run_model()

inference = tegrastats.data.window("inference")
print(inference.sysfs_counters)  # ms each DLA core was powered, by core (nvdla0, nvdla1)
print(inference.sysfs_energy)    # mJ per INA3221 rail, plus TOTAL

# or read the DLA counters directly
print(get_dla_active_time())
```

`sysfs_energy["TOTAL"]` sums every INA3221 rail, including `VIN_SYS_5V0` on an Orin AGX, which tegrastats-based `powerdraw` places in `VIN_TOTAL` rather than `VDD_TOTAL`. On an Orin AGX the sysfs rail energy matched the per-rail power from tegrastats within about 0.1%.

### Command Line

```bash
# board, JetPack, CUDA, TensorRT, ... versions
python3 -m jetsontools info

# record tegrastats every 100 ms while a command runs
python3 -m jetsontools profile --output profile.log --interval 100 --command python3 infer.py
```

See the [CLI reference](https://justincdavis.github.io/jetsontools/cli.html) for all options.

## Documentation

For detailed documentation, visit the [documentation site](https://justincdavis.github.io/jetsontools/):

- [Installation](https://justincdavis.github.io/jetsontools/installation.html)
- [Usage Guide](https://justincdavis.github.io/jetsontools/usage.html): tegrastats logging, windows, sysfs counters, power and energy
- [API Reference](https://justincdavis.github.io/jetsontools/api.html)
- [CLI Reference](https://justincdavis.github.io/jetsontools/cli.html)
- [Changelog](https://justincdavis.github.io/jetsontools/changelog.html)

## Examples

Check out the [examples directory](examples/) for scripts that run on a Jetson:

- Basic recording and power draw (`tegrastats.py`)
- Power and energy of named windows (`windows.py`)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

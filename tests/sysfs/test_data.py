# Copyright (c) 2026 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
from __future__ import annotations

import io

from jetsontools import TegraData
from tests.sysfs._helpers import _data, _tegrastats_log


def test_sysfs_data() -> None:
    data = _data({"early": (1.5, 3.0)})
    assert data.sysfs_kinds["nvdla0"] == "counter"
    assert data.sysfs_counters == {"nvdla0": 800.0}
    assert data.sysfs_gauges["temp"].raw == [100.0, 200.0, 300.0, 400.0]
    early = data.window("early")
    assert early.span == (1.5, 3.0)
    assert early.sysfs_counters == {"nvdla0": 300.0}
    assert early.sysfs_gauges["temp"].mean == 250.0


def test_sysfs_data_filtered() -> None:
    data = _data()
    data.filter([(0.5, 2.5)])
    assert data.sysfs_counters == {"nvdla0": 300.0}
    data.filter([(0.5, 2.5), (2.9, 3.6)])
    assert data.sysfs_counters == {"nvdla0": 350.0}
    assert data.sysfs_gauges["temp"].raw == [100.0, 200.0, 300.0]
    data.filter([(5.0, 6.0)])
    assert data.sysfs_counters == {}
    assert data.sysfs_gauges == {}
    assert data.sysfs_energy == {}


def test_sysfs_data_window_filter() -> None:
    window = _data({"late": (2.5, 4.5)}).window("late")
    window.filter([(0.0, 3.2)])
    assert window.sysfs_counters == {"nvdla0": 0.0}


def test_no_sysfs_data() -> None:
    data = TegraData(io.StringIO(_tegrastats_log([1.0, 2.0])))
    assert data.sysfs_counters == {}
    assert data.sysfs_gauges == {}

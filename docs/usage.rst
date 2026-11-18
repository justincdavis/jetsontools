.. _usage:

Usage Guide
===========

This guide walks through the main workflows: recording tegrastats, reading the
results, measuring named windows, sampling sysfs counters, and measuring power
and energy from the INA3221 power rails.

Recording tegrastats
--------------------

:class:`~jetsontools.TegraStats` runs ``tegrastats`` in a separate process.
Use it as a context manager around the code to measure. Entering the context
waits until tegrastats writes its first line, and leaving it runs
``tegrastats --stop``.

.. code-block:: python

    import time

    from jetsontools import TegraStats

    tegrastats = TegraStats(interval=50)
    with tegrastats:
        time.sleep(5)

    data = tegrastats.data
    print(f"{data.entries} entries over {data.duration:.2f} s")

``interval`` is the tegrastats interval in milliseconds, 1000 by default. Each
line is prefixed with the ``time.time()`` at which it was read, which is what
filtering and windows use. Without ``output`` the log is kept in a temporary
file that lives as long as the ``TegraStats`` object, so ``data`` can be read
after the context exits. Pass ``output`` to keep the log:

.. code-block:: python

    tegrastats = TegraStats(output="run.log", interval=100)

Other options:

- ``readall=True`` passes ``--readall`` to tegrastats, which reports more
  fields, depending on the board, at the cost of more CPU.
- ``sudo=True`` runs ``sudo tegrastats``. Some fields, such as the DLA cores,
  are only reported with sudo.
- ``reset()`` stops tegrastats and starts it again.

Reading the data
----------------

``TegraStats.data`` returns a :class:`~jetsontools.TegraData`. It can also be
created from any log file, including one written by ``tegrastats --logfile``
or copied off another device:

.. code-block:: python

    from jetsontools import TegraData

    data = TegraData("run.log")

``data.data`` holds one ``dict[str, str]`` per line, with the raw values as
strings. Logs written by ``TegraStats`` have a ``timestamp`` field. Names are
upper case, and temperatures such as ``cpu@49.01C`` become ``CPU_TEMP``. See
:func:`~jetsontools.parse_tegrastats` for an example entry.

The parsed metrics are ``Metric`` objects with the ``raw`` values and their
``mean``, ``median``, ``min`` and ``max``:

.. code-block:: python

    # power draw in mW by rail, plus VDD_TOTAL and VIN_TOTAL
    for rail, metric in data.powerdraw.items():
        print(f"{rail}: {metric.mean:.0f} mW")

    # DLA utilization (%) by core, only reported by tegrastats with sudo
    for core, metric in data.dla_utilization.items():
        print(f"{core}: {metric.mean:.1f} %")

    # any other field, with a function parsing its string value
    gpu = data.parse(["GR3D_FREQ"], lambda value: float(value.split("%")[0]))

``powerdraw`` reads every field containing ``VDD`` or ``VIN``, using the
current reading of each ``current/average`` pair. ``VDD_TOTAL`` sums the
``VDD`` rails (leaving out ``VDD_IN``) and ``VIN_TOTAL`` sums the ``VIN``
rails. On an Orin AGX, for example, ``VIN_SYS_5V0`` is in ``VIN_TOTAL`` but not
in ``VDD_TOTAL``.

``dla_utilization`` reports the cores as ``NVDLA0`` and ``NVDLA1``; a core
reported as ``off`` counts as 0%. It is empty when tegrastats did not report
the DLA cores.

``save_as_csv`` writes the entries (or the filtered entries) to a CSV file, and
raises ``ValueError`` when there is nothing to write.

Supported logs
~~~~~~~~~~~~~~

The parser is tested against recorded logs from the Orin AGX (32 GB and 64 GB),
Orin NX 16 GB, Xavier AGX 16 GB and Xavier NX 8 GB. On the Xavier AGX,
tegrastats writes no date or time and reports its rails without units, so the
parser:

- accepts lines without ``DATE`` and ``TIME``
- reads ``MTS fg X% bg Y%`` as ``MTS_FG`` and ``MTS_BG``
- renames the rails ``GPU``, ``CPU``, ``SOC``, ``CV``, ``VDDRQ`` and ``SYS5V``
  to ``VDD_GPU``, ``VDD_CPU``, ``VDD_SOC``, ``VDD_CV``, ``VDDRQ`` and
  ``VIN_SYS5V`` in mW, so they no longer overwrite the CPU and GPU utilization
  fields and are included in ``powerdraw``

Named windows
-------------

``TegraStats.window`` marks a block of code with a name, and
``TegraData.window`` returns the data collected during it:

.. code-block:: python

    with TegraStats(interval=50) as tegrastats:
        with tegrastats.window("idle"):
            time.sleep(2)
        with tegrastats.window("inference"):
            run_model()

    data = tegrastats.data
    print(data.windows)  # {"idle": (start, stop), "inference": (start, stop)}

    inference = data.window("inference")
    print(inference.entries, inference.duration, inference.span)
    for rail, metric in inference.powerdraw.items():
        watts = metric.mean / 1000
        print(f"{rail}: {watts:.2f} W, {watts * inference.duration:.2f} J")

- ``window`` returns a new ``TegraData`` with only the entries inside the
  window, and leaves the original unchanged. It uses all the data, regardless
  of ``filter``.
- ``duration`` of a window is its length in seconds, and ``span`` is its
  ``(start, stop)`` timestamps. For data that is not a window, ``duration`` is
  the time between the first and last entry and ``span`` is ``None``.
- Reusing a name replaces the window.
- An unknown name raises ``KeyError``. A window with no tegrastats entries
  inside it raises ``ValueError``: use a longer window or a shorter interval.

Filtering by timestamps
~~~~~~~~~~~~~~~~~~~~~~~

``filter`` selects the entries within a list of ``(start, stop)``
``time.time()`` ranges. ``powerdraw``, ``dla_utilization``, ``parse``,
``save_as_csv`` and the sysfs properties then use only those entries:

.. code-block:: python

    data.filter([(t0, t1), (t2, t3)])
    print(data.powerdraw["VDD_TOTAL"].mean)

Filtering needs the timestamps written by ``TegraStats``, and raises
``KeyError`` on a plain tegrastats log. :func:`~jetsontools.filter_data` does
the same on parsed entries.

Sysfs counters
--------------

Alongside tegrastats, ``TegraStats`` can sample sysfs files in another
process. These files are readable without sudo. The flags below add readers
for the runtime power management counter (``power/runtime_active_time``) of
each engine, the milliseconds it has been powered:

``read_sysfs_dla``
    Each DLA core, as ``nvdla0`` and ``nvdla1``. A core stays powered about 0.5
    to 0.6 seconds after its last task, and about 110 ms of each power up is not
    counted.
``read_sysfs_gpu``
    The GPU, as ``gpu``. Powered is not busy: the GPU stays powered until it
    rail gates, about 1.6 seconds after its last work on Orin, even with a CUDA
    context open.
``read_sysfs_pva``
    Each PVA, as ``pva0`` and so on. Powered is not busy, and may include idle
    time while an application holds the PVA.
``read_sysfs_media``
    The VIC, NVENC, NVDEC, NVJPG and OFA engines, as ``vic``, ``nvenc``,
    ``nvdec``, ``nvjpg``, ``nvjpg1``, ``ofa`` and so on. Each stays powered for
    its autosuspend delay after its last task.

A flag that finds no files logs a warning. ``TegraStats.sysfs`` lists the
readers in use, with their resolved paths and intervals.

``TegraData.sysfs_counters`` gives the change of each counter between the first
and last sample within the data, a filter range (summed over the ranges) or a
window. ``TegraStats.window`` reads the counters when the block starts and
ends, so their change over a window is exact:

.. code-block:: python

    with TegraStats(interval=100, read_sysfs_dla=True) as tegrastats:
        with tegrastats.window("dla"):
            run_on_dla()

    counters = tegrastats.data.window("dla").sysfs_counters
    print(counters["nvdla0"], counters["nvdla1"])  # ms each core was powered

Because an engine stays powered after its last task, that time is counted in
the next window when the gap between two windows is shorter than the delay.

On an Orin AGX, the ``runtime_active_time`` of ``nvdla0`` only moves while that
core runs work, so its change shows which DLA cores were used.

Reading the counters directly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:func:`~jetsontools.get_dla_active_time` reads the same DLA counters once,
without tegrastats or sudo. The difference of two calls measures which cores
ran work:

.. code-block:: python

    from jetsontools import get_dla_active_time

    before = get_dla_active_time()
    run_on_dla()
    after = get_dla_active_time()
    print({core: after[core] - before[core] for core in after})

It returns an empty dict on a device without DLA cores.

Custom sysfs files
~~~~~~~~~~~~~~~~~~

:class:`~jetsontools.SysfsReader` samples any sysfs file holding a number:

.. code-block:: python

    from jetsontools import SysfsReader, TegraStats

    readers = [
        SysfsReader("thermal0", "/sys/class/thermal/thermal_zone0/temp"),
        SysfsReader("thermal1", "/sys/class/thermal/thermal_zone1/temp", interval=10),
    ]
    with TegraStats(interval=100, sysfs=readers) as tegrastats:
        run_model()

    print(tegrastats.data.sysfs_gauges["thermal0"].mean)

- ``name`` is made of letters, digits, ``_``, ``.`` and ``-``, and must be
  unique within a ``TegraStats`` (``ValueError`` otherwise).
- ``path`` is a path or a glob pattern matching exactly one file. A reader
  without exactly one readable, numeric file is skipped with a warning.
- ``kind`` is ``"gauge"`` (default), an instantaneous value reported by
  ``TegraData.sysfs_gauges`` as a ``Metric``, or ``"counter"``, a cumulative
  value reported by ``TegraData.sysfs_counters`` as its change.
- ``interval`` is the milliseconds between samples, at least 1 ms. When it is
  ``None``, a counter is sampled at the tegrastats interval. For a gauge,
  ``TegraStats`` measures the median time between changes of the value when it
  is created, polling the file at up to 1 kHz for 0.2 seconds, and samples at
  that rate, between 1 ms and the tegrastats interval.

The samples go to ``<output>.sysfs`` next to the tegrastats log when ``output``
is set, and to a temporary file otherwise. ``TegraData(..., sysfs=path)``
reads such a file back.

Power and energy
----------------

``read_sysfs_power=True`` samples the voltage (mV) and current (mA) of each
INA3221 power rail as the gauges ``<rail>.mV`` and ``<rail>.mA``, named by the
rail labels the driver reports. ``TegraData.sysfs_energy`` multiplies them into
power and integrates it over time, within the data, each filter range or the
window:

.. code-block:: python

    with TegraStats(interval=100, read_sysfs_power=True) as tegrastats:
        with tegrastats.window("inference"):
            run_model()

    inference = tegrastats.data.window("inference")
    for rail, millijoules in inference.sysfs_energy.items():
        print(f"{rail}: {millijoules / 1000:.3f} J")
    print(inference.sysfs_gauges["VDD_GPU_SOC.mA"].mean)

``sysfs_energy`` gives millijoules by rail, plus ``TOTAL``, the sum over the
rails. It is empty when no rails were sampled.

``TOTAL`` sums every INA3221 rail. On an Orin AGX that includes
``VIN_SYS_5V0``, which tegrastats reports separately: ``powerdraw`` places it
in ``VIN_TOTAL`` and leaves it out of ``VDD_TOTAL``. Compare ``TOTAL`` with
``VDD_TOTAL + VIN_TOTAL``, or the per-rail values with each other.

On an Orin AGX, the energy from the sysfs rails matched the per-rail power
reported by tegrastats within about 0.1%.

I2C read budget
~~~~~~~~~~~~~~~

Each rail read is an I2C transfer, and tegrastats reads the same rails every
interval. ``TegraStats`` keeps tegrastats and its own readers to at most 200
reads per second together. With ``N`` rails, each sample takes ``2N`` reads,
and the rails are sampled every 50 ms, or less often:

.. code-block:: text

    max(50, 2N * 1000 / (200 - 2N * 1000 / interval)) ms

For example, with 4 rails the rails are sampled every 50 ms with a tegrastats
interval of 1000 ms, and every 200 ms with an interval of 50 ms. When
tegrastats alone leaves less than one sample per second, ``TegraStats`` logs a
warning and samples the rails once per second. The limit covers one
``TegraStats`` only.

Device information
------------------

:func:`~jetsontools.get_info` returns a :class:`~jetsontools.JetsonInfo` with
the board name, model, JetPack and L4T versions, CUDA architecture, memory size
and bitrate, and the CUDA, cuDNN, TensorRT, VisionWorks, VPI, OpenCV and Vulkan
versions. ``get_info(verbose=True)`` also logs each field at INFO level.

.. code-block:: python

    from jetsontools import get_info

    info = get_info()
    print(info.name, info.jetpack, info.cuda)

Logging
-------

jetsontools logs through the ``jetsontools`` logger, at ``WARNING`` by default.
:func:`~jetsontools.set_log_level` changes the level:

.. code-block:: python

    import jetsontools

    jetsontools.set_log_level("DEBUG")

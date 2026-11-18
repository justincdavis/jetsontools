Welcome to jetsontools
======================

**jetsontools** is a Python package for measuring and inspecting NVIDIA Jetson
devices. It runs ``tegrastats`` in the background while your code runs, parses
its output into power, utilization and other metrics, samples sysfs counters and
the INA3221 power rails without sudo, and reports the board and software versions.

Features
--------

- ``TegraStats`` runs ``tegrastats`` in a separate process and writes its output to a file, or a temporary file
- ``TegraData`` parses the log into per-entry fields, power draw (``powerdraw``), DLA utilization (``dla_utilization``) and any other field (``parse``), with timestamp filtering and CSV export
- Named windows: ``TegraStats.window`` marks a block of code, ``TegraData.window`` returns the data collected in it, with its ``duration`` and ``span``
- Sysfs readers, sampled in a separate process without sudo: time each DLA core, the GPU, the PVA and the media engines were powered (``read_sysfs_dla``, ``read_sysfs_gpu``, ``read_sysfs_pva``, ``read_sysfs_media``), and any sysfs file with ``SysfsReader``
- INA3221 power rails (``read_sysfs_power``), sampled within an I2C read budget shared with tegrastats, and integrated into energy per rail with ``TegraData.sysfs_energy``
- ``get_dla_active_time`` reads how long each DLA core has been powered, without tegrastats or sudo
- Parses logs from Orin AGX, Orin NX, Xavier AGX and Xavier NX
- ``get_info`` and ``python3 -m jetsontools info`` report the board, JetPack, L4T, CUDA, cuDNN, TensorRT and other versions
- ``python3 -m jetsontools profile`` records tegrastats while another command runs

Quick Start
-----------

.. code-block:: python

    from jetsontools import TegraStats

    with TegraStats(interval=50) as tegrastats:
        with tegrastats.window("inference"):
            run_model()

    inference = tegrastats.data.window("inference")
    for rail, metric in inference.powerdraw.items():
        print(f"{rail}: {metric.mean:.0f} mW")

Documentation
-------------

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   Installation <installation>
   Usage Guide <usage>
   API Reference <api>
   CLI Reference <cli>
   Examples <examples>
   Changelog <changelog>

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Getting Help
------------

- View the :ref:`Usage Guide <usage>` for the common workflows
- Browse the :ref:`Examples <examples>` for code samples
- Explore the :ref:`API Reference <api>` for detailed documentation
- Report issues on `GitHub <https://github.com/justincdavis/jetsontools/issues>`_

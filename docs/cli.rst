.. _cli:

CLI Reference
=============

jetsontools provides a command-line interface, run as a module:

.. code-block:: console

    $ python3 -m jetsontools --help

Overview
--------

* ``info``: Print information about the Jetson device
* ``profile``: Record tegrastats while a command runs

Both commands accept ``--verbose``, which currently has no effect.

Info
~~~~

Print the board name, model, JetPack and L4T versions, CUDA, CUDA
architecture, memory size and bitrate, cuDNN, TensorRT, VisionWorks, VPI,
OpenCV, Vulkan, and the board identifiers, one per line. This is
:func:`~jetsontools.get_info` with ``verbose=True``.

.. code-block:: console

    $ python3 -m jetsontools info

Profile
~~~~~~~

Run a command while recording tegrastats, using :class:`~jetsontools.TegraStats`.

.. code-block:: console

    # record every 100 ms while a script runs
    $ python3 -m jetsontools profile --output profile.log --interval 100 \
        --command python3 infer.py --model model.engine

    # record 2 s before and 5 s after the command, with sudo
    $ python3 -m jetsontools profile --output profile.log --interval 50 \
        --spinup 2 --cooldown 5 --sudo --command ./benchmark

Options
^^^^^^^

* ``--output``: File to write the tegrastats log to. Without it, the log is
  written to a temporary file and discarded
* ``--interval``: Milliseconds between tegrastats samples (default: 1)
* ``--spinup``: Seconds to record before running the command
* ``--cooldown``: Seconds to keep recording after the command exits
* ``--readall``: Pass ``--readall`` to tegrastats
* ``--sudo``: Run tegrastats with sudo
* ``--command``: The command to run and its arguments. Everything after
  ``--command`` is passed to the command, so it must come last (required)

The command runs with ``check=True``, so a non-zero exit status raises an
error. The log can be read back with :class:`~jetsontools.TegraData`:

.. code-block:: python

    from jetsontools import TegraData

    data = TegraData("profile.log")
    print(data.powerdraw["VDD_TOTAL"].mean)

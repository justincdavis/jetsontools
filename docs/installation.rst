.. _installation:

Installation
============

This guide will help you install jetsontools. The recommended method is to
install jetsontools into a virtual environment to ensure dependency isolation.

System Requirements
-------------------

- Python 3.8 to 3.15
- Linux on an NVIDIA Jetson device, with ``tegrastats`` on the ``PATH`` (it ships with JetPack)

Parsing tegrastats logs and the ``TegraData`` API work on any machine, which is
useful for analyzing logs copied off a device. Recording data with
``TegraStats``, the sysfs readers and ``get_info`` need a Jetson.

Basic Installation
------------------

jetsontools depends only on ``typing_extensions``:

.. code-block:: console

    $ pip install jetsontools

To get the latest changes, install from git:

.. code-block:: console

    $ pip install "git+https://github.com/justincdavis/jetsontools.git"

For development, install from source:

.. code-block:: console

    $ git clone https://github.com/justincdavis/jetsontools.git
    $ cd jetsontools
    $ pip install -e ".[dev]"

The version comes from git tags (setuptools-scm), so a source install needs the
git history; a shallow clone without tags installs as version ``0.0.0``.

Optional Dependencies
---------------------

jetsontools provides several optional dependency groups that can be installed
using pip's extras feature:

Testing
~~~~~~~

.. code-block:: console

    $ pip install "jetsontools[test]"

This installs pytest. The tests mock tegrastats and sysfs, so they run on any
machine.

Documentation
~~~~~~~~~~~~~

.. code-block:: console

    $ pip install "jetsontools[docs]"

This installs Sphinx, the furo theme, sphinx-design and MyST. Build the
documentation with ``ci/make_docs.sh`` (or ``make docs``), which writes the HTML
to ``docs/_build/html``.

Development Tools
~~~~~~~~~~~~~~~~~

.. code-block:: console

    $ pip install "jetsontools[dev]"

This installs:

- The ``ci``, ``test`` and ``docs`` extras (ruff, mypy, pyupgrade, pytest, Sphinx)
- twine, wheel and pyclean

Permissions
-----------

- ``TegraStats(sudo=True)`` runs ``sudo tegrastats``, which needs sudo without a
  password prompt. tegrastats only reports some fields, such as the DLA cores
  (``NVDLA0``, ``NVDLA1``), when run with sudo.
- The sysfs readers (``read_sysfs_*``, ``SysfsReader``, ``get_dla_active_time``)
  read world-readable files and do not need sudo.

Getting Started
---------------

After installation, verify your setup on a Jetson:

.. code-block:: console

    $ python3 -m jetsontools info

For the common workflows, see the :ref:`Usage Guide <usage>`.

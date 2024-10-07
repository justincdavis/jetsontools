.. _installation:

Installation
------------

There are multiple methods for installing jetsontools. The recommended method is
to install jetsontools into a virtual environment. This will ensure that the
dependencies are isolated from other Python projects you may be
working on.

Methods
^^^^^^^
#. Pip:

   .. code-block:: console

      $ pip3 install jetsontools

#. From source:

   .. code-block:: console

      $ git clone https://github.com/justincdavis/jetsontools.git
      $ cd jetsontools
      $ pip3 install .

Optional Dependencies
^^^^^^^^^^^^^^^^^^^^^

#. dev:

   .. code-block:: console

      $ pip3 install jetsontools[dev]
   
   This will install dependencies allowing a full development environment.
   All CI and tools used for development will be installed and can be run.

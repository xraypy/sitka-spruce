.. include:: _config.rst

Downloading and Installation
====================================


Prerequisites
~~~~~~~~~~~~~~~

The current version of Sitka Spruce is |release|, released in August, 2026.

This is an early release, and development is still active.  This
version is suitable for testing but may not be ready for production
use.  Comments and suggestions are welcome.

Sitka Spruce requires Python 3.11 or higher and wxPython 4.2.4.  Other
required packages and minmimum versions are listed in the
`pyproject.toml` file in the source code repository.  All of the
required dependencies are available from `pip` or on `conda` channels.

As an important note is that `wxPython`_ is required.  This package is
available on `PyPI`_ for MacOS and Windows. For Linux, the libraries
that `wxPython`_ needs are not always pre-installed, and cannot easily
bundled in the `PyPI`_ package.  This is a good reason for using an
Anaconda Python environment, which provides `wxPython` and the
libraries it needs through the `conda-forge` repository.


Installation
~~~~~~~~~~~~~~~~

For Python installations that have a working `wxPython`_ package, the
latest version (|release|) is available from `PyPI`_ and can be
installed with::

   pip install sitka-spruce


To install into a new environment in an existing Anaconda Python
installation, use

.. code:: bash

   conda create -y --name sitka python>=3.13
   conda activate sitka
   conda install -y -c conda-forge numpy scipy matplotlib h5py>=3.13 wxpython>=4.2.4
   pip install sitka-spruce
   sitka -m


To install a fresh, stand-alone Anaconda Python installation with Sitka, use


.. code:: bash

   curl -O https://raw.githubusercontent.com/xraypy/sitka-spruce/master/installers/GetSitka.sh
   sh GetSitka.sh



Development Version
~~~~~~~~~~~~~~~~~~~~~~~~

The development version can be cloned with::

   git clone https://github.com/xraypy/sitka-spruce.git

Installation from Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sitka Spruce is a pure python module, so installation on all platforms can use
the source kit and a standard installation using::

   python -m pip install .


.. _desktop_shortcut:

Creating the Desktop Shortcut
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once installed, a desktop shortcut to launch the Sitka application can
be created with::

   sitka -m

If the Python environment with `sitka-spruce` installed is not in your
system PATH, you may need to find the sitka program, either in the
"bin" folder with the appropriate "python" program on macOS or Linux,
or in the "Scripts" folder of your Python environment on Windows.


License
~~~~~~~~~~~~~

The source code and documentation for Sitka Source are distributed under the following license:

..  literalinclude:: ../LICENSE

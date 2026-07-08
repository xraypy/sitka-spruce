.. include:: _config.rst

Downloading and Installation
====================================


Prerequisites
~~~~~~~~~~~~~~~

The current version of Sitka Spruce is |release|, released in July, 2026.

This is a alpha-level, development version, suitable for testing but
probably not recommended for production use.  Comments and suggestions
are welcome.

Sitka Spruce requires Python 3.11 or higher, wxPython 4.2.4 or higher,
matplotlib 3.10 or higher, numpy 2.3 or higher. For HDF5, both the
h5py 3.13 and the hdf5plugin are required.  For Zarr files, zarr 3.2 or
higher is required.

All of the required dependencies, all package are available from `pip`
or on `conda` channels.

As an important note is that `wxPython`_ is required.  This package is
available on `PyPI`_ for MacOS and Windows. For Linux, the packages
that `wxPython`_ itself needs are not always available, and not easily
bundled in the `PyPI`_ package.  This is then a good reason for using
a Anaconda Python environment, which does provide `wxPython` through
its `conda-forge` repository.



Installation
~~~~~~~~~~~~~~~~

For Python installations that have a working `wxPython`_ package,
the latest version (|release|) is available from `PyPI`_ or `github`_.
the `sitka_spruce ` package can be installed with::

   pip install sitka-spruce



To install into a new environment in an existing Anaconda Python
installation, use

.. code:: bash

   conda create -y --name sitka python>=3.13
   conda activate sitka
   conda install -y -c conda-forge numpy scipy matplotlib h5py>=3.13 wxpython>=4.2.4
   pip install sitka-spruce
   sitka -m


To install a fresh Anaconda Python installation with Sitka, use


.. code:: bash

   curl -O https://raw.githubusercontent.com/xraypy/sitka-spruce/master/installers/GetSitka.sh
   sh GetSitka.sh



Development Version
~~~~~~~~~~~~~~~~~~~~~~~~

The latest development version, can be cloned with::

   git clone https://github.com/xraypy/sitka-spruce.git

Installation from Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sitka Spruce is a pure python module, so installation on all platforms can use
the source kit and a standard installation using::

   pip install .


License
~~~~~~~~~~~~~

The source code and documentation for Sitka Source are distributed under the following license:

..  literalinclude:: ../LICENSE

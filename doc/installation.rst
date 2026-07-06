====================================
Downloading and Installation
====================================

.. _github:   https://github.com/xraypy/sitka-spruce
.. _PyPI:     https://pypi.python.org/pypi/sitka-spruce


Prerequisites
~~~~~~~~~~~~~~~

The current version of Sitka Spruce is |release|, released in
June, 2026.

This is an alpha-level, development version, suitable for testing but
not production.  Comments and suggestions are welcome.

Sitka Spruce requires Python 3.11 or higher, wxPython 4.2.5 or higher,
matplotlib 3.10.0 or higher, numpy 2.3 or higher. All of these are
readily available from `pip` or on `conda` channels.


Installation
~~~~~~~~~~~~~~

The latest version (|release|) is available from `PyPI`_ or `github`_, and
the package can be installed with::

   pip install sitka-spruce


Development Version
~~~~~~~~~~~~~~~~~~~~~~~~

To get the latest development version, use::

   git clone https://github.com/xraypy/sitka-spruce.git

Installation from Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

wxmplot is a pure python module, so installation on all platforms can use
the source kit and a standard installation using::

   pip install .


License
~~~~~~~~~~~~~

The wxmplot code is distribution under the following license:

..  literalinclude:: ../LICENSE

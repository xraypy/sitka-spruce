.. include:: _config.rst

.. _motivation:

Motivation for Sitka Spruce
===============================

There are several applications for viewing HDF5 files, and many of the
these are written in Python.  An incomplete list includes:

 * `hdfview`_ from the HDF Group, perhaps the default HDF5 Viewerr.
   This iA Java-based standalone application, and can be used to edit
   HDF5 files.  The graphics and interactivity are very limited.
 * `hdf5view`_  a Python application using Python/Qt.
 * `argos`_     a Python application, also using Python/Qt.
 * `silx`_      a Python libray with a viewing application, also using Python/Qt.
 * `myhdf5`_    a web-based browser for HDF5 files.
 * `h5web`_     the base code for `myhdf5`_, that also incldues an
   interface from Jupyter Lab.

Many of these tools are useful and very good, and may have features
that you prefer over Sitka Spruce.  Still, we felt that there was
still room for one more viewer.  The main features that (we hope)
differentiate Sitka Spruce from existing tools include:

  * using `wxmplot`_ for data visualization. This gives high-quality
    graphics from matplotlib and  and good interactivity for both line
    plots and 2D images.
  * by using `wxPython`_, we plan to use Sitka as a reader for tools
    in the `xraylarch`_ family, including the Larix application for
    XAS data.
  * we aim to make it easier to extract data from the complex data files for
    downstream analysis by exporting either selected data or the full
    addresses to data components.
  * support for working with data in both HDF5 with `h5py`_ and `zarr`_.
  * use as a general-purpose, standalone app for all users
  * interactive use from a Python or Jupyter REPL, improving accessing
    data within HDF5 files for exploratory data analysis.

We welcome feedback, comments, and suggestions on all of these topics
or any other differences with othe visualization or data processing
tools.

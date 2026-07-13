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
 * `nexpy`_     a Python libraray and viewing application,
   specifically for `NeXuS`_ data, an important subset of HDF5, also
   using Python/Qt.
 * `myhdf5`_    a web-based browser for HDF5 files.
 * `h5web`_     the base code for `myhdf5`_, that also incldues an
   interface from Jupyter Lab.

Many of these tools are very good, and some have features that you may
prefer over Sitka Spruce.  But we also note that the sheer number of
viewers available (including 3 separate projects implementating of
"general HDF5 viewers" with Python/Qt), there must be both a need for
such tools, and an expectation (or at least optimism) that creating
another viewer is worthwhile.

Several of these projects (nexpy, silx, h5web) are also somewhat
associated with synchrotron data, which makes heavy use of HDF5 and
`NeXuS`_.  Though we work in that same field, and many of these tools
are very good, we hope we will be forgiven for thinking that there is
room for one more viewer.

The main features and points of emphasis that we think differentiate
Sitka Spruce from existing tools include:

  * using `wxmplot`_ for data visualization. This gives high-quality
    graphics from matplotlib and very good interactivity for both line
    plots and 2D images.
  * by using `wxPython`_, we plan to use Sitka as a reader for tools
    in the `xraylarch`_ family, including the Larix application for
    XAS data. This is expected in the near future, but after the
    initial release.
  * support for working with data in both HDF5 with `h5py`_ and
    `zarr`_.  The initial release supports Zarr Local File Storage,
    but not other stores.
  * we aim to make it very easy to extract data from the complex data
    files for downstream analysis by exporting either selected data or
    the full addresses to data components.
  * we aim to make a GUI that can be used as a general-purpose,
    standalone app for all users and also as an interactive
    application from a Python shell or Jupyter notebook, improving
    accessing data within HDF5 files for exploratory data analysis.
  * for the initial release, we are not explicity or specifically
    supporting NeXuS, but this high on the list of things to consider.

We welcome feedback, comments, suggestions, and collaboration on all
of these topics or any other differences with othe visualization or
data processing tools.

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

  * using `wxmplot`_ gives publication-quality line plots and 2D
    images.  from matplotlib with every good interactivity and
    customizability for the end user.
  * using `wxPython`_, will allow Sitka to be used as a reader for
    tools in the `xraylarch`_ family, including the Larix application
    for XAS data. This is expected in the near future.
  * supporting data in both HDF5 with `h5py`_ and `zarr`_ stores.  The
    initial release supports Zarr Local File Storage, but other stores
    could be added easily.
  * having special support for displaying the metadata written to HDF5
    files for Epics areaDetector files.  At US synchrotron facilities,
    many such HDF5 files are generated. By improving the ability to
    view and use metadata from these files, we hope to encourage
    better use and attention to these metadata capabilities.
  * making it very easy to extract data from the complex data files
    for downstream analysis by exporting either selected data arrays,
    the full addresses to data components, or saving extracted data to
    arrays in simpler HDF5 files.
  * making a GUI that can be used as a general-purpose, standalone app
    for all users and also as an interactive application from a Python
    shell or Jupyter notebook, improving accessing data within HDF5
    files for exploratory data analysis.

We welcome feedback, comments, suggestions, and collaboration on all
of these topics or any other differences with othe visualization or
data processing tools.

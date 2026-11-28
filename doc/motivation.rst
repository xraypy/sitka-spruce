.. include:: _config.rst

.. _motivation:

Motivation
===============================

There are many applications for viewing HDF5 files, including several
separate viewers written in Python.  An incomplete list includes:

 * `hdfview`_ from the HDF Group, perhaps the default HDF5 viewer.
   This is a Java-based standalone application, and can be used to edit
   as well as view HDF5 files.  The graphics are very limited at best,
   and often work poorly. There is effectively no interactivity.
 * `argos`_     a Python application, using Python/Qt.
 * `hdf5view`_  a Python application, also using Python/Qt.
 * `hdf5-viewer`_  a Python application, also using Python/Qt.
 * `vibehdf5`_  a Python application, also using Python/Qt.
 * `silx`_      a Python library with a viewing application, also using Python/Qt.
 * `nexpy`_     a Python library and viewing application,
   specifically for `NeXus`_ data, an important subset of HDF5, also
   using Python/Qt.
 * `myhdf5`_    a web-based browser for HDF5 files.
 * `h5web`_     the base code for `myhdf5`_, that also includes an
   interface from Jupyter Lab.

Many of the Python tools are very good, and may have some features
that you may prefer over Sitka Spruce.

The number of viewers shows that the need for such tools is real, and
strongly suggests that the `hdfview`_ from the HDF Group is not good
enough for serious data visulization and exploration.  The fact that 6
independent projects implement "general HDF5 viewers" with Python/Qt
is fascinating.  Some of these (silx, nexpy) clearly have other
important goals.  Still, this shows that several people saw creating
their own viewer as worthwhile, especially when other goals are
included.  Some of these projects (nexpy, silx, h5web) are also
associated with synchrotron data, which makes heavy use of HDF5 and
`NeXuS`_.  Though we work in that same field, and many of these tools
are very good, we hope we will be forgiven for thinking that there is
room for one more viewer.

The features and points of emphasis that we think differentiate
Sitka Spruce from the existing tools include, in no particular order:

  * Using `wxPython`_. While this appears to be less popular than Qt, we
    think it is a good choice for a general-purpose GUI application, and
    have written and supported many complex wxPython applications over
    the years.  It also avoids many conflicts that are inherent with two
    separate Qt libraries (PyQt and PySide). wxPython also uses a more
    permissive license than PyQt. We respect PyQt's use of the GPL,
    and do not want to worry about such licensing issues.
  * Using `wxPython`_ will also allow Sitka to be used as a reader for
    tools in the `xraylarch`_ family, including the Larix application
    for XAS data. This is expected in the near future.
  * Using `wxmplot`_ gives publication-quality line plots and 2D
    images from matplotlib, and gives very good interactivity and
    customizability to the end user. In Sitka, Images and Plots are
    displayed in separate windows. This allows multiple datasets to be
    viewed at the same time and arranged as the user decides.
  * Supporting data in both HDF5 (with `h5py`_) and `zarr`_ stores.
    The initial release supports Zarr Local File Storage, but other
    stores could be added easily as they become supported by Zarr.
  * Having special support for displaying the metadata written to HDF5
    files for Epics areaDetector files.  At US synchrotron facilities,
    many such HDF5 files are generated. By improving the ability to
    view and use metadata from these files, we hope to encourage
    better use and attention to these metadata capabilities.
  * Making it very easy to extract data from the complex data files
    for downstream analysis by exporting either selected data arrays,
    the full addresses to data components, or saving extracted data to
    arrays in simpler HDF5 files.
  * Making a GUI that can be used as a general-purpose, standalone app
    for all users and also as an interactive application from a Python
    shell or Jupyter notebook, improving access to data within HDF5
    files for exploratory data analysis.

We welcome feedback, comments, suggestions, and collaboration on all
of these topics or any other differences with other visualization or
data processing tools.

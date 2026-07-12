.. include:: _config.rst

Using Sitka
====================================


Sitka can be used as a stand-alone GUI application or from a Python
REPL or Jupyter Notebook.


Running Sitka from the command-line
--------------------------------------

To run sitka from a command-line terminal, use

.. code:: bash

   sitka

You can use the '-d' option to specify a directory from which to read
datasets, as with

.. code:: bash

   sitka -d /home/User/data


Running Sitka from the Desktop shortcut
-----------------------------------------

If you have created the desktop shortcut (see
:ref:`desktop_shortcut`), then clicking on that should launch the main
Sitka application.


Running Sitka from a Python shell, including Jupyter
-------------------------------------------------------------

You can run the Sitka viewer from within a Python shell or Jupyter
notebook that is connected to your computer (that is, supports drawing
to your local screen) to get an interactive graphical exploration of
your data.  To do this, use:

.. code:: Python

   from sitka_spruce import sitka_viewer
   sview = sitka_viewer()

You can also optionally specify a directory
from which to read datasets with

.. code:: Python

    sview = sitka_viewer(folder='/home/User/data')


This will launch the Sitka GUI application in a Window outside of the
Python shell or Jupyter notebook.

The Sitka Viewer will allow the shell or notebook to remain active while the
viewer also runs. That is, you can load and visualize data as with the
standalone application.  You can also use the shell or notebook to
access the data in the Sitka Viewer, either adding datasets to the GUI
or pulling arrays from the GUI into the shell.


.. code:: Python

    ##
    # import an HDF5 file from the shell, and add it to the Sitka Viewer
    # this allows you to fully explore the data arrays in the file
    import h5py
    myfile = h5py.File('myhdf5_file.h5', 'r')
    sview.add_dataset('myhdf5_file.h5', myfile)

    ##
    # Sitka allows you to copy addresses and slices to the System
    # Clipboard, so you can paste them into your shell/notebook
    # Doing <Ctrl-V>  might paste
    #     ['myhdf5_file.h5']['/entry/data/data'][10:20,:,:].sum(axis=0)
    # into the shell, and you can use that to access the data as
    myimage = sview.data.datasets['myhdf5_file.h5']['/entry/data/data'][10:20,:,:].sum(axis=0)

    ##
    # list all datasets in the viewer, no matter how they were read
    for name, dset in sview.data.datasets.items():
        print(name, dset)

    ##
    # list all "named arrays" saved during data exploration
    for name, array in sview.data.array.items():
        print(name, array.shape)

    ##
    # take an example array and run your analysis pipeline on it
    myarray = sview.data.array['spectra1']

    from my_analysistool import analyze
    result  = analyze(myarray)

With this approach, you can quickly load and explore your datasets and
extract and use the arrays you want for downstream processing.

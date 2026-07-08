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



Running Sitka from Python or Jupyter
--------------------------------------

From within a Python repl or Jupyter notebook that is connected to
your computer (and supports drawing to your local screen), use

.. code:: Python

   from sitka_spruce import sitka_viewer
   sview = sitka_viewer()

Here, you can optionally specify a directory from which to read
datasets with

.. code:: Python

   from sitka_spruce import sitka_viewer
   sview = sitka_viewer(folder='/home/User/data')

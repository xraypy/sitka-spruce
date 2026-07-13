.. include:: _config.rst

.. _xyplot_display:


The XY Plot Display Page
====================================

The XY Plot Display page will look like

.. image:: images/sitka_xyplotpage.png
   :width: 98 %

and allow you make images or false-color maps of the multi-dimensional
data.

In the top **Array Selection** section, you can select the dimension
for Y (the vertical axis) and X (the horizontal axis). The choices for
dimensions and number of points will be automatically updated for each
dataset, following the shape values (shown in the Info section).

For data arrays that have 3- or more dimenions, changing the
selections for the Y and X dimensions will automatically change how
the contents of the **Dimension Reduction** is presented.  See
:ref:`dimreduce_panel` for information about how you can use this.

If you have named 1-D arrays of the appropriate length, these will be
included in the drop-down lists for the "Y values" or "X values", to
give dimensions to the resulting image.  By default, the array index
will be used.

To show an image for your selected arrays, but the "Show Image"
button.  You can also select the window display number to show
multiple images at a time.  Each of these will look like:


As with the image diplays, thes plots are fully interactive, and
allowing zooming, panning.  The plots can be configured and can be
copied to the system clipboard with Ctrl-C.  A wide selection of color
themes are available, and colors, linetypes, text, and sizes for most
elements can be changed after displayed.  For more details using this
image display, see `WXMPLOT Interactive Plot Display`_

# sitka-spruce
Visualization for complex scientific datasets in HDF5, Zarr.

While several tools exist for inspecting HDF5 files, we think there is
room for one more, especially one written in wxPython.

The initial goals for sitka-spruce are:

  1. Support for both HDF5 (including NeXuS), and Zarr data, and maybe more formats.
  2. interactive image displays and x/y plots for HDF5/Zarr datasets using `wxmplot`.
  3. Support Table views.
  4. Being able to name and use arrays or slices for visualization and processing.
  5. Useg Sitka as an HDF5/Zarr reader and data selector for other wxPython GUIs,
     including Larix, general-purpose LMFIT Gui, XRD visualization.

At this initial release, goals 1 through 3 are supported and ready for testing and comments.

Last update 2026-July-05

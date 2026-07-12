# sitka-spruce

Sitka spruce supports exploration annd visualization of complex
scientific datasets in HDF5, Zarr.

While several tools exist for inspecting HDF5 files, we think there is
room for one more, especially one written with wxPython and aimed at
helping scientists explore and extract data from complex datasets.

The initial goals for sitka-spruce are:

  1. Support for both HDF5 (including NeXuS), and Zarr data. More formats can be considered.
  2. interactive image displays and x/y plots for HDF5/Zarr datasets using `wxmplot`.
  3. Support Table views.
  4. Being able to name and use arrays or slices for visualization and processing.
  5. Useg Sitka as an HDF5/Zarr reader and data selector for other wxPython GUIs,
     including Larix, general-purpose LMFIT Gui, XRD visualization.

For the initial release, many of these goals are ready for testing and comments.

Last update 2026-July-11

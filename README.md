# sitka-spruce
Visualization for complex scientific datasets in HDF5, Zarr.

While many tools exist for inspecting HDF5 files, we think there is
room for one more, especially one written in wxPython.

The immediaate goals for sitka-spruce are:

  1. Support Image Displays and X/Y Plots with `wxmplot`.
  2. Support for both HDF5 (including NeXuS), and Zarr data,
     and maybe more data forms.
  3. Being able to name and use arrays or slices for visualization
     and processing.

Longer term goals may include:

  1. Use as an HDF5/Zarr reader for X-ray Larch GUIs.
  2. General-purpose data fitting with lmfit.
  3. Integration for XRD images.
  4. XRF viewing and analysis.


Last update 2026-June-28

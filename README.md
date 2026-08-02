# sitka-spruce

Sitka spruce supports exploration annd visualization of complex
scientific datasets in HDF5, Zarr.

While several tools exist for inspecting HDF5 files, we think there is
room for one more, especially one written with wxPython and aimed at
helping scientists explore and extract data from complex datasets.

The initial goals for sitka-spruce are:

  1. Support for both HDF5 (including NeXuS), and Zarr data.
  2. Interactive image displays and line plots for datasets using `wxmplot`.
  3. Support Table views.
  4. Support for displaying metadata from HDF5 files from Epics areaDetector.
  5. Being able to name and export arrays or slices of data for downstream applications.

Though Sitka is fairly new, and in an early release, all of these
goals are ready for testing, comments, and suggestsions.

A near-term goal is to use Sitka as an HDF5/Zarr reader and data
selector for other wxPython GUIs, including Larix, general-purpose
LMFIT Gui, XRD visualization.


Last update 2026-August-02

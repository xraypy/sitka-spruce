import ast
import numpy as np
import wx
import wx.dataview as dv

from wxutils import (GridPanel, SimpleText, pack, Button, TextCtrl, HLine,
                     Check, LEFT, get_color, register_darkdetect,
                     FileSave, Popup)

from pyshortcuts import isotime, fix_filename, get_cwd
from .gui_utils import get_font
from .tablepanel import DataGridFrame
from .data import array2isotimes, dtype2str

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

class NDAttrsPanel(wx.Panel):
    """Panel for Epics ND Attributes"""
    def __init__(self, parent, size=(750, 600)):
        wx.Panel.__init__(self, parent, size=size)
        self.parent = parent
        self.SetBackgroundColour(get_color('sbg'))

        self.gridframes = {}
        self.wids = wids = {}
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)


        wids['show'] = Button(panel, 'Show ND Attributes Table', size=(200, -1),
                              action=self.onShow)

        title = SimpleText(panel, ' Epics ND Attributs',  size=(650, -1), style=wx.ALIGN_LEFT)

        panel.Add(title, newrow=False)
        panel.Add(wids['show'], newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, 0, LEFT|wx.GROW, 4)
        pack(self, sizer)
        register_darkdetect(self.onDarkMode)

    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('sbg', dark=is_dark)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        wx.CallAfter(self.Refresh)

    def onShow(self, event=None):
        group = self.datasets[self.filename][self.itemname]
        out = {}
        for key, dat in group.items():
            val = dat[()]
            if key == 'NDArrayEpicsTSSec':
                out[key] = array2isotimes(val, is_epics=True, timespec='seconds')
            elif key == 'NDArrayTimeStamp':
                out[key] = array2isotimes(val, is_epics=True, timespec='microseconds')
            else:
                out[key] = [dtype2str(val.dtype)(x) for x in val]

        gridframe = self.show_gridframe(window=1)
        gridframe.set_datadict(out, title=f'NDAttributes for {self.filename}')


    def set_object(self, object, itemtype='?', itemname='', filename='', **kws):
        """fill from object"""
        self.filename = filename
        self.itemname = itemname
        self.datasets = self.parent.data.datasets

    def show_gridframe(self, window=1, **opts):
        shown = False
        if window in self.gridframes:
            try:
                self.gridframes[window].Raise()
                shown = True
            except Exception:
                f = self.gridframes.pop(window)
                del f
                shown = False
        if not shown:
            self.gridframes[window] = DataGridFrame(self, **opts)
            self.gridframes[window].Raise()
        return self.gridframes[window]


    def onExportTable(self, evt=None):
        arrays = self.get_arraynames()
        tstamp = fix_filename(isotime(),
                              allow_spaces=True).replace('_','').replace(' ', '_')
        oname = fix_filename(f'Sitka_{tstamp}.h5')

        path = FileSave(self, 'Save Arrays to HDF5',
                        default_dir=get_cwd(),
                        default_file=oname)

        if path is None:
            return

        arrays = self.get_arraynames()
        self.parent.data.export_hdf5(path, arrays)
        self.parent.status_message(f'Wrote arrays to {path}')

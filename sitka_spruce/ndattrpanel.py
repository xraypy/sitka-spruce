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

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

class NDAttrsPanel(wx.Panel):
    """Panel for Epics ND Attributes"""
    def __init__(self, parent, size=(750, 600)):
        wx.Panel.__init__(self, parent, size=size)
        self.parent = parent
        self.SetBackgroundColour(get_color('sbg'))

        self.wids = wids = {}
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)

        def padd_text(text, dcol=1, size=(80, -1), newrow=True):
            panel.Add(SimpleText(panel, text, size=size), dcol=dcol, newrow=newrow)

        wids['show'] = Button(panel, 'Show ND Attributes Table', size=(200, -1),
                              action=self.onShow)

        padd_text(' Epics ND Attribute: ', newrow=False)
        panel.Add(wids['show'])

        panel.pack()
        panel.SetSize((725, 600))

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
        print(" show NDAttrs ")

    def onPanelExposed(self, *args, **kws):
        self.set_object()

    def set_object(self, *args, **kws):
        data = self.parent.data
        self.array_data = []
        # warrays = self.wids['arrays']
        #warrays.DeleteAllItems()

        # for aname, arr in data.arrays.items():
        #    addr = data.array_addrs.get(aname, 'unknown')
        #    args = [True, aname, repr(arr.shape), addr]
        #    self.array_data.append(args)
        #    warrays.AppendItem(tuple(args))

    def set_all_selected(self, val):
        if self.wids['arrays'] is not None:
            warrays = self.wids['arrays']
            for row in range(warrays.GetItemCount()):
                warrays.SetValue(val, row, 0)

    def onSelectAll(self, evt=None):
        self.set_all_selected(True)

    def onSelectNone(self, evt=None):
        self.set_all_selected(False)

    def onSelectArray(self, evt=None):
        if self.wids['arrays'] is None:
            return
        if not self.wids['arrays'].HasSelection():
            return
        item = self.wids['arrays'].GetSelectedRow()
        address = self.array_data[item][3]
        self.access_code = address
        self.wids['access_code'].SetLabel(address)

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

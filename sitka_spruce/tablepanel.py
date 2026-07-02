import numpy as np
import wx
import wx.lib.scrolledpanel as scrolled
from  wx.grid import Grid

from wxutils import (LEFT, pack, FRAMESTYLE)

from wxutils import (GridPanel, SimpleText, pack, Button,
                     Choice, Check, LEFT,
                     get_color, register_darkdetect)

from pyshortcuts import gformat

from .dimreduce import DimReducePanel
from .gui_utils import get_font
from .data import ARRAY_TYPES, get_data, dtype2str


class DataGridFrame(wx.Frame):
    """Simple Data Grid Frame for HDF5/Zarr datasets"""
    def __init__(self, parent, size=(600, 600), title='Data Grid'):
        wx.Frame.__init__(self, parent, title='Sitka Table',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)

        self.title = SimpleText(self, title, font=get_font(larger=1),
                                colour='title_red', size=(500, -1),
                                style=LEFT|wx.ALIGN_CENTER_VERTICAL)

        self.grid = Grid(self, size=size)
        self.grid.CreateGrid(100, 100)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.title, 0, 0, LEFT|wx.GROW, 2)
        sizer.Add(self.grid,  0, 0, LEFT|wx.GROW, 2)
        pack(self, sizer)
        register_darkdetect(self.onDarkMode)
        self.Raise()
        self.Show()

    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('text_bg', dark=is_dark)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        wx.CallAfter(self.Refresh)


    def set_datadict(self, data, title=None):
        """set data from s dict of lists / ndarrays
        """
        self.grid.ClearGrid()
        for i, key in enumerate(data.keys()):
            self.grid.SetColLabelValue(i, key)
            for j, val in enumerate(data[key]):
                self.grid.SetCellValue(j, i, val)


    def set_data2d(self, data, title=None):
        """set data from 2d array"""
        if title is not None:
            self.title.SetLabel(' ' + title)

        self.grid.ClearGrid()
        ncols = self.grid.GetNumberCols()
        nrows = self.grid.GetNumberRows()
        self.grid.DeleteCols(0, ncols)
        self.grid.DeleteRows(0, nrows)

        cast = dtype2str(data.dtype)
        ny, nx = data.shape
        self.grid.AppendCols(nx+1)
        self.grid.AppendRows(ny+1)

        for i in range(ny):
            self.grid.SetRowLabelValue(i, f'{i}')
            for j in range(nx):
                self.grid.SetColLabelValue(j, f'{j}')
                self.grid.SetCellValue(i, j, cast(data[i, j]))

class TablePanel(wx.Panel):
    """Config Panel for Grid Display of HDF5/Zarr datasets"""
    def __init__(self, parent, size=(500, 500)):
        wx.Panel.__init__(self, parent)

        self.SetBackgroundColour(get_color('nb_area'))

        self.data_shape = None
        self.data_obj = None
        self.xsel_cur, self.ysel_cur = 0, 1
        self.skip_dim_proc = False
        self.gridframes = {}
        self.dim_reduce = DimReducePanel(parent=self)

        self.wids = wids = {}
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)

        wids['show'] = Button(panel, 'Show Table', size=(150, -1),
                                 action=self.onShow)

        wids['axes'] =  ['dim0: 0 points', 'dim1: 0 points']

        wids['xdim'] = Choice(panel, wids['axes'],
                              size=(175, -1), action=self.onXdim)
        wids['ydim'] = Choice(panel, wids['axes'],
                              size=(175, -1), action=self.onYdim)
        wids['xdim'].SetSelection(0)
        wids['ydim'].SetSelection(1)

        wids['win'] = Choice(panel, ['1', '2', '3', '4', '5'], size=(75, -1))
        wids['win'].SetStringSelection('1')


        def padd_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        titleopts = {'font': get_font(larger=1),
                     'colour': 'title_red', 'style': LEFT}

        padd_text(' X : ')
        panel.Add(wids['xdim'])

        padd_text(' Y : ', newrow=False)
        panel.Add(wids['ydim'])

        padd_text(' ')
        panel.Add(wids['show'])
        padd_text(' windows:', newrow=False)
        panel.Add(wids['win'])

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 0, 0, LEFT|wx.GROW, 4)
        sizer.Add(self.dim_reduce, 0, 0, LEFT|wx.GROW, 5)
        pack(self, sizer)
        register_darkdetect(self.onDarkMode)

    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('text_bg', dark=is_dark)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        wx.CallAfter(self.Refresh)

    def onXdim(self, event=None):
        if self.skip_dim_proc:
            return
        self.skip_dim_proc = True
        xsel = self.wids['xdim'].GetSelection()
        ysel = self.wids['ydim'].GetSelection()
        if ysel == xsel and xsel != self.xsel_cur:
            self.wids['ydim'].SetSelection(self.xsel_cur)
            self.ysel_cur = self.xsel_cur
        else:
            self.ysel_cur = ysel
        self.xsel_cur = xsel
        if self.data_shape is not None:
            for i, npts in enumerate(self.data_shape):
                enable = i not in (self.xsel_cur, self.ysel_cur)
                self.dim_reduce.enable_dimension(i, enable=enable, npts=npts)
        self.skip_dim_proc = False

    def onYdim(self, event=None):
        if self.skip_dim_proc:
            return
        self.skip_dim_proc = True
        xsel = self.wids['xdim'].GetSelection()
        ysel = self.wids['ydim'].GetSelection()
        if ysel == xsel and ysel != self.ysel_cur:  # y changed
            self.wids['xdim'].SetSelection(self.ysel_cur)
            self.xsel_cur = self.ysel_cur
        else:
            self.xsel_cur = xsel
        self.ysel_cur = ysel

        if self.data_shape is not None:
            for i, npts in enumerate(self.data_shape):
                enable = i not in (self.xsel_cur, self.ysel_cur)
                self.dim_reduce.enable_dimension(i, enable=enable, npts=npts)

        self.skip_dim_proc = False

    def set_object(self, object, itemtype='?', itemname='', filename='', **kws):
        """fill from object"""
        self.filename = filename
        self.itemname = itemname
        self.data_obj = object
        if (itemtype in ARRAY_TYPES):
            self.data_shape = object.shape
            choices = self.dim_reduce.set_datashape(object.shape)
            xcur = self.wids['xdim'].GetSelection()
            ycur = self.wids['ydim'].GetSelection()
            self.wids['xdim'].SetChoices(choices)
            self.wids['ydim'].SetChoices(choices)
            self.wids['ydim'].SetSelection(ycur)
            self.wids['xdim'].SetSelection(xcur)

            xcur = self.wids['xdim'].GetSelection()
            ycur = self.wids['ydim'].GetSelection()
            self.dim_reduce.enable_dimension(xcur, enable=False, npts=None)
            self.dim_reduce.enable_dimension(ycur, enable=False, npts=None)

        self.Refresh()


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

    def onShow(self, event=None, new=True):
        reddim = self.dim_reduce.get_result()

        win    = self.wids['win'].GetStringSelection()
        ydim   = self.wids['ydim'].GetSelection()
        xdim   = self.wids['xdim'].GetSelection()

        dat, alabel = get_data(self.data_obj, reddim)

        if len(dat.shape) < 2:
            print('shape too small')
            return
        _ny, _nx = dat.shape
        _ry, _rx = self.data_shape[ydim], self.data_shape[xdim]
        _ry, _rx = self.data_shape[ydim], self.data_shape[xdim]

        # print(f"Got data {_nx=}  {_rx=}   {_ny=}  {_ry=}  {ydim=} {xdim=}")
        if _ry == _nx and _rx == _ny or (ydim > xdim):
            dat = dat.transpose()

        frame_opts = {'title':  f'SitkaGrid {win} '}
        gframe = self.show_gridframe(win, **frame_opts)

        gframe.set_data2d(dat, title=f'{self.filename}{alabel}')
        gframe.Show()
        gframe.Raise()

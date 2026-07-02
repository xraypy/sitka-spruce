from functools import partial
import numpy as np

import wx

from wxmplot import ImageFrame

from wxutils import (GridPanel, SimpleText, pack, Button,
                     Choice, Check, LEFT,
                     get_color, register_darkdetect)

from .dimreduce import DimReducePanel
from .data import ARRAY_TYPES, get_data

class ArrayImagePanel(wx.Panel):
    """Image Show Config Panel for HDF5/Zarr datasets"""
    def __init__(self, parent, size=(500, 500)):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(get_color('nb_area'))

        self.data_shape = None
        self.data_obj = None
        self.xsel_cur, self.ysel_cur = 0, 1
        self.skip_dim_proc = False
        self.imageframes = {}
        self.wids = wids = {}

        self.dim_reduce = DimReducePanel(parent=self)

        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)
        wids['imshow_new'] = Button(panel, 'Show New Image', size=(150, -1),
                                action=self.onImshow)
        wids['imshow_replace'] = Button(panel, 'Replace Last Image', size=(150, -1),
                                  action=partial(self.onImshow, new=False))

        wids['plot_xchoices'] = ['<index>']
        wids['plot_xval'] = Choice(panel, wids['plot_xchoices'],
                                   size=(200, -1), action=self.onImshow)
        wids['plot_ychoices'] = ['<index>']
        wids['plot_yval'] = Choice(panel, wids['plot_ychoices'],
                                   size=(200, -1), action=self.onImshow)
        wids['ydir'] = Check(panel, 'Y=0 at top', default=False)


        wids['win'] = Choice(panel, ['1', '2', '3', '4', '5'], size=(75, -1))
        wids['win'].SetStringSelection('1')

        wids['axes'] =  ['dim0: 0 points', 'dim1: 0 points']

        wids['xdim'] = Choice(panel, wids['axes'],
                              size=(175, -1), action=self.onXdim)
        wids['ydim'] = Choice(panel, wids['axes'],
                              size=(175, -1), action=self.onYdim)
        wids['xdim'].SetSelection(0)
        wids['ydim'].SetSelection(1)

        def padd_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        padd_text(' X (Horiz): ')
        panel.Add(wids['xdim'])
        padd_text(' X values: ', newrow=False)
        panel.Add(wids['plot_xval'])

        padd_text(' Y (Vert): ')
        panel.Add(wids['ydim'])
        padd_text(' Y values: ', newrow=False)
        panel.Add(wids['plot_yval'])

        padd_text(' ')
        panel.Add(wids['imshow_new'])
        padd_text(' windows:', newrow=False)
        panel.Add(wids['win'])

        padd_text(' ')
        panel.Add(wids['imshow_replace'])
        panel.Add(wids['ydir'])
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


    def show_imageframe(self, window=1, **opts):
        shown = False
        if window in self.imageframes:
            try:
                self.imageframes[window].Raise()
                shown = True
            except Exception:
                f = self.imageframes.pop(window)
                del f
                shown = False
        if not shown:
            self.imageframes[window] = ImageFrame(self, **opts)
            self.imageframes[window].Raise()
        return self.imageframes[window]

    def onImshow(self, event=None, new=True):
        # print("imshow ", new)

        reddim = self.dim_reduce.get_result()

        ########
        win    = self.wids['win'].GetStringSelection()
        ydir   = self.wids['ydir'].IsChecked()
        ydim   = self.wids['ydim'].GetSelection()
        xdim   = self.wids['xdim'].GetSelection()
        xarray  = self.wids['plot_xval'].GetStringSelection()
        yarray  = self.wids['plot_yval'].GetStringSelection()

        xdstr   = self.wids['xdim'].GetStringSelection()
        ydstr   = self.wids['ydim'].GetStringSelection()
        # print(f"imshow  {ydim=}, {xdim=}, {xdstr=}, {ydstr=}, {win=}, {ydir=}")

        img, alabel = get_data(self.data_obj, reddim)

        if len(img.shape) < 2:
            print('shape too small')
            return
        _ny, _nx = img.shape

        _ry, _rx = self.data_shape[ydim], self.data_shape[xdim]

       # print("Got image {_nx=}  {_rx=}   {_ny=}  {_ry=}  ")

        if _ry == _nx and _rx == _ny:
            img = img.transpose()

        if ydir:
            img = img[::-1, :]
        if img.dtype == np.bool:
            img = img.astype(int)

        frame_opts = {'title':  f'SitkaImage {win} '}
        iframe = self.show_imageframe(win, **frame_opts)

        opts = {'title': f'{self.filename}{alabel}'}
        iframe.display(img)
        iframe.Show()
        iframe.Raise()

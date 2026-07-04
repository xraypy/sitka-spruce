import time
from functools import partial
from threading import Thread
import numpy as np

import wx
from wxmplot import PlotFrame

from wxutils import (GridPanel, SimpleText, pack, Button,
                     Choice, Check, LEFT,
                     get_color, register_darkdetect)

from .dimreduce import DimReducePanel
from .data import ARRAY_TYPES, get_data, dim_repr, datasize_repr

class ArrayPlot1DPanel(wx.Panel):
    """Config Panel for 1D Plots of HDF5/Zarr datasets"""
    def __init__(self, parent, size=(750, 500)):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.SetBackgroundColour(get_color('nb_area'))

        self.data_shape = None
        self.data_obj = None
        self.last_yaxes = 0
        self.plotframes = {}
        self.dim_reduce = DimReducePanel(parent=self, callback=self.onDimReduce)
        self.wids = wids = {}
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)

        wids['newplot'] = Button(panel, 'New Plot', size=(200, -1),
                              action=self.onPlot)
        wids['overplot'] = Button(panel, 'Over Plot', size=(200, -1),
                                  action=partial(self.onPlot, new=False))

        wids['sharey'] = Check(panel, ' ', size=(300, -1), default=False)
        wids['win'] = Choice(panel, ['1', '2', '3', '4', '5'], size=(75, -1))
        wids['win'].SetStringSelection('1')

        wids['ychoices'] =  ['dim0: 0pts']
        wids['normchoices'] = ['1']
        wids['xchoices'] = ['<index>']

        wids['yarray'] = Choice(panel, wids['ychoices'],
                                size=(200, -1), action=self.onYarray)
        wids['yop'] = Choice(panel, ['+', '-', '*', '/'],
                             size=(75, -1), action=self.onPlot)
        wids['yop'].SetStringSelection('/')

        wids['ynorm'] = Choice(panel, wids['normchoices'],
                                size=(200, -1), action=self.onPlot)

        wids['xarray'] = Choice(panel, wids['xchoices'],
                                size=(200, -1), action=self.onPlot)

        def padd_text(text, dcol=1, size=(125, -1), newrow=True):
            panel.Add(SimpleText(panel, text, size=size, style=LEFT),
                      dcol=dcol, newrow=newrow)

        padd_text('Y array', newrow=False)
        panel.Add(wids['yarray'])
        panel.Add(wids['yop'])
        panel.Add(wids['ynorm'])

        padd_text('X array')
        panel.Add(wids['xarray'], dcol=2)
        panel.Add((5,5), newrow=True)
        panel.Add(wids['newplot'])
        padd_text(' Window:', size=(125, -1), newrow=False)
        panel.Add(wids['win'])
        panel.Add((5,5), newrow=True)
        panel.Add(wids['overplot'])
        padd_text(' Share Y-axis?', size=(125, -1), newrow=False)
        panel.Add(wids['sharey'], dcol=2)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel,           0, 0, LEFT|wx.GROW, 2)
        sizer.Add(self.dim_reduce, 0, 0, LEFT|wx.GROW, 2)
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


    def set_object(self, object, itemtype='?', itemname='', filename='', **kws):
        """fill from object"""
        self.filename = filename
        self.itemname = itemname
        isdata = (itemtype in ARRAY_TYPES)
        self.data_obj = object
        if isdata:
            self.data_shape = object.shape
            choices = self.dim_reduce.set_datashape(object.shape)
            cur = self.wids['yarray'].GetSelection()
            try:
                self.wids['yarray'].SetChoices(choices)
            except Exception:
                pass
            self.dim_reduce.enable_dimension(cur, enable=False, npts=None)

        self.wids['yarray'].Enable(isdata)
        self.Refresh()

    def onYarray(self, event=None):
        sel = self.wids['yarray'].GetSelection()
        if self.data_shape is not None:
            for i, npts in enumerate(self.data_shape):
                self.dim_reduce.enable_dimension(i, enable=(i!=sel), npts=npts)

    def onDimReduce(self, event=None, dim=None, reduce=None):
        self.onPlot(new=True)

    def onPlot(self, event=None, new=True):
        win    = self.wids['win'].GetStringSelection()
        sharey = self.wids['sharey'].IsChecked()
        # ydim   = self.wids['yarray'].GetSelection()
        # ynorm  = self.wids['ynorm'].GetStringSelection()
        # yop    = self.wids['yop'].GetStringSelection()
        xarray = self.wids['xarray'].GetStringSelection()
        ###
        self.parent.status_message('fetching data....')

        ndim = len(self.data_obj.shape)
        reddim = self.dim_reduce.get_result(ndim)
        def _get_data(reddim):
            self._yarr = get_data(self.data_obj, reddim)

        data_thread = Thread(target=_get_data, args=(reddim,))
        t0_data = time.time()
        data_thread.start()
        time.sleep(0.0005)

        frame_opts = {'title':  f'SitkaPlot {win} '}
        pframe = self.show_plotframe(win, **frame_opts)
        ylabel = dim_repr(reddim)
        opts = {'title': f'{self.filename}\n{self.itemname}'}

        # if 'ynorm' == '1':
        #     ynorm  = 1.0

        plot = pframe.oplot
        if new:
            plot = pframe.plot
            self.last_yaxes = 1
            opts['ylabel'] = ylabel
        elif not sharey:
            self.last_yaxes = ya = min(4, max(1, self.last_yaxes+1))
            if self.last_yaxes > 1:
                opts['yaxes_tracecolor'] = True
                opts[f'y{ya}label'] = ylabel

        opts['yaxes'] = self.last_yaxes
        opts['label'] = f'{self.itemname}{ylabel}'

        data_thread.join()
        dt_data = time.time()-t0_data

        dsize = datasize_repr(self._yarr)
        osize = datasize_repr(self.data_obj)

        self.parent.status_message(f'got data ({dsize} of {osize}) in {dt_data:.2f} seconds')
        self.parent.data.add_array('_ydat', self._yarr)

        xarr = np.arange(len(self._yarr))
        if xarray == '<index>':
            xarr = np.arange(len(self._yarr))

        plot(xarr, self._yarr, **opts)
        pframe.Show()
        pframe.Raise()

    def show_plotframe(self, window=1, **opts):
        shown = False
        if window in self.plotframes:
            try:
                self.plotframes[window].Raise()
                shown = True
            except Exception:
                f = self.plotframes.pop(window)
                del f
                shown = False
        if not shown:
            self.plotframes[window] = PlotFrame(self, **opts)
            self.plotframes[window].Raise()
        return self.plotframes[window]

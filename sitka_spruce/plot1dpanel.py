import time
from functools import partial
from threading import Thread
import numpy as np

import wx
from wxmplot import PlotFrame

from wxutils import (GridPanel, SimpleText, pack, Button,
                     Choice, Check, LEFT, TextCtrl, Popup,
                     get_color, register_darkdetect)

from .gui_utils import get_font
from .dimreduce import DimReducePanel
from .data import ARRAY_TYPES, get_data, dim_code, datasize_repr

class ArrayPlot1DPanel(wx.Panel):
    """Config Panel for 1D Plots of HDF5/Zarr datasets"""
    def __init__(self, parent, size=(750, 500)):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.SetBackgroundColour(get_color('sbg'))
        self.SetFont(get_font())
        self.data_shape = None
        self.data_obj = None
        self.last_yaxes = 0
        self.plotframes = {}
        self.wids = wids = {}

        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)
        self.dim_reduce = DimReducePanel(parent=panel, callback=self.onDimReduce)

        wids['newplot'] = Button(panel, 'New Plot', size=(200, -1),
                              action=self.onPlot)
        wids['overplot'] = Button(panel, 'Over Plot', size=(200, -1),
                                  action=partial(self.onPlot, new=False))

        wids['sharey'] = Check(panel, ' ', size=(300, -1), default=False)
        wids['win'] = Choice(panel, ['1', '2', '3', '4', '5'], size=(75, -1))
        wids['win'].SetStringSelection('1')

        wids['ychoices'] =  ['dim0: 0 points']

        wids['yarray'] = Choice(panel, wids['ychoices'],
                                size=(200, -1), action=self.onYarray)
        wids['yop'] = Choice(panel, ['+', '-', '*', '/'], size=(75, -1))
        wids['yop'].SetStringSelection('/')

        wids['ynorm'] = Choice(panel, ['1'],   size=(200, -1))
        wids['xarray'] = Choice(panel, ['<index>'], size=(200, -1))

        wids['save_array'] = Button(panel, 'Save Array', size=(125, -1),
                                  action=self.onNameArray)
        wids['array_name'] = TextCtrl(panel, 'ydat', size=(200, -1),
                                      act_on_losefocus=False,
                                      action=self.onNameArray)
        wids['check_overwrite']  = Check(panel, ' ', size=(10, -1), default=True)

        def padd_text(text, dcol=1, size=(125, -1), newrow=True):
            panel.Add(SimpleText(panel, text, size=size, style=LEFT),
                      dcol=dcol, newrow=newrow)

        padd_text('Y array', newrow=True)
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

        panel.Add((5, 5), newrow=True)
        panel.Add(self.dim_reduce, dcol=5, newrow=True)
        panel.Add((5, 5), newrow=True)

        panel.Add(wids['save_array'], newrow=True)
        panel.Add(wids['array_name'])
        padd_text(' Verify Overwrite', size=(125, -1), newrow=False)
        panel.Add(wids['check_overwrite'], dcol=1)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel,    1, 0, LEFT|wx.GROW, 2)
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

    def onNameArray(self, event=None):
        arr_name = self.wids['array_name'].GetValue()
        check_overwrite = self.wids['check_overwrite'].IsChecked()
        if check_overwrite and arr_name in self.parent.data.arrays:
            ret = Popup(self, f"Overwrite Array '{arr_name}'?\n",
                        'Verify Overwrite',
                        style=wx.YES_NO|wx.ICON_QUESTION)
            if ret != wx.ID_YES:
                return

        ndim = len(self.data_obj.shape)
        reddim = self.dim_reduce.get_result(ndim)
        _yarr = get_data(self.data_obj, reddim)
        ylabel = dim_code(reddim)
        access_code = f"['{self.filename}']['{self.itemname}']{ylabel}"
        self.parent.data.add_array(arr_name, _yarr, address=access_code)


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
        self.update_array_choices()

    def update_array_choices(self, event=None):
        ystr = self.wids['yarray'].GetStringSelection()
        words = ystr.replace('dim', '').replace('points', '').split()
        yshape = (int(words[1]), )

        achoices = self.parent.data.array_shapes.get(yshape, [])
        if '_ydat' in achoices:
            achoices.remove('_ydat')

        nchoices = ['1']
        nchoices.extend(achoices)
        self.wids['ynorm'].SetChoices(nchoices)

        xchoices = ['<index>']
        xchoices.extend(achoices)
        self.wids['xarray'].SetChoices(xchoices)

    def onDimReduce(self, event=None, dim=None, reduce=None):
        self.onPlot(new=True)

    def onPlot(self, event=None, new=True):
        win    = self.wids['win'].GetStringSelection()
        sharey = self.wids['sharey'].IsChecked()
        # ydim   = self.wids['yarray'].GetSelection()
        ynorm  = self.wids['ynorm'].GetStringSelection()
        yop    = self.wids['yop'].GetStringSelection()
        xarr   = self.wids['xarray'].GetStringSelection()
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
        pframe = self.show_plotframe(int(win), **frame_opts)
        ylabel = dim_code(reddim)
        self.parent.access_code = f"['{self.filename}']['{self.itemname}']{ylabel}"

        opts = {'title': f'{self.filename}\n{self.itemname}'}


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
        opts['xlabel'] = xarr

        data_thread.join()
        dt_data = time.time()-t0_data

        ynorm = self.parent.data.arrays.get(ynorm, 1.0)
        if yop == '*':   self._yarr = self._yarr * ynorm
        elif yop == '/': self._yarr = self._yarr * ynorm
        elif yop == '+': self._yarr = self._yarr + ynorm
        elif yop == '-': self._yarr = self._yarr - ynorm

        dsize = datasize_repr(self._yarr)
        osize = datasize_repr(self.data_obj)

        self.parent.status_message(f'got data ({dsize} of {osize}) in {dt_data:.2f} seconds')

        xvals = self.parent.data.arrays.get(xarr, None)
        if xarr == '<index>' or xvals is None:
            opts['xlabel'] = 'index'
            xvals = np.arange(len(self._yarr))

        plot(xvals, self._yarr, **opts)
        self.parent.data.add_array('_ydat', self._yarr, address=self.parent.access_code)
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

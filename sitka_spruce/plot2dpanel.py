import time
from threading import Thread
import numpy as np

import wx

from wxmplot import ImageFrame

from wxutils import (GridPanel, SimpleText, pack, Button,
                     Choice, Check, LEFT, TextCtrl,
                     get_color, register_darkdetect)

from .dimreduce import DimReducePanel
from .data import ARRAY_TYPES, get_data, dim_code, datasize_repr

class ArrayImagePanel(wx.Panel):
    """Image Show Config Panel for HDF5/Zarr datasets"""
    def __init__(self, parent, size=(750, 500)):
        wx.Panel.__init__(self, parent)
        self.parent = parent

        self.SetBackgroundColour(get_color('text_bg'))

        self.data_shape = None
        self.data_obj = None
        self.access_code = None
        self.xsel_cur, self.ysel_cur = 0, 1
        self.skip_dim_proc = False
        self.imageframes = {}
        self.wids = wids = {}

        self.dim_reduce = DimReducePanel(parent=self, callback=self.onDimReduce)

        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)
        wids['imshow'] = Button(panel, 'Show Image', size=(200, -1),
                                action=self.onImshow)


        wids['plot_xchoices'] = ['<index>']
        wids['plot_xval'] = Choice(panel, wids['plot_xchoices'],
                                   size=(200, -1), action=self.onImshow)
        wids['plot_ychoices'] = ['<index>']
        wids['plot_yval'] = Choice(panel, wids['plot_ychoices'],
                                   size=(200, -1), action=self.onImshow)
        wids['ydir'] = Check(panel, ' ', size=(100, -1), default=False)


        wids['win'] = Choice(panel, ['1', '2', '3', '4', '5'], size=(75, -1))
        wids['win'].SetStringSelection('1')

        wids['axes'] =  ['dim0: 0pts', 'dim1: 0pts']

        wids['xdim'] = Choice(panel, wids['axes'],
                              size=(200, -1), action=self.onXdim)
        wids['ydim'] = Choice(panel, wids['axes'],
                              size=(200, -1), action=self.onYdim)
        wids['ydim'].SetSelection(0)
        wids['xdim'].SetSelection(1)

        wids['save_array'] = Button(panel, 'Save Array', size=(125, -1),
                                  action=self.onNameArray)
        wids['array_name'] = TextCtrl(panel, 'imgdat', size=(200, -1))
        wids['check_overwrite']  = Check(panel, ' ', size=(10, -1), default=True)

        def padd_text(text, dcol=1, size=(100, -1), newrow=True):
            panel.Add(SimpleText(panel, text, size=size), dcol=dcol, newrow=newrow)

        padd_text(' Y (Vert): ', newrow=True)
        panel.Add(wids['ydim'])
        padd_text(' Y values: ', newrow=False)
        panel.Add(wids['plot_yval'])

        padd_text(' X (Horiz): ')
        panel.Add(wids['xdim'])
        padd_text(' X values: ', newrow=False)
        panel.Add(wids['plot_xval'])

        padd_text(' ')
        panel.Add(wids['imshow'])
        padd_text(' Window:', newrow=False)
        panel.Add(wids['win'])

        padd_text(' ')
        panel.Add((5, 5))
        padd_text(' Y=0 at top?', size=(125, -1), newrow=False)
        panel.Add(wids['ydir'], dcol=2)

        panel.Add(wids['save_array'], newrow=True)
        panel.Add(wids['array_name'])
        padd_text(' Verify Overwrite', size=(125, -1), newrow=False)
        panel.Add(wids['check_overwrite'], dcol=1)

        panel.Add((15, 15), newrow=True)

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
        access_code = f"datasets['{self.filename}']['{self.itemname}']{ylabel}"
        self.parent.data.add_array(arr_name, _yarr, address=access_code)


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
            if len(choices) > 0:
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

    def onDimReduce(self, event=None, dim=None, reduce=None):
        self.onImshow(new=True)


    def onImshow(self, event=None, new=True):
        # print("imshow ", new)

        ########
        win    = self.wids['win'].GetStringSelection()
        ydir   = self.wids['ydir'].IsChecked()
        ydim   = self.wids['ydim'].GetSelection()
        xdim   = self.wids['xdim'].GetSelection()
        # xarray  = self.wids['plot_xval'].GetStringSelection()
        # yarray  = self.wids['plot_yval'].GetStringSelection()
        # xdstr   = self.wids['xdim'].GetStringSelection()
        # ydstr   = self.wids['ydim'].GetStringSelection()

        ndim = len(self.data_obj.shape)
        reddim = self.dim_reduce.get_result(ndim)

        def _get_data(reddim):
            self._img = get_data(self.data_obj, reddim)

        data_thread = Thread(target=_get_data, args=(reddim,))
        t0_data = time.time()
        self.parent.status_message('fetching data....')

        data_thread.start()
        time.sleep(0.0005)
        frame_opts = {'title':  f'SitkaImage {win} '}
        iframe = self.show_imageframe(win, **frame_opts)

        dlabel = dim_code(reddim)
        self.access_code = f"datasets['{self.filename}']['{self.itemname}']{dlabel}"
        opts = {'title': f'{self.filename} {dlabel}'}

        data_thread.join()
        if self._img.dtype == np.bool:
            self._img = self._img.astype(int)

        dt_data = time.time()-t0_data
        dsize = datasize_repr(self._img)
        osize = datasize_repr(self.data_obj)

        self.parent.status_message(f'got data ({dsize} of {osize}) in {dt_data:.2f} seconds')

        if len(self._img.shape) < 2:
            self._img.shape = (self._img.shape[0], 1)

        if (ydim > xdim):
            self._img = self._img.transpose()

        xvals = np.arange(self._img.shape[1])
        yvals = np.arange(self._img.shape[0])
        if ydir:
            self._img = self._img[::-1, :]
            yvals = yvals[::-1]

        iframe.display(self._img, x=xvals, y=yvals, **opts)
        iframe.Show()
        iframe.Raise()
        self.parent.data.add_array('_imgdat', self._img)

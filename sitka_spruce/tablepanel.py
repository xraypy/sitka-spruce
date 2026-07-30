import time
from threading import Thread
import wx
from  wx.grid import Grid

from wxutils import (GridPanel, SimpleText, pack, Button,
                     TextCtrl, Popup,
                     Check, Choice, LEFT, get_color,
                     register_darkdetect)

from .dimreduce import DimReducePanel
from .gui_utils import get_font, WIN_CHOICES
from .data import ARRAY_TYPES, dtype2str, get_data, dim_code, datasize_repr

class DataGridFrame(wx.Frame):
    """Simple Data Grid Frame for HDF5/Zarr datasets"""
    def __init__(self, parent, size=(800, 600), title='Data Grid'):
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
        bgcol = get_color('sbg', dark=is_dark)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        wx.CallAfter(self.Refresh)


    def set_datadict(self, data, title=None):
        """set data from s dict of lists / ndarrays
        """
        self.grid.ClearGrid()
        ncols = self.grid.GetNumberCols()
        nrows = self.grid.GetNumberRows()
        self.grid.DeleteCols(0, ncols)
        self.grid.DeleteRows(0, nrows)

        ncols = len(data)
        nrows = 0
        for d in data.values():
            nrows = max(nrows, len(d))

        if nrows == 1:
            rdat = {}
            for key, val in data.items():
                rdat[key] = val[0]

            self.grid.AppendRows(len(rdat))
            self.grid.AppendCols(2)
            self.grid.SetColLabelValue(0, ' Name ')
            self.grid.SetColLabelValue(1, ' Value ')
            i = 0
            for key, val in rdat.items():
                self.grid.SetCellValue(i, 0, key)
                self.grid.SetCellValue(i, 1, val)
                i += 1
            self.grid.AutoSizeColumn(0)
            self.grid.AutoSizeColumn(1)
        else:
            self.grid.AppendRows(nrows)
            self.grid.AppendCols(ncols)
            for i, key in enumerate(data.keys()):
                self.grid.SetColLabelValue(i, key)
                for j, val in enumerate(data[key]):
                    self.grid.SetCellValue(j, i, val)
                self.grid.AutoSizeColumn(i)

    def set_data2d(self, data, title=None):
        """set data from 2d array"""
        if title is not None:
            self.title.SetLabel(' ' + title)

        self.grid.ClearGrid()
        ncols = self.grid.GetNumberCols()
        nrows = self.grid.GetNumberRows()
        self.grid.DeleteCols(0, ncols)
        self.grid.DeleteRows(0, nrows)

        cast= dtype2str(data.dtype)
        ny, nx = data.shape
        self.grid.AppendCols(nx)
        self.grid.AppendRows(ny)

        for i in range(ny):
            self.grid.SetRowLabelValue(i, f'{i}')
            for j in range(nx):
                self.grid.SetColLabelValue(j, f'{j}')
                self.grid.SetCellValue(i, j, cast(data[i, j]))

class TablePanel(wx.Panel):
    """Config Panel for Grid Display of HDF5/Zarr datasets"""
    def __init__(self, parent, size=(750, 500)):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.SetBackgroundColour(get_color('sbg'))
        self.SetFont(get_font())

        self.data_shape = None
        self.data_obj = None
        self.xsel_cur, self.ysel_cur = 0, 1
        self.skip_dim_proc = False
        self.gridframes = {}

        self.wids = wids = {}
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)
        self.dim_reduce = DimReducePanel(parent=panel, callback=self.onDimReduce)

        wids['show'] = Button(panel, 'Show Table', size=(150, -1),
                                 action=self.onShow)

        wids['axes'] =  ['dim0: 0 points', 'dim1: 0 points']

        wids['xdim'] = Choice(panel, wids['axes'],
                              size=(200, -1), action=self.onXdim)
        wids['ydim'] = Choice(panel, wids['axes'],
                              size=(200, -1), action=self.onYdim)
        wids['xdim'].SetSelection(0)
        wids['ydim'].SetSelection(1)

        wids['win'] = Choice(panel, WIN_CHOICES, size=(75, -1))
        wids['win'].SetStringSelection('1')

        wids['save_array'] = Button(panel, 'Save Array', size=(125, -1),
                                  action=self.onNameArray)
        wids['array_name'] = TextCtrl(panel, 'griddat', size=(200, -1),
                                      act_on_losefocus=False,
                                      action=self.onNameArray)
        wids['check_overwrite']  = Check(panel, ' ', size=(30, -1), default=True)



        def padd_text(text, dcol=1, size=(80, -1), newrow=True):
            panel.Add(SimpleText(panel, text, size=size), dcol=dcol, newrow=newrow)

        padd_text(' X: ', newrow=False)
        panel.Add(wids['xdim'])

        padd_text(' Y: ', newrow=False)
        panel.Add(wids['ydim'])

        padd_text(' ')
        panel.Add(wids['show'])
        padd_text(' Window:', size=(100, -1), newrow=False)
        panel.Add(wids['win'])

        panel.Add((5, 5), newrow=True)
        panel.Add(self.dim_reduce, dcol=5, newrow=True)
        panel.Add((5, 5), newrow=True)

        panel.Add(wids['save_array'], newrow=True)
        panel.Add(wids['array_name'])
        padd_text(' Verify Overwrite', size=(125, -1), newrow=False)
        panel.Add(wids['check_overwrite'], dcol=1)

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

    def onDimReduce(self, event=None, dim=None, reduce=None):
        self.onShow(new=True)

    def onShow(self, event=None, new=True):
        reddim = self.dim_reduce.get_result()

        win    = self.wids['win'].GetStringSelection()
        ydim   = self.wids['ydim'].GetSelection()
        xdim   = self.wids['xdim'].GetSelection()

        data_shape = self.data_obj.shape
        ndim = len(data_shape)
        reddim = self.dim_reduce.get_result(ndim)

        def _get_data(reddim):
            self._griddat = get_data(self.data_obj, reddim)

        data_thread = Thread(target=_get_data, args=(reddim,))
        t0_data = time.time()
        self.parent.status_message('fetching data....')
        data_thread.start()

        frame_opts = {'title':  f'SitkaGrid {win} '}
        gframe = self.show_gridframe(win, **frame_opts)
        alabel = dim_code(reddim)
        self.parent.access_code = f"['{self.filename}']['{self.itemname}']{alabel}"

        data_thread.join()
        dt_data = time.time()-t0_data
        if len(data_shape) < 2:
            data_shape = (1, data_shape[0])

        if len(self._griddat.shape) < 2:
            try:
                self._griddat.shape = (1, self._griddat.shape[0])
            except Exception:
                self._griddat.shape = (1,)

        _ny, _nx = self._griddat.shape
        _ry, _rx = data_shape[ydim], data_shape[xdim]
        _ry, _rx = data_shape[ydim], data_shape[xdim]

        dsize = datasize_repr(self._griddat)
        osize = datasize_repr(self.data_obj)

        self.parent.status_message(f'got data ({dsize} of {osize}) in {dt_data:.2f} seconds')
        self.parent.data.add_array('_tabledat', self._griddat, address=self.parent.access_code)

        # print(f"Got data {_nx=}  {_rx=}   {_ny=}  {_ry=}  {ydim=} {xdim=}")
        if _ry == _nx and _rx == _ny or (ydim > xdim):
            self._griddat = self._griddat.transpose()

        gframe.set_data2d(self._griddat, title=f'{self.filename}{alabel}')
        gframe.Show()
        gframe.Raise()

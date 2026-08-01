import ast
import numpy as np
import wx
import wx.dataview as dv

from wxutils import (GridPanel, SimpleText, pack, Button, TextCtrl, HLine,
                     Check, LEFT, get_color, register_darkdetect,
                     FileSave, Popup)

from pyshortcuts import isotime, fix_filename, get_cwd
from .gui_utils import get_font

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

class ArraysPanel(wx.Panel):
    """Panel for Named Arrays"""
    def __init__(self, parent, size=(700, 600)):
        wx.Panel.__init__(self, parent, size=size)
        self.parent = parent
        self.SetBackgroundColour(get_color('sbg'))

        self.access_code = ''
        self.wids = wids = {}
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)


        aview = self.wids['arrays'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        # aview.SetFont(get_font(fixed_width=True, smaller=1))
        aview.SetFont(get_font(fixed_width=False, smaller=1))
        aview.SetMinSize((725, 250))
        aview.AppendToggleColumn(' Select', width=60, mode=dv.DATAVIEW_CELL_ACTIVATABLE)
        aview.AppendTextColumn(' Array Name ', width=125)
        aview.AppendTextColumn(' Shape      ', width=100)
        aview.AppendTextColumn(' Origin     ', width=500)
        for col in range(4):
            align = wx.ALIGN_RIGHT if col == 2 else wx.ALIGN_LEFT
            this = aview.Columns[col]
            this.Sortable = True
            this.Alignment = this.Renderer.Alignment = align
        aview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectArray)

        wids['sel_all'] = Button(panel, 'Select All', size=(125, -1),
                                 action=self.onSelectAll)
        wids['sel_none'] = Button(panel, 'Select None', size=(125, -1),
                                  action=self.onSelectNone)

        wids['plot'] = Button(panel, 'Plot Current', size=(125, -1),
                                  action=self.onPlot)

        wids['save'] = Button(panel, 'Add Array', size=(125, -1),
                              action=self.onSaveArray)
        wids['array_name'] = TextCtrl(panel, ' ', size=(200, -1))
        wids['expr'] =  wx.TextCtrl(panel, value=' ',
                                    size=(400, -1),
                                    style=wx.TE_PROCESS_ENTER)
        wids['expr'].Bind(wx.EVT_TEXT_ENTER, self.onExpr)
        wids['expr'].Bind(wx.EVT_KILL_FOCUS, self.onExpr)

        wids['check_overwrite']  = Check(panel, ' ', size=(30, -1), default=True)
        wids['access_code'] = SimpleText(panel, ' ', size=(700, -1), style=LEFT)

        wids['delete'] = Button(panel, 'Delete Selected Arrays', size=(300, -1),
                              action=self.onDeleteArrays)

        wids['export'] = Button(panel, 'Export Selected Arrays to HDF5', size=(300, -1),
                                action=self.onExportArrays)

        def padd_text(text, dcol=1, size=(150, -1), newrow=True):
            panel.Add(SimpleText(panel, text, size=size, style=LEFT),
                      dcol=dcol, newrow=newrow)

        padd_text(' Named Arrays: ', newrow=False)
        panel.Add(wids['sel_all'], dcol=2)
        panel.Add(wids['sel_none'], dcol=1)
        panel.Add(wids['plot'], dcol=1)
        panel.Add(aview, dcol=7, drow=True, newrow=True)

        panel.Add(wids['access_code'], dcol=7, newrow=True)
        panel.Add((5, 5), newrow=True)
        panel.Add(wids['export'], dcol=3, newrow=True)
        panel.Add(wids['delete'], dcol=3)

        panel.Add(HLine(panel, size=(725, 3)), dcol=7, newrow=True)

        panel.Add((5, 5), newrow=True)

        padd_text(' Add a new array: use existing arrays and Python expressions ',
                  size=(650, -1), dcol=6, newrow=True)
        padd_text(' Array Name:  ', newrow=True)
        panel.Add(wids['array_name'], dcol=3)

        padd_text(' Expression: ', newrow=True)
        panel.Add(wids['expr'], dcol=3, newrow=False)
        panel.Add(wids['save'], newrow=True)
        padd_text(' Verify Overwrite', size=(125, -1), newrow=False)
        panel.Add(wids['check_overwrite'])

        panel.pack()
        panel.SetSize((700, 600))

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

    def onSaveArray(self, event=None):
        name = self.wids['array_name'].GetValue().strip()
        verify = self.wids['check_overwrite'].IsChecked()

        data = self.parent.data
        if verify and name in data.arrays:
            ret = Popup(self, f"Overwrite Array '{name}'?\n",
                        'Verify Overwrite',
                        style=wx.YES_NO|wx.ICON_QUESTION)
            if ret != wx.ID_YES:
                return

        expr = self.wids['expr'].GetValue()
        print(f"on Save Array {name=}  {expr=}")

        data._last_error = []

        ret = data.eval(expr)
        if len(data._last_error) > 0:
            Popup(self, 'Error evaluating Expression for array',
                  f"check '{expr}'")

        else:
            data.add_array(name, ret, address=expr)
            self.wids['access_code'].SetLabel(expr)
            self.set_object()

    def onPanelExposed(self, *args, **kws):
        self.set_object()

    def set_object(self, *args, **kws):
        data = self.parent.data
        self.array_data = []
        warrays = self.wids['arrays']
        warrays.DeleteAllItems()

        for aname, arr in data.arrays.items():
            addr = data.array_addrs.get(aname, 'unknown')
            args = [True, aname, repr(arr.shape), addr]
            self.array_data.append(args)
            warrays.AppendItem(tuple(args))

    def onExpr(self, evt=None, value=None):
        wexpr = self.wids['expr']
        if value is None:
            value = wexpr.GetValue()
        try:
            ast.parse(value)
            fgcol = get_color('text')
            bgcol = get_color('sbg')
        except SyntaxError:
            fgcol = get_color('text_invalid')
            bgcol = get_color('text_invalid_bg')

        wexpr.SetForegroundColour(fgcol)
        wexpr.SetBackgroundColour(bgcol)


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

    def onPlot(self, evt=None):
        if self.wids['arrays'] is None:
            return
        if not self.wids['arrays'].HasSelection():
            return
        item = self.wids['arrays'].GetSelectedRow()
        name = self.array_data[item][1]
        array = self.parent.data.arrays.get(name, None)
        if array is not None:
            title = self.parent.data.array_addrs.get(name, name)
            if len(array.shape) == 1:
                ipage, page = self.parent.get_page('Plot1DPanel')
                if page is not None:
                    frame = page.show_plotframe(window=1)
                    _x = np.arange(len(array))
                    frame.plot(_x, array, label=name, ylabel=name,
                               title=title)
                    frame.Show()
                    frame.Raise()
            elif (len(array.shape) == 2 or
                  (len(array.shape) == 3 and array.shape[2] == 3)):
                ipage, page = self.parent.get_page('ImagePanel')
                if page is not None:
                    frame = page.show_imageframe(window=1)
                    frame.display(array, title=f'{name}: {title}')
                    frame.Show()
                    frame.Raise()

    def get_arraynames(self, all=False):
        """get list of array names, either all or selected"""
        out = []
        arrays = self.parent.data.arrays
        warrays = self.wids['arrays']
        for row in range(warrays.GetItemCount()):
            sel = warrays.GetValue(row, 0)
            name = warrays.GetValue(row, 1)
            if all or sel and name in arrays:
                out.append(name)
        return out

    def onExportArrays(self, evt=None):
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


    def onDeleteArrays(self, evt=None):
        arrays = self.get_arraynames()
        ret = Popup(self, f"Erase {len(arrays)} Array?\nThis cannot be undone.",
                    'Verify erase',
                    style=wx.YES_NO|wx.ICON_QUESTION)
        if ret != wx.ID_YES:
            return

        for aname in arrays:
            self.parent.data.arrays.pop(aname)
        self.set_object()

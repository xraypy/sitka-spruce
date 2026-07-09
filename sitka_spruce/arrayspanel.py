import ast
import time
from threading import Thread
import wx
import wx.dataview as dv
import wx.lib.scrolledpanel as scrolled

from wxutils import (GridPanel, SimpleText, pack, Button, TextCtrl, HLine,
                     Check, Choice, LEFT, get_color, register_darkdetect)

from .gui_utils import get_font
from .data import ARRAY_TYPES, dtype2str, get_data, dim_code, datasize_repr

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

class ArraysPanel(wx.Panel):
    """Panel for Named Arrays"""
    def __init__(self, parent, size=(750, 500)):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.SetBackgroundColour(get_color('text_bg'))

        self.access_code = ''
        self.wids = wids = {}
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)


        aview = self.wids['arrays'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        aview.SetFont(get_font(fixed_width=True, smaller=1))
        aview.SetMinSize((725, 250))
        aview.AppendTextColumn(' Array Name ', width=150)
        aview.AppendTextColumn(' Shape      ', width=125)
        aview.AppendTextColumn(' Origin     ', width=575)
        for col in range(3):
            align = wx.ALIGN_RIGHT if col == 1 else wx.ALIGN_LEFT
            this = aview.Columns[col]
            this.Sortable = True
            this.Alignment = this.Renderer.Alignment = align
        aview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectArray)

        wids['save'] = Button(panel, 'Add Array', size=(125, -1),
                              action=self.onSaveArray)
        wids['array_name'] = TextCtrl(panel, ' ', size=(200, -1))
        wids['expr'] =  wx.TextCtrl(panel, value=' ',
                                    size=(400, -1),
                                    style=wx.TE_PROCESS_ENTER)
        wids['expr'].Bind(wx.EVT_TEXT_ENTER, self.onExpr)
        wids['expr'].Bind(wx.EVT_KILL_FOCUS, self.onExpr)

        wids['check_overwrite']  = Check(panel, ' ', size=(10, -1), default=True)
        wids['access_code'] = SimpleText(panel, ' ', size=(700, -1), style=LEFT)

        def padd_text(text, dcol=1, size=(150, -1), newrow=True):
            panel.Add(SimpleText(panel, text, size=size, style=LEFT),
                      dcol=dcol, newrow=newrow)

        padd_text(' Named Arrays: ')
        panel.Add(aview, dcol=7, drow=True, newrow=True)

        panel.Add(wids['access_code'], dcol=7, newrow=True)

        panel.Add(HLine(panel, size=(725, 3)), dcol=7)

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

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, 0, LEFT|wx.GROW, 4)
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

    def onSaveArray(self, event=None):
        name = self.wids['array_name'].GetValue()
        verify = self.wids['check_overwrite'].IsChecked()
        expr = self.wids['expr'].GetValue()
        print(f"on Save Array {name=} {verify=}, {expr=}")

        data = self.parent.data
        data._last_error = []

        ret = data.eval(expr)
        print("Did eval ", ret, len(data._last_error))

        if len(data._last_error) > 0:
            print("Error evaluating expression")
        else:
            data.add_array(name, ret, address=expr)
            self.wids['access_code'].SetLabel(expr)
            self.set_object()


    def onPanelExposed(self, *args, **kws):
        print("on Array Panel exposed ", args, kws)
        self.set_object()

    def set_object(self, *args, **kws):
        # print("Set object for Arrays")

        data = self.parent.data
        self.array_data = []
        warrays = self.wids['arrays']
        warrays.DeleteAllItems()

        for aname, arr in data.arrays.items():
            addr = data.array_addrs.get(aname, 'unknown')
            args = [aname, repr(arr.shape), addr]
            self.array_data.append(args)
            warrays.AppendItem(tuple(args))

    def onExpr(self, evt=None, value=None):
        wexpr = self.wids['expr']
        if value is None:
            value = wexpr.GetValue()
        try:
            ast.parse(value)
            fgcol = get_color('text')
            bgcol = get_color('text_bg')
        except SyntaxError:
            fgcol = get_color('text_invalid')
            bgcol = get_color('text_invalid_bg')

        wexpr.SetForegroundColour(fgcol)
        wexpr.SetBackgroundColour(bgcol)

    def onSelectArray(self, evt=None):
        if self.wids['arrays'] is None:
            return
        if not self.wids['arrays'].HasSelection():
            return
        item = self.wids['arrays'].GetSelectedRow()
        address = self.array_data[item][2]
        self.access_code = address
        self.wids['access_code'].SetLabel(address)

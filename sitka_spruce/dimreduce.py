import wx

from wxutils import (FloatSpin, GridPanel, SimpleText, Choice, HLine,
                     Check, LEFT, get_color, register_darkdetect)

class DimReduceWidgets():
    """panel for selecting how to reduce array dimension to scalar"""
    def __init__(self, parent, npts=1):
        self.wids = {}
        self.npts = npts
        self.min, self.max = 0, npts-1
        self.wids['npts'] = SimpleText(parent, str(npts), size=(70, -1), style=wx.ALIGN_RIGHT)

        fsopts = {'digits': 0, 'min_val': 0, 'max_val': npts-1, 'size':(75, -1),
                  'action': self.onMinMax}
        self.wids['min'] = FloatSpin(parent, value=0,      **fsopts)
        self.wids['max'] = FloatSpin(parent, value=npts-1, **fsopts)
        self.wids['fix_width'] = Check(parent, '', default=False)
        choices = ['sum', 'mean', 'single']
        self.wids['reduce'] = Choice(parent, choices, size=(100, -1),
                                     action=self.onReduce)
        self.wids['reduce'].SetSelection(0)

    def onMinMax(self, event=None):
        redval = self.wids['reduce'].GetStringSelection()
        fix_width = self.wids['fix_width'].IsChecked()
        if (redval in ('sum', 'mean') and fix_width):
            newmin = int(self.wids['min'].GetValue())
            newmax = int(self.wids['max'].GetValue())
            if newmax != self.max and newmin == self.min:
                delta = newmax - self.max
                self.max = newmax
                self.min = max(0, self.min+delta)
                self.wids['min'].SetValue(self.min)
            elif newmax == self.max and newmin != self.min:
                delta = newmin - self.min
                self.min = newmin
                self.max = min(self.npts-1, self.max+delta)
                self.wids['max'].SetValue(self.max)
        else:
            self.min = int(self.wids['min'].GetValue())
            self.max = int(self.wids['max'].GetValue())
        if self.min > self.max:
            newmin, newmax = self.max, self.min
            self.min, self.max = newmin, newmax
            self.wids['min'].SetValue(self.min)
            self.wids['max'].SetValue(self.max)


    def onReduce(self, event=None):
        redval = self.wids['reduce'].GetStringSelection()
        self.wids['max'].Enable(redval != 'single')
        self.wids['fix_width'].Enable(redval != 'single')

    def on_enable(self, enable=True, npts=None, **kws):
        for attr in ('npts', 'reduce', 'min', 'max', 'fix_width'):
            self.wids[attr].Enable(enable)
        if enable and npts is not None:
            self.set_npts(npts)

    def set_npts(self, npts):
        self.npts = npts
        self.wids['npts'].SetLabel(f'{npts}')
        self.wids['min'].SetMax(npts-1)
        self.wids['max'].SetMax(npts-1)
        self.wids['min'].SetValue(0)
        self.wids['max'].SetValue(npts-1)

    def get_result(self):
        result = self.wids['reduce'].GetStringSelection()
        x0 = int(self.wids['min'].GetValue())
        x1 = int(self.wids['max'].GetValue())
        return (result, x0, x1)

class DimReducePanel(wx.Panel):
    """ panel with dimenision-reduction choices"""
    def __init__(self, parent, maxdim=6):
        wx.Panel.__init__(self, parent)

        self.wids = {}
        self.maxdim = max(2, min(16, maxdim))
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)

        def padd_text(text, dcol=1, newrow=False, right=False):
            style = wx.ALIGN_RIGHT if right else wx.ALIGN_LEFT
            panel.Add(SimpleText(panel, text, style=style),
                      dcol=dcol, style=style, newrow=newrow)

        panel.Add(HLine(panel, size=(500, 3)), dcol=6)
        padd_text('Dimension Reduction for Multidimensional Arrays',
                  dcol=6, newrow=True)
        padd_text('Dim', newrow=True)
        padd_text('Npts', right=True)
        padd_text('Method')
        padd_text('Min')
        padd_text('Max')
        padd_text('Fix Width?')

        for i in range(maxdim):
            dw = self.wids[f'data_dim{i}'] = DimReduceWidgets(panel, npts=1)
            for wid in dw.wids.values():
                wid.Disable()
            padd_text(f' {i}:', newrow=True)
            panel.Add(dw.wids['npts'])
            panel.Add(dw.wids['reduce'])
            panel.Add(dw.wids['min'])
            panel.Add(dw.wids['max'])
            panel.Add(dw.wids['fix_width'])


        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)


        panel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, 0, LEFT|wx.EXPAND|wx.GROW, 2)

        panel.SetMinSize((400, 200))
        panel.SetSize((550, 300))
        register_darkdetect(self.onDarkMode)


    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('text_bg', dark=is_dark)

        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        for i in range(maxdim):
            dw = self.wids[f'data_dim{i}'] = DimReduceWidgets(panel, npts=1)
            dw.wids['npts'].SetForegroundColour(fgcol)

        wx.CallAfter(self.Refresh)


    def set_datashape(self, dshape):
        choices = []
        for i, npts in enumerate(dshape):
            self.enable_dimension(i, npts=npts)
            choices.append(f'dim{i}: {npts} points')

        for i in range(len(dshape), self.maxdim):
            self.enable_dimension(i, enable=False)
        return choices

    def enable_dimension(self, idim, enable=True, npts=None):
        wname = f'data_dim{idim}'
        if wname in self.wids:
            self.wids[wname].on_enable(enable=enable, npts=npts)

    def get_result(self):
        result = []
        for i in range(self.maxdim):
            ret = [i, self.wids[f'data_dim{i}'].wids['npts'].Enabled]
            ret.extend(self.wids[f'data_dim{i}'].get_result())
            result.append(ret)
        return result

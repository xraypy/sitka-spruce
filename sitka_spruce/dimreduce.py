from functools import partial
import wx

from wxutils import (FloatSpin, GridPanel, SimpleText, Choice, HLine,
                     Check, LEFT, get_color, register_darkdetect)

from .config import read_configfile

DEFAULT_OPTIONS = {'maxdim': 5, 'method': 'single', 'point': 'mid'}

class NumericCombo(wx.ComboBox):
    """
    Numeric Combo: ComboBox with numeric-only choices
    """
    def __init__(self, parent, choices, precision=1, fmt=None,
                 init=0, default_val=None, width=80, action=None):

        self.fmt = fmt
        if fmt is None:
            self.fmt = "%%.%if" % precision

        self.action = action
        self.choices  = choices
        schoices = [self.fmt % i for i in self.choices]
        wx.ComboBox.__init__(self, parent, -1, '', (-1, -1), (width, -1),
                             schoices, wx.CB_DROPDOWN|wx.TE_PROCESS_ENTER)

        init = min(init, len(self.choices))
        if default_val is not None:
            if default_val in schoices:
                self.SetStringSelection(default_val)
            else:
                self.add_choice(default_val, select=True)
        else:
            self.SetStringSelection(schoices[init])
        self.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        if action is not None:
            self.Bind(wx.EVT_COMBOBOX, action)

    def OnEnter(self, event=None):
        val = float(event.GetString())
        self.add_choice(val)
        if self.action is not None:
            self.action(val)

    def add_choice(self, val, select=True):
        if val not in self.choices:
            self.choices.append(val)
        self.choices.sort()
        self.Clear()
        self.AppendItems([self.fmt % x for x in self.choices])
        if select:
            self.SetSelection(self.choices.index(val))
            if self.action is not None:
                self.action(val)


class DimReduceWidgets():
    """panel for selecting how to reduce array dimension to scalar"""
    def __init__(self, parent, npts=1, options=None, callback=None):
        self.wids = {}
        self.npts = npts
        self.options = {k: v for k, v in DEFAULT_OPTIONS.items()}
        if options is not None:
            self.options.update(options)

        self.min, self.max = 0, npts-1
        self.callback = callback
        self.wids['npts'] = SimpleText(parent, str(npts), size=(65, -1),
                                       style=wx.ALIGN_RIGHT)

        fsopts = {'digits': 0, 'min_val': 0, 'max_val': npts-1, 'size':(85, -1),
                  'action': self.onMinMax}
        self.wids['min'] = FloatSpin(parent, value=0,      **fsopts)
        self.wids['max'] = FloatSpin(parent, value=npts-1, **fsopts)
        self.wids['fix_width'] = Check(parent, ' ', size=(75, -1), default=False)
        self.wids['live'] = Check(parent, ' ', size=(75, -1), default=False)
        choices = ['sum', 'mean', 'single']
        self.wids['reduce'] = Choice(parent, choices, size=(100, -1),
                                     action=self.onReduce)
        if self.options['method'] not in choices:
            self.options['method'] = 'single'
        self.wids['reduce'].SetStringSelection(self.options['method'])

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
        if self.wids['live'].IsChecked() and callable(self.callback):
            wx.CallAfter(self.callback, self.get_result())

    def onReduce(self, event=None):
        redval = self.wids['reduce'].GetStringSelection()
        self.wids['max'].Enable(redval != 'single')
        self.wids['fix_width'].Enable(redval != 'single')
        if self.wids['live'].IsChecked() and callable(self.callback):
            wx.CallAfter(self.callback, self.get_result())

    def on_enable(self, enable=True, npts=None, **kws):
        for attr in ('npts', 'reduce', 'min', 'max', 'fix_width', 'live'):
            self.wids[attr].Enable(enable)
        if enable and npts is not None:
            self.set_npts(npts)

    def set_npts(self, npts):
        self.npts = npts
        self.wids['npts'].SetLabel(f'{npts}')
        self.wids['min'].SetMax(npts-1)
        self.wids['max'].SetMax(npts-1)
        self.wids['max'].SetValue(npts-1)
        minval = 0
        if self.wids['reduce'].GetStringSelection() == 'single':
            self.wids['max'].Disable()
            if self.options['point'] == 'mid':
                minval = int(npts/2)
        self.wids['min'].SetValue(minval)

    def get_result(self):
        result = self.wids['reduce'].GetStringSelection()
        x0 = int(self.wids['min'].GetValue())
        x1 = int(self.wids['max'].GetValue())
        return (result, x0, x1)

class DimReducePanel(wx.Panel):
    """ panel with dimenision-reduction choices"""
    def __init__(self, parent, size=(725, -1), maxdim=5, callback=None):
        wx.Panel.__init__(self, parent, size=size)
        self.callback = callback
        self.wids = {}
        conf = read_configfile()
        self.dimopts = conf.get('dimreduce',  DEFAULT_OPTIONS)
        self.maxdim = max(2, min(16, int(self.dimopts.get('maxdim', 5))))
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)


        step_sizes = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        self.wids['stepsize'] = NumericCombo(panel, step_sizes, precision=0,
                                             width=100, action=self.onStepSize)

        def padd_text(text, dcol=1, newrow=False, size=(80, -1), right=False):
            style = wx.ALIGN_RIGHT if right else wx.ALIGN_LEFT
            panel.Add(SimpleText(panel, text, size=size, style=style),
                      dcol=dcol, style=style, newrow=newrow)

        panel.Add(HLine(panel, size=(725, 3)), dcol=7)
        padd_text('Dimension Reduction for ND Arrays',
                  size=(275, -1), dcol=4, newrow=True)
        panel.Add(SimpleText(panel, 'Min/Max Step Size:' , size=(150, -1), style=wx.ALIGN_RIGHT),
                  dcol=2, style=wx.ALIGN_RIGHT, newrow=False)
        panel.Add( self.wids['stepsize'], dcol=1)

        padd_text('Dim', size=(40, -1), newrow=True)
        padd_text('Npts', size=(65, -1), right=True)
        padd_text('Method')
        padd_text('Min')
        padd_text('Max')
        padd_text('Fix Width', size=(95, -1))
        padd_text('AutoUpdate?', size=(95, -1))

        for i in range(self.maxdim):
            dw = DimReduceWidgets(panel, npts=1, options=self.dimopts,
                                  callback=partial(self.onChange, i))
            self.wids[f'data_dim{i}'] = dw
            for wid in dw.wids.values():
                wid.Disable()
            padd_text(f' {i}', size=(35, -1), newrow=True)
            panel.Add(dw.wids['npts'])
            panel.Add(dw.wids['reduce'])
            panel.Add(dw.wids['min'])
            panel.Add(dw.wids['max'])
            panel.Add(dw.wids['fix_width'])
            panel.Add(dw.wids['live'])

        panel.Add(HLine(panel, size=(725, 3)), dcol=7, newrow=True)

        panel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, 0, LEFT|wx.EXPAND|wx.GROW, 2)

        panel.SetMinSize((500, 150))
        panel.SetSize(panel.GetBestSize())
        register_darkdetect(self.onDarkMode)

    def onStepSize(self, event=None):
        stepsize = int(self.wids['stepsize'].GetStringSelection())
        for i in range(self.maxdim):
            self.wids[f'data_dim{i}'].wids['min'].SetIncrement(stepsize)
            self.wids[f'data_dim{i}'].wids['max'].SetIncrement(stepsize)

    def onChange(self, dim, reduce):
        self.callback(dim=dim, reduce=reduce)

    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('sbg', dark=is_dark)

        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        for i in range(self.maxdim):
            dw = self.wids[f'data_dim{i}']
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

    def get_result(self, ndim=None):
        result = []
        if ndim is None:
            ndim = self.maxdim
        ndim = min(self.maxdim, ndim)
        for i in range(ndim):
            ret = [i, self.wids[f'data_dim{i}'].wids['npts'].Enabled]
            ret.extend(self.wids[f'data_dim{i}'].get_result())
            result.append(ret)
        return result

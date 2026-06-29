#!/usr/bin/env python
"""
sitka_spruce HDF5 and Zarr data browser
"""

import sys
import time
import glob
import numpy as np

import inspect
from functools import partial
from pathlib import Path

import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.mixins.inspection
import wx.html as html
from wx.adv import AboutBox, AboutDialogInfo

from wxmplot import PlotFrame, ImageFrame

import h5py

try:
    import zarr
except:
    zarr = None

try:
    import larch
except:
    larch = None

from wxutils import (FloatCtrl, FloatSpin, GridPanel,
                     SimpleText, pack, Button, HLine, Choice,
                     get_widget_value, set_widget_value,
                     TextCtrl, Check, CEN, RIGHT, LEFT,
                     get_color, register_darkdetect, MenuItem,
                     flatnotebook)

from pyshortcuts import uname, fix_filename, get_cwd

VERSION = '0.1'

from .gui_utils import Font, fontsize, get_font
from .data  import (get_items, get_itemtype, get_attributes,
                    get_data1d, get_data2d)


COMMONTYPES = (int, float, complex, str, bytes, bool, list, tuple, np.ndarray)

FILE_WILDCARD = 'HDF5/Zarr files(*.hdf5;*.h5;*.zarr)|*.hdf5;*.h5;*.zarr|All files (*.*)|*.*'

DV_STYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

ARRAY_TYPES = ('h5py.Dataset', 'zarr.Array', 'np.ndarray')
GROUP_TYPES = ('h5py.Group', 'zarr.Group', 'larch.Group')

def call_signature(obj):
    """try to get call signature for callable object"""
    fname = obj.__name__

    if isinstance(obj, partial):
        obj = obj.func

    argspec = None
    argspec = inspect.getfullargspec(obj)
    keywords = argspec.varkw

    fargs = []
    ioff = len(argspec.args) - len(argspec.defaults)
    for iarg, arg in enumerate(argspec.args):
        if iarg < ioff:
            fargs.append(arg)
        else:
            fargs.append(f"{arg}={repr(argspec.defaults[iarg-ioff])}")
    if keywords is not None:
        fargs.append(f"**{keywords}")

    out = f"{fname}({', '.join(fargs)})"
    maxlen = 71
    if len(out) > maxlen:
        o  = []
        while len(out) > maxlen:
            ecomm = maxlen - out[maxlen-1::-1].find(',')
            o.append(out[:ecomm])
            out = " "*(len(fname)+1) + out[ecomm:].strip()
        if len(out)  > 0:
            o.append(out)
        out = '\n'.join(o)
    return out

class H5ZTree(wx.TreeCtrl):
    """FillingTree based on TreeCtrl."""
    __label__ = 'Data'

    def __init__(self, parent, root_data=None, root_label=None,
                 size=(300, 250),
                 style=wx.TR_DEFAULT_STYLE|wx.TR_HIDE_ROOT,
                 on_select=None):
        """Create FillingTree instance."""
        wx.TreeCtrl.__init__(self, parent, size=size, style=style)
        self.item = None
        self.on_select = None
        if callable(on_select):
            self.on_select = on_select
        self.root_label = root_label
        self.set_root(root_data)

    def set_root(self, root_data=None):
        if root_data is None:
            root_data = {}
        self.root_data = root_data
        if self.root_label is None:
            self.root_label = self.__label__

        self.item = self.root = self.AddRoot(self.root_label, -1, -1,  self.root_data)

        self.SetItemHasChildren(self.root,  self.objHasChildren(self.root_data))
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelectionChanged, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnItemExpanding, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed, id=self.GetId())

    def OnItemExpanding(self, event=None):
        """Add children to the item."""
        try:
            item = event.GetItem()
        except:
            item = self.item
        if self.IsExpanded(item):
            return
        self.addChildren(item)
        self.SelectItem(item)

    def OnItemCollapsed(self, event=None):
        """Remove all children from the item."""
        item = event.GetItem()

    def OnSelectionChanged(self, event=None):
        """Display information about the item."""
        if hasattr(event, 'GetItem'):
            self.item = event.GetItem()
        self.display()

    def objHasChildren(self, obj):
        """Return true if object has children."""
        children = self.objGetChildren(obj)
        if isinstance(children, dict):
            return len(children) > 0
        else:
            return False

    def objGetChildren(self, obj):
        """Return dictionary with attributes or contents of object."""
        out = {}
        if (obj is None or obj is False or obj is True):
            pass
        elif isinstance(obj, COMMONTYPES):
            out = obj
        elif isinstance(obj, (list, tuple)):
            out = {}
            for n in range(len(obj)):
                key = '[' + str(n) + ']'
                out[key] = obj[n]
        else:
            out = get_items(obj)
        return out

    def addChildren(self, item):
        self.DeleteChildren(item)
        obj = self.GetItemData(item)
        for key, value in self.objGetChildren(obj).items():
            branch = self.AppendItem(parent=item, text=key, data=value)
            self.SetItemHasChildren(branch, self.objHasChildren(value))

    def display(self):
        item = self.item
        if not item:
            return
        obj = self.GetItemData(item)
        if wx.Platform == '__WXMSW__' and obj is None:
            return

        if self.IsExpanded(item):
            self.addChildren(item)
        self.SetItemHasChildren(item, self.objHasChildren(obj))

        if self.on_select is not None:
            filename = self.get_fullname(item)
            itemname = ''
            if '/' in filename:
                filename, itemname = filename.split('/', 1)
            self.on_select(obj, filename=filename,
                           itemname=itemname,
                           itemtype=get_itemtype(obj))

    def get_fullname(self, item, part=''):
        """Return a syntactically proper name for item."""
        try:
            name = self.GetItemText(item)
        except:
            print("no name ? ", item)
            return None

        parent = None
        obj = None
        if item != self.root:
            parent = self.GetItemParent(item)
            obj = self.GetItemData(item)
        # Apply dictionary syntax to dictionary items, except the root
        # and first level children of a namepace.
        if ((isinstance(obj, dict) or hasattr(obj, 'keys')) and
            ((item != self.root and parent != self.root))):
            name = f'{name}'
        if len(part) > 0:
             name = f'{name}/{part}'
        # Repeat for everything but the root item
        # and first level children of a namespace.
        if (item != self.root and parent != self.root):
            name = self.get_fullname(parent, part=name)
        return name

class DimReduceWidgets():
    """panel for selecting how to reduce array dimension to scalar"""
    def __init__(self, parent, npts=1):
        self.wids = wids = {}
        self.npts = npts
        self.min, self.max = 0, npts-1
        wids['npts'] = SimpleText(parent, str(npts), size=(70, -1), style=wx.ALIGN_RIGHT)

        fsopts = {'digits': 0, 'min_val': 0, 'max_val': npts-1, 'size':(75, -1),
                  'action': self.onMinMax}
        wids['min'] = FloatSpin(parent, value=0,      **fsopts)
        wids['max'] = FloatSpin(parent, value=npts-1, **fsopts)
        wids['fix_width'] = Check(parent, '', default=False)
        choices = ['sum', 'mean', 'single']
        wids['reduce'] = Choice(parent, choices, size=(100, -1),
                                 action=self.onReduce)
        wids['reduce'].SetSelection(0)

    def onMinMax(self, event=None):
        redval = self.wids['reduce'].GetStringSelection()
        fix_width = self.wids['fix_width'].IsChecked()
        # print(f'onMinMax  {redval=}  {fix_width=} {self.min=}  {self.max=}')

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

        self.wids = wids = {}
        self.maxdim = max(2, min(16, maxdim))
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)

        def padd_text(text, dcol=1, newrow=False, right=False):
            style = wx.ALIGN_RIGHT if right else wx.ALIGN_LEFT
            panel.Add(SimpleText(panel, text, style=style),
                      dcol=dcol, style=style, newrow=newrow)

        padd_text('Dimension Reduction for Multidimensional Arrays', dcol=6)
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
        panel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, 0, LEFT|wx.EXPAND|wx.GROW, 2)

        panel.SetMinSize((400, 200))
        panel.SetSize((500, 300))

    def set_datashape(self, dshape):
        choices = []
        for i, npts in enumerate(dshape):
            self.enable_dimension(i, npts=npts)
            choices.append(f'dim{i}: {npts} points')

        for i in range(len(dshape), self.maxdim):
            self.enable_dimension(i, enable=False)
        return choices

    def enable_dimension(self, idim, enable=True, npts=None):
        self.wids[f'data_dim{idim}'].on_enable(enable=enable, npts=npts)

    def get_result(self):
        result = []
        for i in range(self.maxdim):
            ret = [i, self.wids[f'data_dim{i}'].wids['npts'].Enabled]
            ret.extend(self.wids[f'data_dim{i}'].get_result())
            result.append(ret)
        return result


class ArrayPlotPanel(wx.Panel):
    """X/Y Plot Config Panel for HDF5/Zarr datasets"""
    def __init__(self, parent, size=(500, 500)):
        wx.Panel.__init__(self, parent)

        self.SetBackgroundColour(get_color('nb_area'))

        self.data_shape = None
        self.data_obj = None
        self.last_yaxes = 0
        self.plotframes = {}
        self.dim_reduce = DimReducePanel(parent=self)
        self.wids = wids = {}
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)

        wids['newplot'] = Button(panel, 'New Plot', size=(150, -1),
                              action=self.onPlot)
        wids['overplot'] = Button(panel, 'Over Plot', size=(150, -1),
                                  action=partial(self.onPlot, new=False))

        wids['sharey'] = Check(panel, 'share y-axis?', default=False)
        wids['win'] = Choice(panel, ['1', '2', '3', '4', '5'], size=(75, -1))
        wids['win'].SetStringSelection('1')

        wids['ychoices'] =  ['dim0: 0 points']
        wids['normchoices'] = ['1']
        wids['xchoices'] = ['<index>']

        wids['yarray'] = Choice(panel, wids['ychoices'],
                                size=(175, -1), action=self.onYarray)
        wids['yop'] = Choice(panel, ['+', '-', '*', '/'],
                                   size=(75, -1), action=self.onPlot)
        wids['yop'].SetStringSelection('/')

        wids['ynorm'] = Choice(panel, wids['normchoices'],
                                size=(175, -1), action=self.onPlot)

        wids['xarray'] = Choice(panel, wids['xchoices'],
                                size=(175, -1), action=self.onPlot)

        def padd_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        titleopts = {'font': get_font(larger=1),
                     'colour': 'title_red', 'style': LEFT}

        padd_text('Y array', newrow=False)
        panel.Add(wids['yarray'])
        panel.Add(wids['yop'])
        panel.Add(wids['ynorm'])

        padd_text('X array')
        panel.Add(wids['xarray'], dcol=2)
        panel.Add((5,5), newrow=True)
        panel.Add(wids['newplot'])
        padd_text(' window:', newrow=False)
        panel.Add(wids['win'])
        panel.Add((5,5), newrow=True)
        panel.Add(wids['overplot'])
        panel.Add(wids['sharey'], dcol=2)

        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel,           0, 0, LEFT|wx.GROW, 2)
        sizer.Add(self.dim_reduce, 0, 0, LEFT|wx.GROW, 2)
        pack(self, sizer)


    def set_object(self, object, itemtype='?', itemname='', filename='', **kws):
        """fill from object"""
        # print("set object ", object, itemtype, kws)
        self.filename = filename
        self.itemname = itemname
        isdata = (itemtype in ARRAY_TYPES)
        self.data_obj = object
        if isdata:
            self.data_shape = object.shape
            choices = self.dim_reduce.set_datashape(object.shape)
            cur = self.wids['yarray'].GetSelection()
            self.wids['yarray'].SetChoices(choices)
            self.dim_reduce.enable_dimension(cur, enable=False, npts=None)

        self.wids['yarray'].Enable(isdata)
        self.Refresh()

    def onYarray(self, event=None):
        sel = self.wids['yarray'].GetSelection()
        if self.data_shape is not None:
            for i, npts in enumerate(self.data_shape):
                self.dim_reduce.enable_dimension(i, enable=(i!=sel), npts=npts)

    def onPlot(self, event=None, new=True):
        # print("plot " , new, self.data_obj)
        reddim = self.dim_reduce.get_result()
        win    = self.wids['win'].GetStringSelection()
        sharey = self.wids['sharey'].IsChecked()
        ydim   = self.wids['yarray'].GetSelection()
        ylabel = self.wids['yarray'].GetStringSelection()
        ynorm  = self.wids['ynorm'].GetStringSelection()
        yop    = self.wids['yop'].GetStringSelection()
        xarray = self.wids['xarray'].GetStringSelection()
        ###
        print(f"plot  {ydim=}, {yop=}, {ynorm=}, {xarray=}, {win=}, {sharey=}")
        yarr, alabel = get_data1d(self.data_obj, ydim, reddim)
        xarr = np.arange(len(yarr))
        if 'ynorm' == '1':
            ynorm  = 1.0
        if xarray == '<index>':
            xarr = np.arange(len(yarr))

        frame_opts = {'title':  f'SitkaSpruce PlotWindow {win} '}
        pframe = self.show_plotframe(win, **frame_opts)

        plot = pframe.oplot
        ylabel = f'{self.itemname}{alabel}'
        opts = {'title': f'{self.filename}'}
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
        opts['label'] = ylabel
        print(opts)
        plot(xarr, yarr, **opts)
        pframe.Show()
        pframe.Raise()

    def show_plotframe(self, window=1, **opts):
        shown = False
        if window in self.plotframes:
            try:
                self.plotframes[window].Raise()
                shown = True
            except:
                f = self.plotframes.pop(window)
                del f
                shown = False
        if not shown:
            self.plotframes[window] = PlotFrame(self, **opts)
            self.plotframes[window].Raise()
        return self.plotframes[window]



class ArrayImagePanel(wx.Panel):
    """Image Show Config Panel for HDF5/Zarr datasets"""
    def __init__(self, parent, size=(500, 500)):
        wx.Panel.__init__(self, parent)

        self.SetBackgroundColour(get_color('nb_area'))

        self.wids = wids = {}
        panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)
        wids['imshow'] = Button(panel, 'Show Image', size=(150, -1),
                                action=self.onImshow)


        wids['plot_xchoices'] = ['<index>']
        wids['plot_xval'] = Choice(panel, wids['plot_xchoices'],
                                   size=(200, -1), action=self.onPlot)
        #
        def padd_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)


        padd_text('Select X dimension')
        panel.Add(wids['plot_xval'])
        panel.Add(wids['imshow'], newrow=True)

        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, 0, LEFT|wx.EXPAND|wx.GROW, 2)
        pack(self, sizer)


    def set_object(self, object, itemtype, name='?'):
        """fill from object"""
        print("fill ", itemtype, name, object)
        self.Refresh()

    def onPlot(self, event=None):
        print("plot")

    def onImshow(self, event=None):
        print("imshow")


class HDF5_Frame(wx.Frame):
    """Frame containing the namespace tree component."""
    name = 'HDF5 Data Tree'
    def __init__(self, parent=None, root_data=None,
                 title='HDF5 Data Tree', id=-1,
                 pos=wx.DefaultPosition, size=(850, 600),
                 style=wx.DEFAULT_FRAME_STYLE):
        """Create HDF5_Frame instance."""
        self.wids = {}
        wx.Frame.__init__(self, parent, id, title, pos, size, style)
        self.create_display(root_data, size=size)
        self.CreateStatusBar()
        self.SetStatusText('Welcome to HDF5 Browser')
        self.BuildMenus()


    def create_display(self, root_data, size=(850, 600)):
        splitter = wx.SplitterWindow(self, size=size, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(250)

        leftpanel = wx.Panel(splitter)
        rightpanel = scrolled.ScrolledPanel(splitter)

        self.tree = H5ZTree(leftpanel, root_data=root_data,
                            on_select=self.onObjectSelect)

        self.info = dv.DataViewListCtrl(leftpanel, style=DV_STYLE)
        self.info.AppendTextColumn('Name', width=125)
        self.info.AppendTextColumn('Value', width=175)
        for col in (0, 1):
            this = self.info.Columns[col]
            this.Sortable = False
            this.Alignment = this.Renderer.Alignment = wx.ALIGN_LEFT

        self.tree.SetMinSize((300, 250))
        self.info.SetMinSize((300, 250))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.ALL|wx.GROW)
        sizer.Add(self.info, 0, wx.ALL|wx.GROW)
        pack(leftpanel, sizer)

        self.filename_label = SimpleText(rightpanel, '', font=get_font(larger=1),
                                         colour='title_red', size=(500, -1),
                                         style=LEFT|wx.ALIGN_CENTER_VERTICAL)
        self.itemname_label = SimpleText(rightpanel, '', font=get_font(larger=1),
                                         colour='title_red', size=(500, -1),
                                         style=LEFT|wx.ALIGN_CENTER_VERTICAL)

        self.nb = flatnotebook(rightpanel, {},
                               on_change=self.onNBChanged,
                               # style=FNB_STYLE,
                               size=(550, 600))

        # self.mainpanel = ArrayViewPanel(splitter)
        self.nb.AddPage(ArrayPlotPanel(self), 'X/Y Plots', True)
        self.nb.AddPage(ArrayImagePanel(self), 'Image Display', True)
        # self.nb.AddPage(ArrayTablePanel, 'Table View', True)
        self.nb.SetSelection(0)
        self.current_nbpage = self.nb.GetSelection()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.filename_label, 0, wx.ALL|wx.LEFT, 4)
        sizer.Add(self.itemname_label, 0, wx.ALL|wx.LEFT, 4)
        sizer.Add(self.nb, 1, wx.ALL|wx.GROW, 4)
        pack(rightpanel, sizer)

        rightpanel.SetBackgroundColour(get_color('nb_area'))
        self.nb.SetBackgroundColour(get_color('nb_area'))
        self.nb.SetForegroundColour(get_color('nb_area'))
        self.tree.SetBackgroundColour(get_color('list_bg'))
        self.tree.SetForegroundColour(get_color('list_fg'))


        self.info.SetFont(get_font())
        self.tree.SetFont(get_font())
        self.set_fontsize(14)

        splitter.SplitVertically(leftpanel, rightpanel, 300)
        splitter.SetMinimumPaneSize(175)
        register_darkdetect(self.onDarkMode)

        # Display the root item.
        if self.tree.root is not None:
            self.tree.display()

    def onNBChanged(self, event=None):
        oldpage = self.nb.GetPage(event.GetOldSelection())
        newpage = self.nb.GetPage(event.GetSelection())
        on_hide = getattr(oldpage, 'onPanelHidden', None)
        if callable(on_hide):
            on_hide()
        on_expose = getattr(newpage, 'onPanelExposed', None)
        if callable(on_expose):
            on_expose()


    def onObjectSelect(self, object, filename='', itemname='', itemtype='?'):
        if len(filename) < 1:
            filename = ''
        self.filename_label.SetLabel(f" Filename: {filename}")
        if len(itemname) < 1:
            itemname = ''
        self.itemname_label.SetLabel(f" Address: {itemname}")
        self.fill_info(filename, itemtype, object)

        curpage = self.nb.GetPage(self.current_nbpage)
        try:
            curpage.set_object(object, itemtype=itemtype,
                               filename=filename, itemname=itemname)
        except Exception:
            pass


    def fill_info(self, name, itemtype, object):
        self.info.DeleteAllItems()
        if name == 'Data':
            self.info.AppendItem(('name', 'toplevel'))
        else:
            name = Path(name).name
            self.info.AppendItem(('name', name))
            self.info.AppendItem(('datatype', itemtype))
            for key, val in get_attributes(object).items():
                self.info.AppendItem((key, val))

        self.info.Refresh()

    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('text_bg', dark=is_dark)
        orint("Colors ", fgcol, bgcol)
        self.tree.SetBackgroundColour(bgcol)
        self.tree.SetForegroundColour(fgcol)
        self.info.SetBackgroundColour(bgcol)
        self.info.SetForegroundColour(fgcol)
        wx.CallAfter(self.Refresh)
#         self.text.SetBackgroundColour(bgcol)
#         self.text.SetForegroundColour(fgcol)


    def Raise(self):
        self.SetStatusText("Ready", 0)
        self.Refresh()
        wx.Frame.Raise(self)

    def BuildMenus(self):
        menuBar = wx.MenuBar()
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Read Data File\tCtrl+O",
                 "Read Data File", self.onReadData)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, 'Show wxPython Inspector\tCtrl+I',
                 'Debug wxPython App', self.onWxInspect)

        self.Bind(wx.EVT_CLOSE,  self.onExit)
        MenuItem(self, fmenu, 'E&xit', 'Exit', self.onExit)
        menuBar.Append(fmenu, '&File')

        omenu = wx.Menu()
        MenuItem(self, omenu,  "Increase Font Size", "", self.onIncreaseFont)
        MenuItem(self, omenu,  "Decrease Font Size", "", self.onDecreaseFont)
        menuBar.Append(omenu, 'Options')

        #hmenu = wx.Menu()
        #MenuItem(self, hmenu, '&About',
        #         'Information about this program',  self.onAbout)
        #menuBar.Append(hmenu, '&Help')
        self.SetMenuBar(menuBar)

    def onIncreaseFont(self, event=None):
        self.set_fontsize(self.GetFont().GetPointSize()+1)

    def onDecreaseFont(self, event=None):
        self.set_fontsize(self.GetFont().GetPointSize()-1)

    def set_fontsize(self, fsize):
        self.fontsize =  fsize
        def set_fsize(obj, fsize):
            fn = obj.GetFont()
            fn.SetPointSize(fsize)
            obj.SetFont(fn)

        set_fsize(self, fsize)

        set_fsize(self.tree,  fsize)
        set_fsize(self.info,  fsize)
        set_fsize(self.nb,  fsize)

    def onWxInspect(self, event=None):
        wx.GetApp().ShowInspectionTool()

    def show_subframe(self, event=None, name=None, creator=None, **opts):
        if name is None or creator is None:
            return
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                del self.subframes[name]
        if not shown:
            self.subframes[name] = creator(parent=self, **opts)
            self.subframes[name].Show()

    def onReadData(self, event=None):
        dlg = wx.FileDialog(self, message='Open Data File',
                            defaultDir=get_cwd(),
                            wildcard=FILE_WILDCARD,
                            style=wx.FD_OPEN|wx.FD_CHANGE_DIR)
        path = None
        if dlg.ShowModal() == wx.ID_OK:
            path = Path(dlg.GetPath()).absolute()
        dlg.Destroy()

        if path is None:
            return

        fname = path.name
        if fname in self.data:
            dlg = wx.MessageDialog(None, f'File {fname} already exists... re-read?', 'Question',
                                   wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            ret = dlg.ShowModal()
            if ret == wx.ID_NO:
                return

        try:
            self.data[fname] = h5py.File(fname, 'r')
        except Exception:
            pass
        # self.filling.tree.display()
        # self.filling.ShowNode(fname)

    def onChangeDir(self, event=None):
        dlg = wx.DirDialog(None, 'Choose a Working Directory',
                           defaultPath = get_cwd(),
                           style = wx.DD_DEFAULT_STYLE)

        if dlg.ShowModal() == wx.ID_OK:
            os.chdir(dlg.GetPath())
        dlg.Destroy()
        return get_cwd()

    def onAbout(self, event=None):
        about_msg =  """HDF5 Viewer"""
        dlg = wx.MessageDialog(self, about_msg,
                               "About HDF5 Viewer", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()


    def onExit(self, event=None):
        dlg = wx.MessageDialog(None, 'Really Quit?', 'Question',
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        ret = dlg.ShowModal()

        if ret == wx.ID_YES:
            try:
                for a in self.GetChildren():
                    a.Destroy()
            except:
                pass
            self.Destroy()
        else:
            try:
                event.Veto()
            except:
                pass

class HDF5_App(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    "simple app to wrap HDF5_Frame"
    def __init__(self, with_inspect=False, root_data=None, **kws):
        self.with_inspect = with_inspect
        self.root_data = root_data
        wx.App.__init__(self, **kws)

    def createApp(self):
        self.frame = HDF5_Frame(root_data=self.root_data)
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True

    def OnInit(self):
        self.createApp()
        if self.with_inspect:
            self.ShowInspectionTool()
        return True

    def set_data(self, root_data):
        self.frame.root_data = self.root_data = root_data

    def run(self):
        self.MainLoop()

if __name__ == '__main__':
    files = {}
    for fname in sorted(glob.glob('*.h5')):
        try:
            obj = h5py.File(fname)
            files[fname] = obj
        except Exception:
            pass
        if len(files) > 2:
            break

    app = HDF5_App(root_data=files, with_inspect=False)
    app.MainLoop()

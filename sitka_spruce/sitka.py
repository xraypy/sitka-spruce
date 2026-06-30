#!/usr/bin/env python
"""
sitka_spruce HDF5 and Zarr data browser
"""

import sys
import time
import glob
import numpy as np

from functools import partial
from pathlib import Path

import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.mixins.inspection
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
from .data  import (get_items, get_itemtype, get_attributes, get_data)


COMMONTYPES = (int, float, complex, str, bytes, bool, list, tuple, np.ndarray)

FILE_WILDCARD = 'HDF5/Zarr files(*.hdf5;*.h5;*.zarr)|*.hdf5;*.h5;*.zarr|All files (*.*)|*.*'

FILE_SUFFIXES = {'hdf5': h5py.File, 'h5': h5py.File}
if zarr is not None:
    FILE_SUFFIXES['zarr'] = zarr.open


DV_STYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

ARRAY_TYPES = ('h5py.Dataset', 'zarr.Array', 'np.ndarray')
GROUP_TYPES = ('h5py.Group', 'zarr.Group', 'larch.Group')

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
            filename, itemname = self.get_fullname(item)
            self.on_select(obj, filename=filename,
                           itemname=itemname,
                           itemtype=get_itemtype(obj))

    def oldget_fullname(self, item, part=''):
        """Return a syntactically proper name for item."""
        try:
            name = self.GetItemText(item)
        except:
            print("no name ? ", item)
            return None
        print(f"Get Fullname1 {item=}  {name=} {part=}")
        print(f"Get Fullname2 ", dir(item))

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
        print(f"Get Fullname:  {name=}")
        return name

    def get_fullname(self, item):
        """Return a syntactically proper name for item."""
        try:
            name = self.GetItemText(item)
        except:
            print("no name ? ", item)
            return '', ''

        tree = [name]
        while item != self.root:
            item = self.GetItemParent(item)
            if item.IsOk() and item != self.root:
                tree.append(self.GetItemText(item))

        filename = tree.pop()
        tree.reverse()
        itemname = '/'.join(tree)
        return filename, itemname


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
        panel.SetSize((550, 300))

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
        # print(f"plot  {ydim=}, {yop=}, {ynorm=}, {xarray=}, {win=}, {sharey=}")
        yarr, alabel = get_data(self.data_obj, reddim)
        xarr = np.arange(len(yarr))
        if 'ynorm' == '1':
            ynorm  = 1.0
        if xarray == '<index>':
            xarr = np.arange(len(yarr))

        frame_opts = {'title':  f'SitkaPlot {win} '}
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


        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 0, 0, LEFT|wx.GROW, 2)
        sizer.Add(self.dim_reduce, 0, 0, LEFT|wx.GROW, 2)
        pack(self, sizer)

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
        print("fill 2d obj ", itemtype, itemname, filename, object)

        self.filename = filename
        self.itemname = itemname
        isdata = (itemtype in ARRAY_TYPES)
        self.data_obj = object
        if isdata:
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
            except:
                f = self.imageframes.pop(window)
                del f
                shown = False
        if not shown:
            self.imageframes[window] = ImageFrame(self, **opts)
            self.imageframes[window].Raise()
        return self.imageframes[window]

    def onImshow(self, event=None, new=True):
        print("imshow ", new)

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
        print(f"imshow  {ydim=}, {xdim=}, {xdstr=}, {ydstr=}, {win=}, {ydir=}")

        img, alabel = get_data(self.data_obj, reddim)

        print("Got image ", img.shape, self.data_shape, alabel)
        _ny, _nx = img.shape

        _ry, _rx = self.data_shape[ydim], self.data_shape[xdim]

        print("Got image {_nx=}  {_rx=}   {_ny=}  {_ry=}  ")

        if _ry == _nx and _rx == _ny:
            img = img.transpose()

        if ydir:
            img = img[::-1, :]

        # xarr = np.arange(len(yarr))
        # xarr = np.arange(len(yarr))

        frame_opts = {'title':  f'SitkaImage {win} '}
        iframe = self.show_imageframe(win, **frame_opts)

        opts = {'title': f'{self.filename}{alabel}'}
        iframe.display(img)
        iframe.Show()
        iframe.Raise()



class SitkaFrame(wx.Frame):
    """Main Window for Sitka HDF5/Zarr viewer"""
    def __init__(self, parent=None, root_data=None,
                 title='Sitka HDF5 Viewer', id=-1,
                 pos=wx.DefaultPosition, size=(900, 650),
                 style=wx.DEFAULT_FRAME_STYLE):
        """Create Frame instance."""
        self.wids = {}
        wx.Frame.__init__(self, parent, id, title, pos, size, style)
        self.create_display(root_data, size=size)
        self.CreateStatusBar()
        self.SetStatusText('Welcome to HDF5 Browser')
        self.BuildMenus()


    def create_display(self, root_data, size=(900, 650)):
        splitter = wx.SplitterWindow(self, size=size, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(300)

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

        self.tree.SetMinSize((325, 300))
        self.info.SetMinSize((325, 300))

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

        splitter.SplitVertically(leftpanel, rightpanel, 1)
        splitter.SetMinimumPaneSize(300)
        register_darkdetect(self.onDarkMode)

        # Display the root item.
        if self.tree.root is not None:
            self.tree.display()

    def onNBChanged(self, event=None):
        oldpage = self.nb.GetPage(event.GetOldSelection())
        newpage = self.nb.GetPage(event.GetSelection())
        self.current_nbpage = event.GetSelection()
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

        # print(f"on Object {itemtype=}, {itemname=}, {filename=}", object)
        self.itemname_label.SetLabel(f" Address: {itemname}")
        self.fill_info(filename, itemtype, object)

        for ipage in range(self.nb.GetPageCount()):
            page = self.nb.GetPage(ipage)
            page.set_object(object, itemtype=itemtype,
                           filename=filename, itemname=itemname)


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

class Sitka_App(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    "simple app to wrap HDF5_Frame"
    def __init__(self, with_inspect=False, root_data=None, **kws):
        self.with_inspect = with_inspect
        self.root_data = root_data
        wx.App.__init__(self, **kws)

    def createApp(self):
        self.frame = SitkaFrame(root_data=self.root_data)
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

    app = Sitka_App(root_data=files, with_inspect=False)
    app.MainLoop()
    def run(self):
        self.MainLoop()

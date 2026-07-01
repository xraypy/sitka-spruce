#!/usr/bin/env python
"""
sitka_spruce HDF5 and Zarr data browser
"""

import sys
import time
import glob
from pathlib import Path

import numpy as np

import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.mixins.inspection
from wx.adv import AboutBox, AboutDialogInfo

from wxmplot import ImageFrame

import h5py
import zarr

try:
    import larch
except:
    larch = None

from wxutils import (FloatCtrl, FloatSpin, GridPanel,
                     SimpleText, pack, Button, HLine, Choice,
                     get_widget_value, set_widget_value,
                     TextCtrl, Check, CEN, RIGHT, LEFT,
                     get_color, use_darkdetect, register_darkdetect, MenuItem,
                     flatnotebook)

from pyshortcuts import uname, fix_filename, get_cwd

VERSION = '0.1'

from .gui_utils import Font, fontsize, get_font
from .data  import (get_items, get_itemtype, get_attributes, get_data,
                    SitkaData, ARRAY_TYPES)
from .hdatatree import HDataTree
from .plot1dpanel import ArrayPlot1DPanel
from .plot2dpanel import ArrayImagePanel


FILE_WILDCARD = 'HDF5/Zarr files(*.hdf5;*.h5;*.zarr)|*.hdf5;*.h5;*.zarr|All files (*.*)|*.*'

FILE_SUFFIXES = {'hdf5': h5py.File, 'h5': h5py.File, 'zarr': zarr.open}
if zarr is not None:
    FILE_SUFFIXES['zarr'] = zarr.open


DV_STYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

class SitkaFrame(wx.Frame):
    """Main Window for Sitka HDF5/Zarr viewer"""
    def __init__(self, parent=None, title='Sitka HDF5 Viewer',
                 size=(900, 650),  style=wx.DEFAULT_FRAME_STYLE):
        """Create Frame instance."""
        self.data = SitkaData()
        self.wids = {}
        wx.Frame.__init__(self, parent, title=title, size=size,
                          style=style)
        self.create_display(size=size)
        self.CreateStatusBar()
        self.SetStatusText('Welcome to Sitka')
        self.BuildMenus()


    def create_display(self, size=(900, 650)):
        splitter = wx.SplitterWindow(self, size=size, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(300)

        leftpanel = wx.Panel(splitter)
        rightpanel = scrolled.ScrolledPanel(splitter)

        self.tree = HDataTree(leftpanel, on_select=self.onSelectObject)

        self.info = dv.DataViewListCtrl(leftpanel, style=DV_STYLE)
        self.info.AppendTextColumn('Name', width=125)
        self.info.AppendTextColumn('Value', width=175)
        for col in (0, 1):
            this = self.info.Columns[col]
            this.Sortable = False
            this.Alignment = this.Renderer.Alignment = wx.ALIGN_LEFT

        self.tree.SetMinSize((350, 300))
        self.info.SetMinSize((350, 300))

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
        self.nb.AddPage(ArrayPlot1DPanel(self), 'X/Y Plots', True)
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
        self.tree.set_root(self.data.datasets)
        if self.tree.root is not None:
            self.tree.OnSelectionChanged()

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


    def onSelectObject(self, object, address, itemtype='?'):
        filename = address[0]
        itemname = '/'.join(address[1:])
        if len(filename) < 1:
            filename = ''
        self.filename_label.SetLabel(f" Filename: {filename}")
        if len(itemname) < 2:
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
        if fname in self.data.datasets:
            dlg = wx.MessageDialog(None,
                                   f'File {fname} already exists... overwrite?',
                                   'Question',
                                   wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            ret = dlg.ShowModal()
            if ret == wx.ID_NO:
                return

        opener = FILE_SUFFIXES.get(path.suffix, h5py.File)
        self.add_dataset(fname, opener(path, 'r'))

    def add_dataset(self, name, dataset):
        self.data.add_dataset(name, dataset)
        self.tree.onRefresh()


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
    def __init__(self, with_inspect=False, **kws):
        self.with_inspect = with_inspect
        wx.App.__init__(self, **kws)

    def createApp(self):
        self.frame = SitkaFrame()
        self.frame.Show()
        self.SetTopWindow(self.frame)
        use_darkdetect()
        return True

    def OnInit(self):
        self.createApp()
        if self.with_inspect:
            self.ShowInspectionTool()
        return True

    def add_data(self, name, object):
        self.frame.add_data(name, object)

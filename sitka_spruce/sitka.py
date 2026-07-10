#!/usr/bin/env python
"""
sitka_spruce HDF5 and Zarr data browser
"""
import os

import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv
import wx.lib.mixins.inspection

import hdf5plugin
import h5py
import zarr

from pathlib import Path

from wxutils import (SimpleText, pack,  LEFT,  get_color,
                     use_darkdetect, register_darkdetect,
                     MenuItem,  flatnotebook, GridPanel, Button)
from wxutils.colors import add_named_color


from pyshortcuts import get_cwd

from .gui_utils import  get_font, FONTSIZE
from .data  import get_attributes, SitkaData
from .hdatatree import HDataTree
from .plot1dpanel import ArrayPlot1DPanel
from .plot2dpanel import ArrayImagePanel
from .tablepanel import TablePanel
from .arrayspanel import ArraysPanel

try:
    import larch
except ImportError:
    larch = None

VERSION = '0.1'

FILE_WILDCARD = 'HDF5/Zarr files(*.hdf5;*.h5;*.zarr)|*.hdf5;*.h5;*.zarr|All files (*.*)|*.*'

FILE_OPENERS = {'hdf5': h5py.File, 'h5': h5py.File, 'zarr': zarr.open}

DV_STYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

ICON_FILE = 'sitka.ico'
ICON_DIR = Path(Path(__file__).parent, 'icons').absolute()

add_named_color('sbg', (245, 250, 250, 255), ( 35,  40,  40, 255))

def get_opener(path):
    """get file opener for path name
    currently returns one of h5py.File or zarr.open
    """
    if isinstance(path, str):
        path = Path(path)

    opener = None
    if path.suffix in FILE_OPENERS:
        opener = FILE_OPENERS[path.suffix]
    elif h5py.is_hdf5(path):
        opener = FILE_OPENERS['h5']
    elif (path.exists() and path.is_dir() and   # home-built 'is_zarr'
          (path/'zarr.json').exists() and
          (path/'zarr.json').is_file()):
        opener = FILE_OPENERS['zarr']
    return opener


class SitkaFrame(wx.Frame):
    """Main Window for Sitka HDF5/Zarr viewer"""
    def __init__(self, parent=None, title='Sitka HDF5 Viewer',
                 size=(1100, 650),  style=wx.DEFAULT_FRAME_STYLE):
        """Create Frame instance."""
        self.data = SitkaData()
        self.wids = {}
        wx.Frame.__init__(self, parent, title=title, size=size,
                          style=style)
        self.create_display(size=size)
        self.CreateStatusBar()
        self.status_message('Welcome to Sitka')
        self.BuildMenus()

    def status_message(self, msg):
        self.SetStatusText(msg)
        self.GetStatusBar().Refresh()
        self.Refresh()


    def create_display(self, size=(1100, 650)):
        splitter = wx.SplitterWindow(self, size=size, style=wx.SP_LIVE_UPDATE)

        leftpanel = wx.Panel(splitter)
        # rightpanel = scrolled.ScrolledPanel(splitter)
        # rightpanel = scrolled.ScrolledPanel(splitter)
        rightpanel = wx.Panel(splitter)

        self.tree = HDataTree(leftpanel, on_select=self.onSelectObject)

        self.info = dv.DataViewListCtrl(leftpanel, style=DV_STYLE)
        self.info.AppendTextColumn('Name', width=125)
        self.info.AppendTextColumn('Value', width=175)
        for col in (0, 1):
            this = self.info.Columns[col]
            this.Sortable = False
            this.Alignment = this.Renderer.Alignment = wx.ALIGN_LEFT

        self.tree.SetMinSize((250, 300))
        self.info.SetMinSize((250, 250))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.ALL|wx.GROW)
        sizer.Add(self.info, 0, wx.ALL|wx.GROW)
        pack(leftpanel, sizer)


        mpanel = GridPanel(rightpanel, ncols=4, nrows=10, pad=2, itemstyle=LEFT)

        self.filename_label = SimpleText(mpanel, '', font=get_font(larger=1),
                                         colour='title_red', size=(525, -1),
                                         style=LEFT|wx.ALIGN_CENTER_VERTICAL)
        self.itemname_label = SimpleText(mpanel, '', font=get_font(larger=1),
                                         colour='title_red', size=(525, -1),
                                         style=LEFT|wx.ALIGN_CENTER_VERTICAL)
        self.copybtn = Button(mpanel, 'Copy Address', size=(150, -1),
                              action=self.onCopyAddress)

        self.nb = flatnotebook(mpanel, {},
                               on_change=self.onNBChanged,
                               size=(875, 550))

        # self.mainpanel = ArrayViewPanel(splitter)
        self.nb.AddPage(ArrayImagePanel(self), 'Image Display', True)
        self.nb.AddPage(ArrayPlot1DPanel(self), 'XY Plot Display', True)
        self.nb.AddPage(TablePanel(self), 'Table Display', True)
        self.nb.AddPage(ArraysPanel(self), 'Named Arrays', True)
        self.nb.SetSelection(0)
        self.current_nbpage = self.nb.GetSelection()


        mpanel.Add(self.filename_label, dcol=3)
        mpanel.Add(self.copybtn, dcol=1)
        mpanel.Add(self.itemname_label, dcol=3, newrow=True)
        mpanel.Add(self.nb, dcol=4, drow=5, newrow=True)
        mpanel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(mpanel, 1, wx.ALL|wx.LEFT, 4)
        pack(rightpanel, sizer)

        rightpanel.SetBackgroundColour(get_color('sbg'))
        self.rightpanel = rightpanel
        self.nb.SetBackgroundColour(get_color('sbg'))
        self.nb.SetForegroundColour(get_color('sbg'))
        self.tree.SetBackgroundColour(get_color('sbg'))
        self.tree.SetForegroundColour(get_color('text_fg'))

        self.info.SetFont(get_font())
        self.tree.SetFont(get_font())
        self.set_fontsize(FONTSIZE)

        splitter.SplitVertically(leftpanel, rightpanel, 1)
        splitter.SetMinimumPaneSize(300)
        register_darkdetect(self.onDarkMode)


        # Display the root item.
        self.tree.set_root(self.data.datasets)
        if self.tree.root is not None:
            self.tree.OnSelectionChanged()
        # iconpath = Path(ICON_DIR, ICON_FILE).as_posix()
        # self.SetIcon(wx.Icon(iconpath, wx.BITMAP_TYPE_ICO))

    def onCopyAddress(self, event=None):
        page = self.nb.GetPage(self.current_nbpage)
        msg = 'Could not copy data address to Clipboard'
        if page.access_code is not None and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(page.access_code))
            wx.TheClipboard.Close()
            msg = 'Copied data address to Clipboard'
        self.status_message(msg)


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
        wx.CallAfter(self.tree.onKillFocus)
        event.Skip()


    def onSelectObject(self, object, address, itemtype='?'):
        filename = address[0]
        if len(filename) < 1:
            filename = ''
        itemname = '/'.join(address[1:])
        if len(itemname) < 2:
            itemname = ''

        self.filename_label.SetLabel(f" Filename: {filename}")
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
        bgcol = get_color('sbg', dark=is_dark)
        self.tree.SetBackgroundColour(bgcol)
        self.tree.SetForegroundColour(fgcol)
        self.info.SetBackgroundColour(bgcol)
        self.info.SetForegroundColour(fgcol)
        self.rightpanel.SetBackgroundColour(bgcol)
        wx.CallAfter(self.Refresh)

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
            except Exception:
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

        opener = get_opener(path)
        if opener is not None:
            self.add_dataset(fname, opener(path, mode='r'))

    def add_dataset(self, name, dataset=None):
        """add dataset to Sitka.

        Arguments
        ----------
        name     (str)    name for dataset, typically filename
        dataset  (dataset or None) dataset to add

        Notes
        ------
        If dataset is None, the name will be interpreted as a file to be opened,
        using its suffix or file type to guess how to open the file

        """
        if dataset is None:
            path = Path(name)
            opener = get_opener(path)
            if opener is not None:
                dataset = opener(path, mode='r')
        if dataset is not None:
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
            except Exception:
                pass
            self.Destroy()
        else:
            try:
                event.Veto()
            except Exception:
                pass

class Sitka_App(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    "simple app to wrap HDF5_Frame"
    def __init__(self, with_inspect=False, **kws):
        self.with_inspect = with_inspect
        wx.App.__init__(self, **kws)

    def createApp(self):
        self.frame = SitkaFrame()
        use_darkdetect()
        self.frame.Show()

        self.SetTopWindow(self.frame)

        iconpath = Path(ICON_DIR, ICON_FILE).as_posix()
        self.frame.SetIcon(wx.Icon(iconpath, wx.BITMAP_TYPE_ICO))
        return True

    def OnInit(self):
        self.createApp()
        if self.with_inspect:
            self.ShowInspectionTool()
        return True

    def add_dataset(self, name, dataset=None):
        self.frame.add_dataset(name, dataset=dataset)

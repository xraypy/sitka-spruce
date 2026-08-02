#!/usr/bin/env python
"""
sitka_spruce HDF5 and Zarr data browser
"""
import wx
import wx.dataview as dv
import wx.lib.mixins.inspection
from wx.adv import AboutBox, AboutDialogInfo

from pathlib import Path

from wxutils import (SimpleText, pack,  LEFT,  get_color,
                     use_darkdetect, register_darkdetect,
                     MenuItem,  flatnotebook, GridPanel, Button,
                     FileOpen, FileSave, SelectWorkdir, Popup)


from pyshortcuts import get_cwd, fix_filename
from .version import version
from .gui_utils import  get_font, FONTSIZE
from .data  import (get_attributes, SitkaData, get_opener, get_sitka_files,
                    EPICS_NDATTR)
from .hdatatree import HDataTree
from .plot1dpanel import ArrayPlot1DPanel
from .plot2dpanel import ArrayImagePanel
from .tablepanel import TablePanel
from .arrayspanel import ArraysPanel
from .ndattrpanel import NDAttrsPanel
try:
    import larch
except ImportError:
    larch = None

FILE_WILDCARD = 'HDF5/Zarr files(*.hdf5;*.h5;*.zarr)|*.hdf5;*.h5;*.zarr|All files (*.*)|*.*'


DV_STYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

ICON_FILE = 'sitka.ico'
ICON_DIR = Path(Path(__file__).parent, 'icons').absolute()

NDATTR_TITLE = 'Epics NDAttributes'

class FileDropTarget(wx.FileDropTarget):
    def __init__(self, window, callback):
        wx.FileDropTarget.__init__(self)
        self.window = window
        self.callback = callback

    def OnDropFiles(self, x, y, filenames):
        self.callback(filenames)
        return True


class SitkaFrame(wx.Frame):
    """Main Window for Sitka HDF5/Zarr viewer"""
    def __init__(self, parent=None, with_inspect=False,
                 title='Sitka Hierarchical Data Viewer for HDF5 and Zarr',
                 size=(1000, 675),  style=wx.DEFAULT_FRAME_STYLE):
        """Create Frame instance."""
        self.data = SitkaData()
        self.wids = {}
        self.filename = None
        self.with_inspect = with_inspect
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


    def create_display(self, size=(1050, 650)):
        splitter = wx.SplitterWindow(self, size=size, style=wx.SP_LIVE_UPDATE)

        leftpanel = wx.Panel(splitter)
        rightpanel = wx.Panel(splitter)

        self.tree = HDataTree(leftpanel, on_select=self.onSelectObject)

        self.info = dv.DataViewListCtrl(leftpanel, style=DV_STYLE)
        self.info.AppendTextColumn('Name', width=125)
        self.info.AppendTextColumn('Value', width=175)
        for col in (0, 1):
            this = self.info.Columns[col]
            this.Sortable = False
            this.Alignment = this.Renderer.Alignment = wx.ALIGN_LEFT

        self.tree.SetMinSize((275, 300))
        self.info.SetMinSize((275, 250))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.ALL|wx.GROW)
        sizer.Add(self.info, 0, wx.ALL|wx.GROW)
        pack(leftpanel, sizer)


        tpanel = self.tpanel = GridPanel(rightpanel, ncols=4, nrows=10, pad=2, itemstyle=LEFT)

        self.filename_label = SimpleText(tpanel, '', font=get_font(larger=1),
                                         colour='title_red', size=(675, -1),
                                         style=LEFT|wx.ALIGN_CENTER_VERTICAL)
        self.itemname_label = SimpleText(tpanel, '', font=get_font(larger=1),
                                         colour='title_red', size=(675, -1),
                                         style=LEFT|wx.ALIGN_CENTER_VERTICAL)
        self.copybtn = Button(tpanel, 'Copy Address', size=(200, -1),
                              action=self.onCopyAddress)
        self.importbtn = Button(tpanel, 'Import Named Arrays', size=(200, -1),
                                     action=self.onImportNamedArrays)

        self.nb = flatnotebook(tpanel, {},
                               on_change=self.onNBChanged,
                               size=(700, 625))

        # self.mainpanel = ArrayViewPanel(splitter)
        self.nb.AddPage(ArrayImagePanel(self), 'Image Display', True)
        self.nb.AddPage(ArrayPlot1DPanel(self), 'XY Plot Display', True)
        self.nb.AddPage(TablePanel(self), 'Table Display', True)
        self.nb.AddPage(ArraysPanel(self), 'Named Arrays', True)
        self.nb.SetSelection(0)
        self.current_nbpage = self.nb.GetSelection()
        self.nb_pages = {}

        for i in range(self.nb.GetPageCount()):
            title = self.nb.GetPageText(i)
            page = self.nb.GetPage(i)
            page.SetBackgroundColour(get_color('sbg'))
            self.nb_pages[title] = (i, page)


        tpanel.Add(self.filename_label, dcol=4)
        tpanel.Add(self.itemname_label, dcol=4, newrow=True)
        tpanel.Add(self.copybtn,   dcol=2, newrow=True)
        tpanel.Add(self.importbtn, dcol=2, newrow=False)
        tpanel.Add(self.nb, dcol=4, drow=5, newrow=True)
        tpanel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(tpanel, 1, wx.ALL|wx.LEFT, 4)
        pack(rightpanel, sizer)

        # print("Sitka: SBG ", get_color('sbg'))

        rightpanel.SetBackgroundColour(get_color('sbg'))
        self.rightpanel = rightpanel

        self.info.SetFont(get_font())
        self.tree.SetFont(get_font())
        self.set_fontsize(FONTSIZE)

        self.tree.SetDropTarget(FileDropTarget(self,
                                               self.onDroppedFiles))

        splitter.SplitVertically(leftpanel, rightpanel, 1)
        splitter.SetMinimumPaneSize(300)
        register_darkdetect(self.onDarkMode)
        self.onDarkMode()


        # Display the root item.
        self.tree.set_root(self.data.datasets)
        if self.tree.root is not None:
            self.tree.OnSelectionChanged()
        # iconpath = Path(ICON_DIR, ICON_FILE).as_posix()
        # self.SetIcon(wx.Icon(iconpath, wx.BITMAP_TYPE_ICO))

    def onCopyAddress(self, event=None):
        msg = 'Could not copy data address to Clipboard'
        if self.access_code is not None and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.access_code))
            wx.TheClipboard.Close()
            msg = 'Copied data address to Clipboard'
        self.status_message(msg)

    def onImportNamedArrays(self, event=None):
        obj = self.tree.GetItemData(self.tree.item)
        addr = self.tree.get_address(self.tree.item)
        fname = addr.pop(0)
        addr = '/'.join(addr)
        for key, val in obj.items():
            self.data.add_array(key, val[()], address=f'{fname}:{addr}/{key}')
        ipage, page = self.get_page('ArraysPanel')
        if page is not None:
            page.set_object()
            self.nb.SetSelection(ipage)


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

    def add_ndattrs_panel(self):
        self.nb.AddPage(NDAttrsPanel(self), NDATTR_TITLE, True)
        self.nb_pages = {}
        ix = 0
        for i in range(self.nb.GetPageCount()):
            title = self.nb.GetPageText(i)
            if title == NDATTR_TITLE:
                ix = i
            page = self.nb.GetPage(i)

            self.nb_pages[title] = (i, page)
        self.nb.SetSelection(ix)

    def onSelectObject(self, object, address, itemtype='?'):
        filename = address[0]
        if len(filename) < 1:
            filename = ''
        itemname = '/'.join(address[1:])
        if len(itemname) < 2:
            itemname = ''
        self.filename = filename
        self.filename_label.SetLabel(f" Filename: {filename}")
        self.itemname_label.SetLabel(f" Address: {itemname}")
        self.importbtn.Enable(itemname=='sitka_arrays')

        if EPICS_NDATTR in itemname:
            if NDATTR_TITLE not in self.nb_pages:
                self.add_ndattrs_panel()
            ipage, page = self.nb_pages.get(NDATTR_TITLE, (0, None))
            self.nb.SetSelection(ipage)
        else:
            ipage, page = self.nb_pages.get('Image  Display', (0, None))
            try:
                if len(object.shape) == 1:
                    ipage, page = self.nb_pages.get('XY Plot Display', (1, None))
            except Exception:
                pass
            self.nb.SetSelection(ipage)

        self.fill_info(filename, itemtype, itemname, object)

        for ipage in range(self.nb.GetPageCount()):
            page = self.nb.GetPage(ipage)
            page.set_object(object, itemtype=itemtype,
                            filename=filename, itemname=itemname)

    def fill_info(self, name, itemtype, itemname, object):
        self.file_info = (name, itemname, itemtype)
        self.access_code = f"['{name}']['{itemname}']"

        self.info.DeleteAllItems()
        if name == 'Data':
            self.info.AppendItem(('filename', 'toplevel'))
        else:
             name = Path(name).name
             self.info.AppendItem(('filename', name))
             self.info.AppendItem(('datatype', itemtype))
             attrs = get_attributes(object, itemname)
             for key, val in attrs.items():
                 self.info.AppendItem((key, val))
        self.info.Refresh()

    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('sbg', dark=is_dark)
        for w in (self.tree, self.info, self.rightpanel,
                  self.nb, self.tpanel):
            w.SetBackgroundColour(bgcol)
            w.SetForegroundColour(fgcol)

        self.info.SetAlternateRowColour(bgcol)
        self.info.SetOwnBackgroundColour(bgcol)
        self.nb.SetTabAreaColour(bgcol)
        wx.CallAfter(self.Refresh)

    def Raise(self):
        self.SetStatusText("Ready", 0)
        self.Refresh()
        wx.Frame.Raise(self)

    def BuildMenus(self):
        menubar = wx.MenuBar()
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "Read Data File\tCtrl+O",
                 "Read Data File", self.onReadData)
        MenuItem(self, fmenu, "Close Current Data File",
                 "Close Data File", self.onCloseData)
        MenuItem(self, fmenu, "Read Files from Folder\tCtrl+F",
                 "Read all Files from Selected Folder",
                 self.onReadFolder)

        fmenu.AppendSeparator()
        self.Bind(wx.EVT_CLOSE,  self.onExit)
        MenuItem(self, fmenu, 'E&xit', 'Exit', self.onExit)
        menubar.Append(fmenu, '&File')

        omenu = wx.Menu()
        MenuItem(self, omenu,  "Increase Font Size", "", self.onIncreaseFont)
        MenuItem(self, omenu,  "Decrease Font Size", "", self.onDecreaseFont)

        omenu.AppendSeparator()
        MenuItem(self, omenu, 'Copy Address to Clipboard\tCtrl+C',
                 'Copy Current Address to to Clipboard', self.onCopyAddress)
        MenuItem(self, omenu, "Export Attributes to TSV File\tCtrl+E",
                 "Export Info and Attributes to tab-separated File",
                 self.onExportInfo)

        if self.with_inspect:
            omenu.AppendSeparator()
            MenuItem(self, omenu, 'Show wxPython Inspector\tCtrl+I',
                     'Debug wxPython App', self.onWxInspect)


        menubar.Append(omenu, 'Options')

        hmenu = wx.Menu()
        MenuItem(self, hmenu, 'About Sitka Spruce', 'About Sitka Spruce',
                 self.onAbout)
        menubar.Append(hmenu, '&Help')

        self.SetMenuBar(menubar)

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
        self.info.Refresh()
        set_fsize(self.nb,  fsize)
        for ipage in range(self.nb.GetPageCount()):
            page = self.nb.GetPage(ipage)
            set_fsize(page,  fsize)
        self.nb.Refresh()


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


    def onCloseData(self, event=None):
        if self.filename in self.data.datasets:
            ret = Popup(self, f'Remove {self.filename} from Sitka?', '',
                       style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
            if ret == wx.ID_YES:
                self.data.datasets[self.filename].close()
                self.data.datasets.pop(self.filename)
                self.tree.onRefresh()

    def onDroppedFiles(self, filenames):
        invalid = []
        for filename in filenames:
            path = Path(filename)
            fname = path.name
            opener = get_opener(path)
            if opener is not None:
                self.add_dataset(fname, opener(path, mode='r'))
            else:
                invalid.append(filename)
        if len(invalid) > 0:
            msg = '\n'.join(invalid)
            Popup(self, 'Could not read some files in Sitka', msg)


    def onReadData(self, event=None):
        path = FileOpen(self, 'Open Data File', default_dir=get_cwd(),
                        wildcard=FILE_WILDCARD)
        if path is None:
            return

        fname = Path(path).name
        if fname in self.data.datasets:
            ret = Popup(self,
                       f'File {fname} already exists... overwrite?',
                       f'Overwrite {fname}',
                       style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
            if ret == wx.ID_NO:
                return

        opener = get_opener(path)
        if opener is not None:
            self.add_dataset(fname, opener(path, mode='r'))

    def onReadFolder(self, event=None):
        dlg = wx.DirDialog(self, 'Select Folder',
                       style=wx.DD_DEFAULT_STYLE|wx.DD_CHANGE_DIR)

        if  dlg.ShowModal() != wx.ID_OK:
            return

        folder = Path(dlg.GetPath()).absolute().as_posix()
        dlg.Destroy()
        for fname, dset in get_sitka_files(folder).items():
            self.add_dataset(fname, dataset=dset)

    def add_dataset(self, name, dataset=None):
        """add dataset (HDF5/Zarr Group or Dataset) to Sitka.

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

    def add_array(self, name, data, address=None):
        """add single nd-data array to Sitka.

        Arguments
        ----------
        name    (str)     name for array (must be valid Python variable name)
        data    (ndarray) data to add
        address (str or None) address to use for named array
        """
        self.data.add_array(name, data, address=address)
        self.tree.onRefresh()
        ipage, page = self.get_page('ArraysPanel')
        if page is not None:
            page.set_object()
            self.nb.SetSelection(ipage)

    def get_page(self, name):
        for ipage in range(self.nb.GetPageCount()):
            page = self.nb.GetPage(ipage)
            pname = page.__class__.__name__
            if name in pname:
                return ipage, page
                break
        return 0, None



    def onChangeDir(self, event=None):
        SelectWorkdir(self)

    def onExportInfo(self, event=None):
        (filename, itemname, itemtype) =  self.file_info
        oname = fix_filename(f'{filename}_{itemname}_info.tsv')

        path = FileSave(self, 'Save Attribute Table to Tab-separated File',
                        default_dir=get_cwd(),
                        default_file=oname)

        if path is None:
            return

        out = ['Name\t Value', '----\t-------']
        for row in range(self.info.GetItemCount()):
            out.append(f'{self.info.GetValue(row, 0)}\t{self.info.GetValue(row, 1)}')

        out.append('')
        with open(path, 'w') as fh:
            fh.write('\n'.join(out))
        self.status_message(f'Wrote attributes to {path}')

    def onAbout(self, event=None):
        info = AboutDialogInfo()
        info.SetName(' Sitka Spruce')
        info.SetDescription(' Hierarchical Data Viewer for HDF5 and Zarr')
        info.SetVersion(version)
        info.AddDeveloper('Matthew Newville: newville@cars.uchicago.edu')
        AboutBox(info)



    def onExit(self, event=None):
        ret = Popup(self,
                    'Really Quit?', '',
                    style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
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
        self.frame = SitkaFrame(with_inspect=self.with_inspect)
        use_darkdetect()
        self.frame.Show()

        self.SetTopWindow(self.frame)

        iconpath = Path(ICON_DIR, ICON_FILE).as_posix()
        self.frame.SetIcon(wx.Icon(iconpath, wx.BITMAP_TYPE_ICO))
        return True

    def OnInit(self):
        self.createApp()
        return True

    def add_dataset(self, name, dataset=None):
        self.frame.add_dataset(name, dataset=dataset)

    def add_array(self, name, array, address=None):
        self.frame.add_dataset(name, array, address=address)

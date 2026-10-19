"""
sitka_spruce HDF5 and Zarr data browser
"""
import os
import wx
import wx.dataview as dv
import wx.lib.mixins.inspection
from wx.adv import AboutBox, AboutDialogInfo
from contextlib import suppress
from time import time
from pathlib import Path

from wxutils import (SimpleText, pack,  LEFT,  get_color,
                     use_darkdetect, register_darkdetect,
                     MenuItem,  flatnotebook, GridPanel, Button,
                     FileOpen, FileSave, SelectWorkdir, Popup)


    
from pyshortcuts import get_cwd, fix_filename, uname
from .version import version
from .logger import get_logger
from .gui_utils import  get_font, FONTSIZE
from .data  import (get_attributes, SitkaData, get_opener, get_sitka_files,
                    EPICS_NDATTR)
from .hdatatree import HDataTree
from .plot1dpanel import ArrayPlot1DPanel
from .plot2dpanel import ArrayImagePanel
from .tablepanel import TablePanel
from .arrayspanel import ArraysPanel
from .ndattrpanel import NDAttrsPanel

SetAppDisplayName = SetDockIcon = None
with suppress(ImportError):
    from wxutils import SetAppDisplayName, SetDockIcon

get_ipython = None
with suppress(ImportError):
    from IPython import get_ipython



FILE_WILDCARD = 'HDF5/Zarr files(*.hdf5;*.h5;*.zarr)|*.hdf5;*.h5;*.zarr|All files (*.*)|*.*'


DV_STYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

ICON_FILE = 'sitka.ico'
ICON_FILE_MAC = 'sitka.icns'
ICON_DIR = Path(Path(__file__).parent, 'icons').absolute()

NDATTR_TITLE = 'Epics NDAttributes'


APPNAME_CODE = """ # used to find name of SitkaFrame instance
from sitka_spruce import SitkaFrame
saname = '<none>'
_globs = {key: val  for key, val in globals().items()}
for key, val in _globs.items():
    if isinstance(val, SitkaFrame):
       aname = key
print(aname)
"""

IMSHOW_CODE = """
import hdf5plugin, h5py
import numpy as np
import matplotlib.pyplot as plt
h5file = h5py.File('{filename}', mode='r')
# from Jupyter session
# hfile = {dset}['{filename}']
img = h5file{access}
img_title = "'{filename}'{access}"
clevel = 0.1 # percent contrast level
ilo, ihi = np.percentile(img, [clevel, 100.0-clevel])
plt.imshow(np.clip(img, ilo, ihi))
plt.gca().set_title(img_title)
plt.show()
"""

PLOT1D_CODE = """
import hdf5plugin, h5py
import numpy as np
import matplotlib.pyplot as plt
h5file = h5py.File('{filename}', mode='r')
# from Jupyter session
# hfile = {dset}['{filename}']
ydat = h5file{access}
xdat = np.arange(len(ydat))
plt.plot(xdat, ydat)
plt.title('''{title}''')
plt.show()
"""

class FileDropTarget(wx.FileDropTarget):
    def __init__(self, window, callback):
        wx.FileDropTarget.__init__(self)
        self.window = window
        self.callback = callback

    def OnDropFiles(self, x, y, filenames):
        self.callback(filenames)
        return True


class IPyConnector:
    """
    not-exactly working as well as hoped, but a partial interface to
    working with the IPython notebook that launched Sitka
    """
    def __init__(self, logger):
        self.ipy  = None if get_ipython is None else get_ipython()
        self.logger  = logger
        self.appname = None
        self.ipayload = {"source": "set_next_input", "text": "",
                         "replace": False}

    def get_appname(self):
        'get name in IPython kernel of Sitka Frame'
        if self.ipy is not None:
            self.ipy.run_cell_magic('capture', 'output', APPNAME_CODE)
            capio = self.ipy.user_ns['output']
            appname = capio.stdout.split('\n')[0]
            if appname not in ('<none>', None, 'None'):
                self.appname = appname

    def runcode(self, content):
        'WIP, not yet working'
        if self.ipy is None:
            return
        self.ipayload["text"] = content
        self.ipy.payload_manager.write_payload(self.ipayload)
        self.ipy.set_next_input(content)
        self.logger.debug(f'ipy:runcode:  {content}')
        out = self.ipy.run_cell(content)
        self.logger.debug(f'ipy:success {out.success}')
        self.logger.debug(f'ipy:result {out.result}')
        self.logger.debug(f'ipy:info {out.info}')


class SitkaFrame(wx.Frame):
    """Main Window for Sitka HDF5/Zarr viewer"""
    def __init__(self, parent=None, with_inspect=False,
                 title='Sitka Hierarchical Data Viewer for HDF5 and Zarr',
                 size=(1000, 675),  style=wx.DEFAULT_FRAME_STYLE):
        """Create Frame instance."""
        self.logger = get_logger()
        self.data = SitkaData(logger=self.logger)
        self.config = {'ipython_plot': False}
        self.ipyconn = None
        if get_ipython is not None:
            self.ipyconn = IPyConnector(self.logger)
            
        self.workdir = None
        self.filename = None
        self.with_inspect = with_inspect
        self.access_code = None
        self.python_code = None
        
        self.wids = {}
        wx.Frame.__init__(self, parent, title=title, size=size,
                          style=style)

        self.SetTitle('Sitka')
        self.CreateStatusBar()
        self.create_display(size=size)
        self.BuildMenus()
        self.status_message('Welcome to Sitka')
        self.watch_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onWatchTimer, self.watch_timer)

        
    def status_message(self, msg):
        self.SetStatusText(msg)
        sbar = self.GetStatusBar()
        sbar.SetForegroundColour(get_color('text'))
        sbar.SetBackgroundColour(get_color('sbg'))
        sbar.Refresh()
        # self.Refresh()


    def create_display(self, size=(1050, 650)):
        splitter = wx.SplitterWindow(self, size=size, style=wx.SP_LIVE_UPDATE)

        leftpanel = wx.Panel(splitter)
        rightpanel = wx.Panel(splitter)

        self.tree = HDataTree(leftpanel, on_select=self.onSelectObject,
                              logger=self.logger)

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
        self.copy_addr_btn = Button(tpanel, 'Copy Address', size=(200, -1),
                              action=self.onCopyAddress)
        self.copy_py_btn = Button(tpanel, 'Copy Python Code', size=(200, -1),
                              action=self.onCopyPyCode)
        self.importbtn = Button(tpanel, 'Import Named Arrays', size=(200, -1),
                                     action=self.onImportNamedArrays)

        self.nb = flatnotebook(tpanel, {},
                               on_change=self.onNBChanged,
                               size=(700, 625))

        panels = {'Image Display': ArrayImagePanel,
                  'XY Plot Display': ArrayPlot1DPanel,
                  'Table Display': TablePanel,
                  'Named Arrays': ArraysPanel,
                  }
        for title, _class in panels.items():
            self.nb.AddPage(_class(self, logger=self.logger), title, True)
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
        tpanel.Add(self.copy_addr_btn, dcol=2, newrow=True)
        tpanel.Add(self.copy_py_btn, dcol=1, newrow=False)
        tpanel.Add(self.importbtn,  dcol=2, newrow=False)
        tpanel.Add(self.nb, dcol=4, drow=5, newrow=True)
        tpanel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(tpanel, 1, wx.ALL|wx.LEFT, 4)
        pack(rightpanel, sizer)

        rightpanel.SetBackgroundColour(get_color('sbg'))
        self.rightpanel = rightpanel
        isize = 1 if uname.startswith('win')else 0
        self.set_fontsize(FONTSIZE)
        self.info.SetFont(get_font(smaller=isize))
        self.tree.SetFont(get_font())

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


    def onCopyAddress(self, event=None):
        msg = 'Could not copy data address to Clipboard'
        if self.access_code is not None and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.access_code))
            wx.TheClipboard.Close()
            msg = 'Copied data address to Clipboard'
        self.logger.info(msg)
        self.status_message(msg)

    def onCopyPyCode(self, event=None):
        msg = 'Could not copy python code to Clipboard'
        if self.python_code is not None and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.python_code))
            wx.TheClipboard.Close()
            msg = 'Copied Python code to Clipboard'
        self.logger.info(msg)
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
        self.copy_py_btn.Enable(self.python_code is not None)
        self.copy_addr_btn.Enable(self.access_code is not None)

        if EPICS_NDATTR in itemname:
            if NDATTR_TITLE not in self.nb_pages:
                self.add_ndattrs_panel()
            ipage, page = self.nb_pages.get(NDATTR_TITLE, (0, None))
            self.nb.SetSelection(ipage)
        else:
            nshape = len(getattr(object, 'shape', []))
            if nshape == 1:
                ipage, page = self.nb_pages.get('XY Plot Display', (1, None))
            else:
                ipage, page = self.nb_pages.get('Image  Display', (0, None))
            self.nb.SetSelection(ipage)

        self.fill_info(filename, itemtype, itemname, object)

        for ipage in range(self.nb.GetPageCount()):
            page = self.nb.GetPage(ipage)
            page.set_object(object, itemtype=itemtype,
                            filename=filename, itemname=itemname)

    def set_pycode(self, command, filename=None, itemname=None,
                   dlabel=None, **kws):
        self.python_code = None
        if filename is None or itemname is None:
            return
        appname = 'sitkaviewer'
        if self.ipyconn is not None:
            if self.ipyconn.appname is None:
                self.ipyconn.get_appname()
            if self.ipyconn.appname is not None:
                appname = self.ipyconn.appname
        if command == 'imshow':
            dset = f'{appname}.data.datasets'
            access = f"['{itemname}']{dlabel}"
            self.python_code = IMSHOW_CODE.format(dset=dset,
                                                  filename=filename,
                                                  access=access)
            self.copy_py_btn.Enable()
        elif command == 'plot1d':
            dset = f'{appname}.data.datasets'
            access = f"['{itemname}']{dlabel}"
            title = kws.get('title', access)
            self.python_code = PLOT1D_CODE.format(dset=dset,
                                                  filename=filename,
                                                  access=access,
                                                  title=title)
            self.copy_py_btn.Enable()

    def fill_info(self, name, itemtype, itemname, object):
        self.file_info = (name, itemname, itemtype)
        self.access_code = f"['{name}']['{itemname}']"
        self.copy_addr_btn.Enable()

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
        self.watch_menu =  MenuItem(self, fmenu, "Watch Working Folder",
                                    "Automatically Import Folders from Working Folder",
                                    self.onWatchFolder, kind=wx.ITEM_CHECK,
                                    checked=False)
        self.watch_menu.Enable(False)

        fmenu.AppendSeparator()
        self.Bind(wx.EVT_CLOSE,  self.onExit)
        MenuItem(self, fmenu, 'E&xit', 'Exit', self.onExit)
        menubar.Append(fmenu, '&File')

        omenu = wx.Menu()
        if get_ipython is not None:
            ipy = None
            with suppress(Exception):
                ipy = get_ipython()
            if ipy is not None:
                MenuItem(self, omenu,  "Show Plots/Images in IPython Notebook", "",
                         self.onUseIPythonPlot,  kind=wx.ITEM_CHECK,
                         checked=False)
                omenu.AppendSeparator()
                
        MenuItem(self, omenu,  "Increase Font Size", "", self.onIncreaseFont)
        MenuItem(self, omenu,  "Decrease Font Size", "", self.onDecreaseFont)

        omenu.AppendSeparator()
        MenuItem(self, omenu, 'Copy Address to Clipboard\tCtrl+C',
                 'Copy Current Address to to Clipboard', self.onCopyAddress)
        MenuItem(self, omenu, 'Copy Python Plotting Code to Clipboard',
                 'Copy Plotting Code to to Clipboard', self.onCopyPyCode)
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

    def onUseIPythonPlot(self, event=None):
        self.config['ipython_plot'] = not self.config['ipython_plot']

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
        if len(folder) > 0:
            self.ReadFolder(self, folder)

    def ReadFolder(self, folder):
        self.workdir = folder
        self.watch_menu.Enable()
        for fname, dset in get_sitka_files(folder, logger=self.logger).items():
            self.add_dataset(fname, dataset=dset)

    def onWatchFolder(self, event=None):
        checked = event.IsChecked()
        if not checked:
            self.watch_time.Stop()
        elif self.workdir is not None:
            self.watch_timer.Start(5000)

    def onWatchTimer(self, event=None):
        path = Path(self.workdir)
        if path.exists() and path.is_dir():
            for fname in os.listdir(path):
                if fname in self.data.datasets:
                    continue
                thispath = Path(path, fname)
                opener = get_opener(thispath)
                if opener is None:
                    continue
                
                mtime = os.stat(thispath).st_mtime
                if (time() >  mtime + 15):
                    self.add_dataset(fname,
                                     dataset=opener(thispath.absolute(), mode='r'))

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
        (filename, itemname, _) =  self.file_info
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
            self.watch_timer.Stop()
            try:
                for a in self.GetChildren():
                    a.Destroy()
            except Exception as exc:
                self.logger.debug(f'exit exception destroying children {exc}')

            self.Destroy()

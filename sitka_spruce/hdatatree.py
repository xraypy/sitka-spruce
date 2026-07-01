import wx
import numpy as np

from wxutils import get_color, register_darkdetect

from .data  import get_items, get_itemtype

COMMONTYPES = (int, float, complex, str, bytes, bool, list, tuple, np.ndarray)

TREESTYLE = wx.TR_DEFAULT_STYLE|wx.TR_HIDE_ROOT

class HDataTree(wx.TreeCtrl):
    """TreeCtrl for hierarchical data structures and files such as HDF5/Zarr"""
    def __init__(self, parent, size=(350, 250), style=TREESTYLE, on_select=None):
        """Create FillingTree instance."""
        wx.TreeCtrl.__init__(self, parent, size=size, style=style)
        self.item = None
        self.on_select = None
        self.root = None
        if callable(on_select):
            self.on_select = on_select
        register_darkdetect(self.onDarkMode)

    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('text_bg', dark=is_dark)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        self.SetBackgroundColour(bgcol)
        self.SetForegroundColour(fgcol)
        wx.CallAfter(self.Refresh)

    def set_root(self, data=None, label='Data Sets'):
        if data is None:
            data = {}
        self.item = self.root = self.AddRoot(label, -1, -1,  data)
        self.SetItemHasChildren(self.root,  self.objHasChildren(data))
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelectionChanged, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnItemExpanding, id=self.GetId())
        self.onRefresh()

    def onRefresh(self, evt=None):
        """ refesh data tree, preserving current selection"""
        root = self.GetRootItem()
        this = self.GetFocusedItem()
        parents = [self.GetItemText(this)]
        while True:
            try:
                this = self.GetItemParent(this)
                if this == root:
                    break
                parents.append(self.GetItemText(this))
            except:
                break

        self.addChildren(root)
        node = root
        while len(parents) > 0:
            name = parents.pop()
            node = self.get_node_by_name(node, name)
            if node is not None:
                self.Expand(node)

        try:
            self.Expand(node)
            self.SelectItem(node)
        except:
            pass

    def get_node_by_name(self, node, name):
        if node is None:
            node = self.GetRootItem()
        item, cookie = self.GetFirstChild(node)
        if item.IsOk() and self.GetItemText(item) == name:
            return item

        nodecount = self.GetChildrenCount(node)
        while nodecount > 1:
            nodecount -= 1
            item, cookie = self.GetNextChild(node, cookie)
            if not item.IsOk() or self.GetItemText(item) == name:
                return item


    def OnItemExpanding(self, event=None):
        """Add children to the item."""
        try:
            item = event.GetItem()
        except Exception:
            item = self.item
        if self.IsExpanded(item):
            return
        self.addChildren(item)
        self.SelectItem(item)

    def OnSelectionChanged(self, event=None):
        """Display information about the item."""
        if hasattr(event, 'GetItem'):
            self.item = event.GetItem()
        if self.item:
            obj = self.GetItemData(self.item)
            if wx.Platform == '__WXMSW__' and obj is None:
                return

            if self.IsExpanded(self.item):
                self.addChildren(self.item)
                self.SetItemHasChildren(self.item, self.objHasChildren(obj))

            if self.on_select is not None:
                self.on_select(obj, address=self.get_address(self.item),
                               itemtype=get_itemtype(obj))


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

    def get_address(self, item, delim='/'):
        """Return list for a full tree selection"""
        try:
            name = self.GetItemText(item)
        except Exception:
            return ['']

        addr = [name]
        while item != self.root:
            item = self.GetItemParent(item)
            if item.IsOk() and item != self.root:
                addr.append(self.GetItemText(item))
        addr.reverse()
        return addr

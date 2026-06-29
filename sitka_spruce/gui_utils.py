import wx
from pyshortcuts import uname
FONTSIZE = 12
FONTSIZE_FW = 13

def fontsize(fixed_width=False):
    """return best default fontsize"""
    font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
    font.SetPointSize(FONTSIZE_FW if fixed_width else FONTSIZE)
    if uname not in ('win', 'darwin'):
        font = font.Smaller()
    elif fixed_width:
        font = font.Larger()
    return int(font.GetFractionalPointSize())

def Font(size, serif=False, bold=False, fixed_width=False):
    """define a font by size and serif/ non-serif
    f = Font(10, serif=True)
    """
    family = wx.DEFAULT
    if not serif:
        family = wx.SWISS
    if fixed_width:
        family = wx.MODERN
    style = wx.BOLD if bold else wx.NORMAL
    return wx.Font(size, family, wx.NORMAL, style, 0, "")

def get_font(larger=0, smaller=0, serif=False, bold=False, fixed_width=False):
    "return a font"
    fnt = Font(fontsize(fixed_width=fixed_width),
               serif=serif, bold=bold, fixed_width=fixed_width)
    for i in range(larger):
        fnt = fnt.Larger()
    for i in range(smaller):
        fnt = fnt.Smaller()
    return fnt

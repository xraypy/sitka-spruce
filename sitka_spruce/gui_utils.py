import inspect
from functools import partial

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

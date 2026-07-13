import sys
from argparse import ArgumentParser
from pathlib import Path
from pyshortcuts import uname, make_shortcut, ico_ext

from wxmplot.interactive import get_wxapp

from .data import get_sitka_files
from .sitka import Sitka_App, SitkaFrame

def sitka_viewer(folder=None):
    """Sitka Vewer for HDF5/Zarr files that that can be run
    interactively from within an Python/Jupyer repl

    Arguments
    ---------
    folder (str or None) folder name to read HDF5/Zarr files from

    Returns
    -------
    SitkaFrame a wx.Frame for the viewer.

    This has a '.data' member that holds the datasets and working
    arrays used by sitka.
    """
    get_wxapp()
    sview = SitkaFrame()
    if folder is not None:
        for fname, dset in get_sitka_files(folder).items():
            sview.add_dataset(fname, dataset=dset)
    sview.Show()
    sview.Raise()
    return sview

def sitka_cli():
    """
    sitka command-line app
    """

    parser = ArgumentParser(description='Sitka Data Viewer')
    parser.add_argument('-d', '--dir', dest='directory',
                       default=None, help="directory to find data files")
    parser.add_argument('-m', '--makeicon', action='store_true', default=False,
                            help="make desktop shortcut")
    parser.add_argument('-i', '--inspect', action='store_true', default=False,
                            help="enable wxInspect")
    args = parser.parse_args()

    if args.makeicon:
        bindir = 'Scripts' if uname == 'win' else 'bin'
        bindir = Path(sys.prefix, bindir).absolute()
        script = 'sitka'
        script = Path(bindir, script).absolute().as_posix()

        for ext in ico_ext:
            icondir = Path(Path(__file__).parent, 'icons').absolute()
            print(f" app icon : {icondir=}")
            ticon = Path(icondir, f"sitka.{ext:s}").absolute()
            if ticon.exists():
                icon = ticon
        make_shortcut(script, name='Sitka', folder=None,
                      icon=icon.as_posix(),
                      description='Sitka Data Viewer',
                      terminal=False)
        return

    app = Sitka_App(with_inspect=args.inspect)
    if args.directory is not None:
        files = get_sitka_files(args.directory)
        if len(files) > 0:
            for fname, dset in files.items():
                app.add_dataset(fname, dataset=dset)
    app.MainLoop()

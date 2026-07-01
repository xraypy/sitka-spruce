import sys
from argparse import ArgumentParser
from pathlib import Path
from pyshortcuts import uname, make_shortcut, ico_ext, get_folders
from glob import glob

from .sitka import Sitka_App, FILE_SUFFIXES

def sitka_cli():
    parser = ArgumentParser(description='Sitka Data Viewer')
    parser.add_argument('-d', '--dir', dest='directory',
                       default=None, help="directory to find data files")
    parser.add_argument('-m', '--makeicon', action='store_true', default=False,
                            help="make desktop shortcut")
    args = parser.parse_args()

    if args.makeicon:
        bindir = 'Scripts' if uname == 'win' else 'bin'
        bindir = Path(sys.prefix, bindir).absolute()
        script = f'sitka'
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

    files = {}
    if args.directory is not None:
        pth = Path(args.directory)
        if pth.exists:
            pname = pth.as_posix()
            filelist = []
            for ext, opener in FILE_SUFFIXES.items():
                filelist.append((opener, sorted(glob(f'{pname}/*.{ext}'))))

            for opener, flist in filelist:
                for fname in flist:
                    sname = Path(fname).name
                    try:
                        files[sname] = opener(fname)
                    except Exception as exc:
                        print(f"Could not open {fname} with {opener}")
                        print(f"   exception = {exc}")
    app = Sitka_App()
    if len(files) > 0:
        for name, object in files.items():
            app.add_data(name, object)
    app.MainLoop()

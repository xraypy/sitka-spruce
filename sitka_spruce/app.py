from argparse import ArgumentParser
from pathlib import Path

from wxmplot.interactive import get_wxapp
from wxutils import (AppConfig, WxApplication,
                     add_application_arguments, handle_shortcut_arguments)


from .data import get_sitka_files
from .sitka import SitkaFrame


APP_CONFIG = AppConfig(
    name="Sitka",
    assets=str(Path(__file__).resolve().parent / "icons"),
    description="Sitka Hierarchical Data Viewer for HDF5 and Zarr",
    application_id="sitka_spruce.sitka",
)


def sitka_viewer(folder=None):
    """Sitka Viewer for use from a Python/Jupyter REPL."""

    get_wxapp()
    sview = SitkaFrame()
    if folder is not None:
        sview.ReadFolder(folder)    

    sview.Show()
    sview.Raise()
    return sview


def make_parser():
    parser = ArgumentParser(description="Sitka Data Viewer")
    add_application_arguments(parser)
    parser.add_argument('-d', '--dir', dest='directory',
                        default=None, help="directory to find data files")
    return parser


def sitka_cli():
    parser = make_parser()
    args = parser.parse_args()

    if handle_shortcut_arguments(parser, args, APP_CONFIG, desktop=True):
        return

    app = WxApplication(APP_CONFIG)
    frame = SitkaFrame(with_inspect=args.inspect)

    if args.directory is not None:
        frame.ReadFolder(args.directory)

    app.run(frame)

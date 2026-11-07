"""Command line entry point.

  dewatermark                         open the web UI (default)
  dewatermark ui [--port N]           same, with options
  dewatermark clean a.png b.jpg ...   clean files, writes *_clean.png
  dewatermark watch                   macOS: clean whatever image you copy
"""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__


def _tuning(p):
    p.add_argument("--photo", action="store_true", help="photo/scan mode (uneven light, blur, noise)")
    p.add_argument("--cut", type=int, default=None, help="manual cut 0-255 (default: automatic)")
    p.add_argument("--soft", type=int, default=40, help="edge softness (default 40)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dewatermark", description="Remove faint watermarks from screenshots and photos of text.")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd")

    ui = sub.add_parser("ui", help="open the web UI (default)")
    ui.add_argument("--port", type=int, default=None, help="port (default: first free from 8790)")
    ui.add_argument("--no-browser", action="store_true", help="don't open a browser tab")

    cl = sub.add_parser("clean", help="clean image files")
    cl.add_argument("files", nargs="+")
    cl.add_argument("-o", "--output", help="output file (single input) or folder")
    _tuning(cl)

    wa = sub.add_parser("watch", help="macOS: clean every image you copy")
    _tuning(wa)

    a = ap.parse_args(argv)

    if a.cmd in (None, "ui"):
        from .server import serve
        serve(port=getattr(a, "port", None), open_browser=not getattr(a, "no_browser", False))
    elif a.cmd == "clean":
        from PIL import Image
        from .core import dewatermark
        mode = "photo" if a.photo else "screenshot"
        for f in a.files:
            clean, info = dewatermark(Image.open(f), a.cut, a.soft, mode)
            stem = os.path.splitext(os.path.basename(f))[0] + "_clean.png"
            if a.output and os.path.isdir(a.output):
                out = os.path.join(a.output, stem)
            elif a.output and len(a.files) == 1:
                out = a.output
            else:
                out = os.path.join(os.path.dirname(f), stem)
            clean.save(out)
            print(f"{f} -> {out}  (cut={info['cut']}, {mode})")
    elif a.cmd == "watch":
        from .watch import watch
        watch("photo" if a.photo else "screenshot", a.cut, a.soft)


if __name__ == "__main__":
    sys.exit(main())

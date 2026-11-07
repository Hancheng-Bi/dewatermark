"""Clipboard watcher: copy an image, and the cleaned version replaces it.

Reading the clipboard works on macOS and Windows (Pillow's ImageGrab).
Writing the cleaned image back uses AppleScript, so this mode is macOS-only;
everywhere else, use the web UI.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image, ImageGrab

from .core import dewatermark


def _hash(img):
    return hashlib.md5(np.asarray(img.convert("RGB")).tobytes()).hexdigest()


def _read():
    try:
        data = ImageGrab.grabclipboard()
    except Exception:
        return None
    if isinstance(data, Image.Image):
        return data
    if isinstance(data, list):  # files copied in Finder
        for p in data:
            try:
                return Image.open(p)
            except Exception:
                pass
    return None


def _write(img):
    path = os.path.join(tempfile.gettempdir(), "dewatermark_clip.png")
    img.save(path, "PNG")
    script = f'set the clipboard to (read (POSIX file "{path}") as «class PNGf»)'
    subprocess.run(["osascript", "-e", script], check=True, capture_output=True)


def watch(mode="screenshot", threshold=None, softness=40, interval=0.8):
    if sys.platform != "darwin":
        sys.exit("Clipboard watch mode is macOS-only. Run `dewatermark` for the web UI.")
    seen = set()
    first = _read()
    if first is not None:
        seen.add(_hash(first))
    print(f"Watching the clipboard ({mode} mode). Copy an image; Ctrl+C to stop.")
    try:
        while True:
            time.sleep(interval)
            img = _read()
            if img is None:
                continue
            h = _hash(img)
            if h in seen:
                continue
            seen.add(h)
            try:
                clean, info = dewatermark(img, threshold, softness, mode)
                seen.add(_hash(clean))
                _write(clean)
                print(f"✔ {img.width}×{img.height}, cut={info['cut']} → ready to paste")
            except Exception as e:
                print(f"✘ {e}")
    except KeyboardInterrupt:
        print("\nstopped")

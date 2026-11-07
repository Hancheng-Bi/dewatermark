"""Synthetic tests: text + tiled watermark, check the watermark is gone and
the text survives. Run with `python -m pytest` (pytest is not a runtime dep)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from dewatermark import dewatermark

W, H = 640, 360


def _text_mask():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for i in range(4):
        d.rectangle((40, 40 + i * 60, 40 + 400, 40 + i * 60 + 6), fill=255)  # "text" strokes
    return np.asarray(m) > 0


def _wm_mask():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for x in range(-H, W, 90):
        d.line((x, H, x + H, 0), fill=255, width=10)  # diagonal watermark bands
    return np.asarray(m) > 0


def _compose(bg, text, wm, wm_alpha=0.3):
    t, w = _text_mask(), _wm_mask()
    img = np.empty((H, W, 3), np.float32)
    img[:] = bg
    img[w] = img[w] * (1 - wm_alpha) + np.array(wm) * wm_alpha
    img[t] = text
    return np.clip(img, 0, 255).astype(np.uint8), t, w & ~t


def _check(out, text, wm, light):
    g = np.asarray(out.convert("L")).astype(float)
    ink = 255 - g if light else g
    assert ink[text].mean() > 200, "text was lost"
    assert ink[wm].mean() < 20, "watermark remains"


def test_dark_screenshot():
    arr, t, w = _compose((12, 12, 14), (235, 235, 235), (200, 120, 120))
    out, info = dewatermark(Image.fromarray(arr))
    assert not info["light_background"]
    _check(out, t, w, light=False)


def test_light_screenshot():
    arr, t, w = _compose((250, 250, 250), (20, 20, 20), (120, 120, 200))
    out, info = dewatermark(Image.fromarray(arr))
    assert info["light_background"]
    _check(out, t, w, light=True)


def test_photo_uneven_light_blur_noise():
    arr, t, w = _compose((235, 230, 220), (30, 30, 35), (150, 150, 170), wm_alpha=0.35)
    yy, xx = np.mgrid[0:H, 0:W]
    light = 0.6 + 0.4 * (xx / W)  # strong left-to-right shading
    arr = arr.astype(np.float32) * light[..., None]
    arr += np.random.default_rng(0).normal(0, 6, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    out, _ = dewatermark(img, mode="photo")
    # blur widens strokes, so check only stroke centres / band centres
    from scipy import ndimage  # test-only
    _check(out, ndimage.binary_erosion(t, iterations=2), ndimage.binary_erosion(w, iterations=3), light=True)

"""
The de-watermarking algorithm. Depends only on NumPy and Pillow.

Idea: a watermark is a faint, semi-transparent overlay. Compared with the text
it is weaker (less contrast with the background) and often tinted. So we build
an "ink" map (how strongly each pixel looks like text), find the level that
separates real text from everything weaker (3-class Otsu: background /
watermark / text, keep the top class) and remap everything below it to
background.

Two modes:
  screenshot  clean, evenly lit images: works on the raw pixels.
  photo       photos or scans: also flattens uneven lighting, denoises,
              sharpens slightly and removes leftover specks.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageFilter, ImageOps

MODES = ("screenshot", "photo")


def otsu3_upper(values: np.ndarray) -> int:
    """Upper threshold of a 3-class Otsu split on uint8 data."""
    hist = np.bincount(values.ravel(), minlength=256).astype(np.float64)
    p = hist / hist.sum()
    levels = np.arange(256, dtype=np.float64)
    w = np.cumsum(p)
    mu = np.cumsum(p * levels)
    mu_t = mu[-1]
    best, best_t2 = -1.0, 128
    for t1 in range(1, 254):
        w0, m0 = w[t1], mu[t1]
        if w0 <= 0:
            continue
        t2 = np.arange(t1 + 1, 255)
        w1 = w[t2] - w0
        w2 = 1.0 - w[t2]
        m1 = mu[t2] - m0
        m2 = mu_t - mu[t2]
        with np.errstate(divide="ignore", invalid="ignore"):
            var = (m0**2 / w0
                   + np.where(w1 > 0, m1**2 / w1, 0)
                   + np.where(w2 > 0, m2**2 / w2, 0))
        i = int(np.nanargmax(var))
        if var[i] > best:
            best, best_t2 = var[i], int(t2[i])
    return best_t2


def _morph(chan: np.ndarray, radius: int, opening: bool) -> np.ndarray:
    """Smooth background estimate via grey opening/closing, done on a
    downscaled copy so it stays fast on large photos."""
    h, w = chan.shape
    f = max(1, radius // 4)
    k = 2 * math.ceil(radius / f) + 1
    small = Image.fromarray(chan).resize((max(1, w // f), max(1, h // f)), Image.BOX)
    first, second = (ImageFilter.MinFilter, ImageFilter.MaxFilter) if opening else \
                    (ImageFilter.MaxFilter, ImageFilter.MinFilter)
    small = small.filter(first(k)).filter(second(k)).filter(ImageFilter.GaussianBlur(k / 2))
    return np.asarray(small.resize((w, h), Image.BILINEAR), dtype=np.float32)


def _ink_map(rgb: np.ndarray, light: bool, photo: bool) -> np.ndarray:
    """uint8 map: 0 = background, high = strong text, watermark in between."""
    if light:
        # dark text on light paper; tinted watermark keeps a high max channel
        chan = rgb.max(axis=2)
    else:
        # light text on dark background; tinted watermark has a low min channel
        chan = rgb.min(axis=2)

    if not photo:
        ink = 255 - chan if light else chan
        return ink.astype(np.uint8)

    radius = max(8, min(chan.shape) // 25)
    c = chan.astype(np.float32)
    if light:
        bg = np.maximum(_morph(chan, radius, opening=False), 1.0)
        ink = np.clip(1.0 - c / bg, 0, 1) * 255
    else:
        bg = _morph(chan, radius, opening=True)
        ink = np.clip(c - bg, 0, None)
    # stretch so the strongest text reaches full scale
    top = np.percentile(ink, 99.7)
    if top > 0:
        ink = np.clip(ink * (255.0 / top), 0, 255)
    img = Image.fromarray(ink.astype(np.uint8))
    blur = max(0.6, min(chan.shape) / 1500)
    img = img.filter(ImageFilter.GaussianBlur(blur))
    img = img.filter(ImageFilter.UnsharpMask(radius=2 * blur + 1, percent=80, threshold=2))
    return np.asarray(img, dtype=np.uint8)


def dewatermark(img: Image.Image, threshold: int | None = None, softness: int = 40,
                mode: str = "screenshot"):
    """Clean an image. Returns (PIL.Image, info dict).

    threshold  0-255 cut; None = automatic. Higher removes more.
    softness   width of the anti-aliasing ramp above the cut.
    mode       "screenshot" or "photo".
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    photo = mode == "photo"
    img = ImageOps.exif_transpose(img)
    rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
    light = bool(np.median(rgb) > 127)

    ink = _ink_map(rgb, light, photo)
    cut = threshold if threshold is not None else otsu3_upper(ink)
    cut = int(np.clip(cut, 1, 250))
    top = min(255, cut + max(1, softness))

    out = (ink.astype(np.float32) - cut) / (top - cut)
    out = (np.clip(out, 0, 1) * 255).astype(np.uint8)
    if photo:
        out = np.asarray(Image.fromarray(out).filter(ImageFilter.MedianFilter(3)))
    if light:
        out = 255 - out
    result = Image.fromarray(out, "L").convert("RGB")
    return result, {"cut": cut, "light_background": light, "mode": mode}

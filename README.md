# dewatermark

Remove faint watermarks from screenshots and photos of text, from a local web UI
or the command line. Everything runs on your own machine. The only dependencies
are **NumPy** and **Pillow**.

![Before / after: dark screenshot (top) and a blurry, unevenly lit photo (bottom)](docs/demo.png)

## Install

You need Python 3.9 or newer. Pick one:

```bash
# Recommended: installs the `dewatermark` command in its own isolated environment
pipx install git+https://github.com/Hancheng-Bi/dewatermark.git

# Or with plain pip (ideally inside a virtual environment)
pip install git+https://github.com/Hancheng-Bi/dewatermark.git

# Or run it once without installing (needs uv)
uvx --from git+https://github.com/Hancheng-Bi/dewatermark.git dewatermark
```

## Use

### Web UI

```bash
dewatermark
```

Your browser opens at `http://localhost:8790` (or the next free port).

1. Paste an image with **⌘V** / **Ctrl+V**, or drop a file onto the page. The cleaned
   version is copied to your clipboard right away.
2. Choose **Screenshot** for clean, evenly lit images, or **Photo** for photos and scans
   that are blurry, noisy or unevenly lit.
3. If traces of the watermark remain, untick **Auto cut** and drag **Cut** up. If thin
   text disappears, drag it down.

Options: `dewatermark ui --port 9000`, `dewatermark ui --no-browser`.

### Command line

```bash
dewatermark clean screenshot.png               # writes screenshot_clean.png
dewatermark clean --photo IMG_1234.jpg         # photo mode
dewatermark clean *.png -o cleaned/            # batch into a folder
dewatermark clean shot.png --cut 150 --soft 20 # manual tuning
```

### Clipboard watcher (macOS)

```bash
dewatermark watch          # or: dewatermark watch --photo
```

Copy any image and the cleaned version replaces it on your clipboard within a second.

### From Python

```python
from PIL import Image
from dewatermark import dewatermark

clean, info = dewatermark(Image.open("shot.png"), mode="photo")  # threshold=None, softness=40
clean.save("shot_clean.png")
```

## How it works

A typical watermark is a faint, semi-transparent overlay. It contrasts less with
the background than the real text does, and it is often tinted.

1. **Ink map.** Each pixel gets a score for how much it looks like text. On dark
   backgrounds the score is the *minimum* of R, G and B. On light backgrounds it is
   based on the *maximum*. Either way, tinted watermark pixels score low.
2. **Photo mode only.** Uneven lighting is flattened by estimating the background
   with a grey opening or closing, run on a downscaled copy so it stays fast. The
   ink map is then lightly denoised and sharpened.
3. **Automatic cut.** A 3-class Otsu threshold splits the histogram into background,
   watermark and text, and only the top class is kept.
4. **Soft remap.** Everything below the cut becomes background, and the text keeps an
   anti-aliased edge. Photo mode also removes small leftover specks.

## Limitations

- It works when the watermark is **fainter or more coloured than the text**. A watermark
  as dark and solid as the text cannot be separated by brightness.
- The output is black and white, so coloured text such as syntax highlighting comes out
  in a single colour.
- It is built for **text** images. Watermarks over photos of people or scenes need
  inpainting, for example with OpenCV or the LaMa model, which this tool does not do.

Only remove watermarks from images you have the right to modify.

## Development

```bash
git clone https://github.com/Hancheng-Bi/dewatermark.git && cd dewatermark
pip install -e . pytest scipy
pytest
```

## License

MIT

"""Tiny local web UI (standard library http.server, no extra dependencies)."""
from __future__ import annotations

import io
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import parse_qs, urlparse

from PIL import Image

from .core import dewatermark

MAX_UPLOAD = 80 * 1024 * 1024
DEFAULT_PORTS = list(range(8790, 8800)) + [0]  # 0 = any free port


def _page() -> bytes:
    return resources.files("dewatermark").joinpath("static/index.html").read_bytes()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, ctype, body, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", _page())
        else:
            self._send(404, "text/plain", b"not found")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/process":
            self._send(404, "text/plain", b"not found")
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0 or n > MAX_UPLOAD:
                raise ValueError("image missing or too large")
            q = parse_qs(u.query)
            img = Image.open(io.BytesIO(self.rfile.read(n)))
            clean, info = dewatermark(
                img,
                threshold=int(q["cut"][0]) if "cut" in q else None,
                softness=int(q.get("soft", ["40"])[0]),
                mode=q.get("mode", ["screenshot"])[0],
            )
            buf = io.BytesIO()
            clean.save(buf, "PNG")
            self._send(200, "image/png", buf.getvalue(), {"X-Cut": str(info["cut"])})
        except Exception as e:  # report to the page instead of crashing
            self._send(400, "text/plain; charset=utf-8", str(e).encode())


def serve(port: int | None = None, open_browser: bool = True, host: str = "127.0.0.1"):
    srv = None
    for p in ([port] if port else DEFAULT_PORTS):
        try:
            srv = ThreadingHTTPServer((host, p), Handler)
            break
        except OSError:
            continue
    if srv is None:
        sys.exit(f"Port {port} is in use; pick another with --port")
    url = f"http://localhost:{srv.server_address[1]}"
    print(f"De-watermark UI running at {url}\nPress Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        srv.server_close()

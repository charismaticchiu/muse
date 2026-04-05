"""HTTP server for the muse web gallery."""

import json
import mimetypes
import webbrowser
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from muse.session import SessionManager


class GalleryApp:
    """Handles API logic for the gallery."""

    def __init__(self, muse_home: Path):
        self.muse_home = muse_home
        self.session_mgr = SessionManager(muse_home)

    def handle_api(self, path: str) -> str:
        if path == "/api/sessions":
            return self._list_sessions()
        if path.startswith("/api/sessions/"):
            name = path[len("/api/sessions/"):]
            return self._session_detail(name)
        return json.dumps({"error": "not found"})

    def _list_sessions(self) -> str:
        sessions = self.session_mgr.list_sessions()
        return json.dumps([s.to_dict() for s in sessions], default=str)

    def _session_detail(self, name: str) -> str:
        try:
            session = self.session_mgr.load(name)
        except (FileNotFoundError, json.JSONDecodeError):
            return json.dumps({"error": f"Session not found: {name}"})

        steps = self.session_mgr.get_history(name)
        return json.dumps(
            {"session": session.to_dict(), "steps": [s.to_dict() for s in steps]},
            default=str,
        )


class GalleryHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves API + static files."""

    def __init__(self, *args, gallery_app: GalleryApp, static_dir: Path, **kwargs):
        self.gallery_app = gallery_app
        self.static_dir = static_dir
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._handle_api()
        elif self.path.startswith("/images/"):
            self._handle_image()
        else:
            super().do_GET()

    def _handle_api(self):
        response = self.gallery_app.handle_api(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response.encode())

    def _handle_image(self):
        parts = self.path[len("/images/"):].split("/", 1)
        if len(parts) != 2:
            self.send_error(404)
            return

        session_name, filename = parts
        image_path = (
            self.gallery_app.muse_home / "sessions" / session_name / "steps" / filename
        )

        if not image_path.exists():
            self.send_error(404)
            return

        mime_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.end_headers()
        self.wfile.write(image_path.read_bytes())

    def log_message(self, format, *args):
        pass


def start_gallery(muse_home: Path, port: int = 3333, open_browser: bool = True):
    """Start the gallery HTTP server."""
    static_dir = Path(__file__).parent / "static"
    app = GalleryApp(muse_home)

    handler = partial(GalleryHandler, gallery_app=app, static_dir=static_dir)
    server = HTTPServer(("127.0.0.1", port), handler)

    url = f"http://localhost:{port}"
    print(f"  Gallery running at {url}")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Gallery stopped.")
        server.server_close()

from http.server import BaseHTTPRequestHandler, HTTPServer
import threading


class CaptionServer:
    def __init__(self, host: str, port: int, on_text) -> None:
        self._host = host
        self._port = port
        self._on_text = on_text
        self._server = None
        self._thread = None

    def start(self) -> None:
        handler = self._build_handler()
        self._server = HTTPServer((self._host, self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._server = None
        self._thread = None

    def _build_handler(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != "/caption":
                    self.send_response(404)
                    self.end_headers()
                    return

                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b""
                text = raw.decode("utf-8", errors="ignore").strip()
                if text:
                    parent._on_text(text)

                self.send_response(204)
                self.end_headers()

            def log_message(self, _format, *_args):
                return

        return Handler

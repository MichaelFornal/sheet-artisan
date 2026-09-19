"""A tiny threaded HTTP server for tests: routes are plain functions, every hit is counted."""
from __future__ import annotations

import collections
import http.server
import json
import threading
import urllib.parse


class FixtureServer:
    """routes: {path: fn(method, query: dict, body: bytes, hit_number: int) -> (status, headers, body)}.

    A path with no route returns 404. `hits[path]` counts requests per path.
    """

    def __init__(self, routes):
        self.routes = routes
        self.hits = collections.Counter()
        self.last_headers = {}
        self._lock = threading.Lock()
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _serve(self, method):
                parsed = urllib.parse.urlparse(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                with server._lock:
                    server.hits[parsed.path] += 1
                    server.last_headers[parsed.path] = dict(self.headers)
                    n = server.hits[parsed.path]
                fn = server.routes.get(parsed.path)
                if fn is None:  # "prefix*" routes match anything under the prefix
                    fn = next((f for k, f in server.routes.items()
                               if k.endswith("*") and parsed.path.startswith(k[:-1])), None)
                if fn is None:
                    status, headers, payload = 404, {}, b"not found"
                else:
                    query = dict(urllib.parse.parse_qsl(parsed.query))
                    query["_path"] = parsed.path
                    status, headers, payload = fn(method, query, body, n)
                if isinstance(payload, (dict, list)):
                    payload = json.dumps(payload).encode()
                    headers = {"Content-Type": "application/json", **headers}
                elif isinstance(payload, str):
                    payload = payload.encode()
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                self._serve("GET")

            def do_POST(self):
                self._serve("POST")

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)

    def url(self, path=""):
        return f"http://127.0.0.1:{self.port}{path}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


def ok(payload="ok", status=200, headers=None):
    return lambda method, query, body, n: (status, headers or {}, payload)


ROBOTS_ALLOW_ALL = ok("User-agent: *\nDisallow:\n")

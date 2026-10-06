"""
Mock cloud ingestion service.

A tiny local HTTP server (stdlib only) that accepts reading batches and
exposes a simple JSON API. Storage is an in-memory list mirrored to a
JSONL file. This is a stand-in for a real cloud endpoint, for demo and
teaching purposes only. Everything stored is SYNTHETIC.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _Handler(BaseHTTPRequestHandler):
    server_version = "MockCloud/1.0"

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/readings":
            return self._json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length).decode())
            readings = payload["readings"]
        except (ValueError, KeyError, UnicodeDecodeError):
            return self._json({"error": "bad request"}, 400)
        store = self.server.store
        with self.server.lock:
            store.extend(readings)
            if self.server.jsonl_path:
                with open(self.server.jsonl_path, "a") as f:
                    for r in readings:
                        f.write(json.dumps(r) + "\n")
            count = len(store)
        self._json({"ok": True, "stored_total": count})

    def do_GET(self):
        if self.path == "/api/readings":
            with self.server.lock:
                data = list(self.server.store)
            return self._json({"count": len(data), "readings": data})
        if self.path == "/api/stats":
            with self.server.lock:
                nodes = sorted({r["node_id"] for r in self.server.store})
                count = len(self.server.store)
            return self._json({"stored_readings": count, "nodes": nodes})
        if self.path in ("/", "/health"):
            return self._json({"status": "ok", "service": "mock-cloud-ingest"})
        return self._json({"error": "not found"}, 404)

    def log_message(self, *args):
        pass  # keep demo output clean


class CloudServer:
    """Local mock-cloud HTTP server running in a background thread."""

    def __init__(self, host="127.0.0.1", port=0, jsonl_path=None):
        self.host = host
        self.jsonl_path = jsonl_path
        if jsonl_path:
            os.makedirs(os.path.dirname(jsonl_path) or ".", exist_ok=True)
            open(jsonl_path, "w").close()  # fresh log per run
        self._server = ThreadingHTTPServer((host, port), _Handler)
        self._server.store = []
        self._server.lock = threading.Lock()
        self._server.jsonl_path = jsonl_path
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self):
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def reading_count(self):
        with self._server.lock:
            return len(self._server.store)

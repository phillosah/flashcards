"""
FlashCards server.
Serves the web app and provides read/write access to a local JSON file.

Local usage:
    python server.py [--port 8000] [--file flashcards_data.json]

Render deployment:
    PORT env var is set automatically by Render.
    DATA_FILE env var can override the data file path.
"""

import http.server
import json
import os
import argparse
import threading
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Thread lock so concurrent requests don't corrupt the file
_file_lock = threading.Lock()


class FlashCardsHandler(http.server.SimpleHTTPRequestHandler):
    data_file = os.path.join(SCRIPT_DIR, "flashcards_data.json")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/data":
            self._serve_data()
        elif path == "/api/ping":
            self._ping()
        else:
            super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/data":
            self._save_data()
        else:
            self.send_error(404)

    def _serve_data(self):
        with _file_lock:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = f.read()
            else:
                data = "[]"
        self._json_response(200, data.encode("utf-8"))

    def _save_data(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            parsed = json.loads(body)
            if not isinstance(parsed, list):
                raise ValueError("Expected a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[save] Invalid data: {e}")
            self._json_response(400, json.dumps({"error": str(e)}).encode())
            return

        with _file_lock:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            # Write to temp file then rename for atomic update
            tmp = self.data_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.data_file)

        print(f"[save] {len(parsed)} folder(s) saved to {self.data_file}")
        self._json_response(200, b'{"ok":true}')

    def _ping(self):
        info = {
            "status": "ok",
            "data_file": self.data_file,
            "file_exists": os.path.exists(self.data_file),
            "file_writable": os.access(os.path.dirname(self.data_file), os.W_OK),
        }
        self._json_response(200, json.dumps(info).encode())

    def _json_response(self, code, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Log everything so Render logs show what's happening
        super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description="FlashCards server")
    default_port = int(os.environ.get("PORT", 8000))
    parser.add_argument("--port", type=int, default=default_port)

    # DATA_FILE: if set and relative, resolve it relative to SCRIPT_DIR
    env_file = os.environ.get("DATA_FILE", "")
    if env_file and not os.path.isabs(env_file):
        env_file = os.path.join(SCRIPT_DIR, env_file)
    default_file = env_file or os.path.join(SCRIPT_DIR, "flashcards_data.json")
    parser.add_argument("--file", default=default_file)
    args = parser.parse_args()

    FlashCardsHandler.data_file = os.path.abspath(args.file)

    print(f"Data file : {FlashCardsHandler.data_file}")
    print(f"Server    : http://0.0.0.0:{args.port}")
    print(f"Ping      : http://0.0.0.0:{args.port}/api/ping")
    print(f"Press Ctrl+C to stop.\n")

    # ThreadingHTTPServer handles multiple browsers concurrently
    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), FlashCardsHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()

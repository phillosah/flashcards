"""
FlashCards server.
Serves the web app and provides read/write access to a local JSON file.

Local usage:
    python server.py [--port 8000] [--file flashcards_data.json]

Render (or any cloud host):
    Set env var DATA_FILE to a path on a persistent disk, e.g. /data/flashcards_data.json
    The PORT env var is read automatically.
"""

import http.server
import json
import os
import argparse
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class FlashCardsHandler(http.server.SimpleHTTPRequestHandler):
    data_file = os.path.join(SCRIPT_DIR, "flashcards_data.json")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)

    def do_GET(self):
        if urlparse(self.path).path == "/api/data":
            self._serve_data()
        else:
            super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path == "/api/data":
            self._save_data()
        else:
            self.send_error(404)

    def _serve_data(self):
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
            self._json_response(400, json.dumps({"error": str(e)}).encode())
            return
        # Ensure parent directory exists (important for Render persistent disk)
        os.makedirs(os.path.dirname(os.path.abspath(self.data_file)), exist_ok=True)
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        self._json_response(200, b'{"ok":true}')

    def _json_response(self, code, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        path = args[0].split()[1] if args else ""
        if path.startswith("/api") or "404" in str(args):
            super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description="FlashCards server")
    # PORT env var is set by Render automatically; --port flag for local use
    default_port = int(os.environ.get("PORT", 8000))
    parser.add_argument("--port", type=int, default=default_port)
    # DATA_FILE env var lets Render point at a persistent disk path
    default_file = os.environ.get("DATA_FILE", os.path.join(SCRIPT_DIR, "flashcards_data.json"))
    parser.add_argument("--file", default=default_file, help="Path to the JSON data file")
    args = parser.parse_args()

    FlashCardsHandler.data_file = os.path.abspath(args.file)

    print(f"Data file : {FlashCardsHandler.data_file}")
    print(f"Server    : http://0.0.0.0:{args.port}")
    print(f"Press Ctrl+C to stop.\n")

    server = http.server.HTTPServer(("0.0.0.0", args.port), FlashCardsHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()

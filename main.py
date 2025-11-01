import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from snake import info, start, move, end  # your existing functions

class BattlesnakeHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._set_headers()
            response = info()
        else:
            self.send_error(404, "Not Found")
            return

        self.wfile.write(json.dumps(response).encode("utf-8"))

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            game_state = json.loads(body) if body else {}
        except json.JSONDecodeError:
            game_state = {}

        if path == "/start":
            response = start(game_state)
        elif path == "/move":
            response = move(game_state)
        elif path == "/end":
            response = end(game_state)
        else:
            self.send_error(404, "Not Found")
            return

        self._set_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def log_message(self, format, *args):
        # Disable default access logs
        return

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), BattlesnakeHandler)
    print(f"Server running on port {port}")
    server.serve_forever()

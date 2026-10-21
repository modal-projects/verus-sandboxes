"""Runs in the verifier Sidecar: checks Rust source against its own copy of the contract."""

import shutil
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer


def check(source: bytes) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as work:
        for name in ("main.rs", "spec.rs"):
            shutil.copy(f"/contract/{name}", work)
        with open(f"{work}/candidate.rs", "wb") as f:
            f.write(source)
        p = subprocess.run(
            ["verus", "--no-cheating", f"{work}/main.rs"], capture_output=True, text=True
        )
        return p.returncode == 0, p.stdout + p.stderr


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        ok, output = check(self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(200 if ok else 422)
        self.end_headers()
        self.wfile.write(output.encode())


if __name__ == "__main__":
    HTTPServer(("", 8080), Handler).serve_forever()

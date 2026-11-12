"""Local live interface; the CLI and web UI share the same agent runner."""
import argparse
import asyncio
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from agent import make_agent
from cli import QUESTION, review
from tools import RepositoryTools


def choose_folder():
    """Open a native picker on the computer running this local server."""
    if sys.platform == "darwin":
        result = subprocess.run(
            ["osascript", "-e",
             'POSIX path of (choose folder with prompt "Choose a repository")'],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode:
            if "(-128)" in result.stderr:  # User cancelled the picker.
                return None
            raise RuntimeError("Folder picker unavailable; paste a path instead.")
        return result.stdout.strip()
    import tkinter
    from tkinter import filedialog
    root = tkinter.Tk()
    root.withdraw()
    try:
        return filedialog.askdirectory(title="Choose a repository") or None
    finally:
        root.destroy()


def serve(repo=None, model_name="gemini-3.5-flash-lite", port=8767):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError("Set GEMINI_API_KEY to run live reviews.")
    token = secrets.token_urlsafe(32)
    page = Path(__file__).with_name("web.html").read_text()
    initial = str(Path(repo).expanduser().resolve()) if repo else ""
    page = page.replace("__TOKEN__", token).replace("__REPO__", escape(initial))
    origin = f"http://127.0.0.1:{port}"

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'",
            )
            self.end_headers()

        def json_response(self, status, value):
            self.respond(status, "application/json")
            self.wfile.write(json.dumps(value).encode())

        def do_GET(self):
            if self.headers.get("Host") != f"127.0.0.1:{port}":
                self.send_error(403)
                return
            if self.path != "/":
                self.send_error(404)
                return
            self.respond(200, "text/html; charset=utf-8")
            self.wfile.write(page.encode())

        def do_POST(self):
            if (
                self.path not in ("/review", "/folder")
                or self.headers.get("Host") != f"127.0.0.1:{port}"
                or self.headers.get("Origin") != origin
                or self.headers.get("X-Review-Token") != token
                or self.headers.get("Content-Type") != "application/json"
            ):
                self.send_error(403)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    raise ValueError()
                request = json.loads(self.rfile.read(size))
                if not isinstance(request, dict):
                    raise ValueError()
                if self.path == "/folder":
                    if request != {}:
                        raise ValueError()
                elif (
                    set(request) != {"repo"}
                    or not isinstance(request["repo"], str)
                    or not request["repo"].strip()
                ):
                    raise ValueError()
            except (ValueError, TypeError):
                self.json_response(400, {"error": "Choose a repository folder."})
                return
            if self.path == "/folder":
                try:
                    self.json_response(200, {"path": choose_folder()})
                except Exception:
                    self.json_response(503, {
                        "error": "Folder picker unavailable. Paste a path instead."
                    })
                return
            try:
                # Snapshot the selected folder afresh for each review.
                source = RepositoryTools(request["repo"].strip())
                if not source.files:
                    raise ValueError()
                agent = make_agent(source, model_name, key)
            except (OSError, ValueError):
                self.json_response(400, {
                    "error": "Choose an accessible folder with source files."
                })
                return
            self.respond(200, "application/x-ndjson; charset=utf-8")

            def emit(label, value):
                event = json.dumps({"label": label, "value": value})
                self.wfile.write((event + "\n").encode())
                self.wfile.flush()

            try:
                asyncio.run(review(agent, QUESTION, emit=emit))
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_):
            pass

    # One review at a time; deliberately not a hosted multi-user service.
    with HTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"Live Gemini: {origin}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument(
        "--model", default=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    )
    args = parser.parse_args()
    try:
        serve(args.repo, args.model, args.port)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Cannot start: {error}\n")

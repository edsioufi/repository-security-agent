"""Local-only web interface; the CLI and web UI share the same agent runner."""
import argparse
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets

from agent import make_agent
from cli import QUESTION, review
from tools import RepositoryTools


def serve(repo, model_name, offline=False, port=8767):
    # The source root is chosen by the local operator, never a web request.
    source = RepositoryTools(repo)
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not offline and not key:
        raise ValueError("Set GEMINI_API_KEY or pass --offline.")
    token = secrets.token_urlsafe(32)
    mode = "Offline scripted demonstration" if offline else "Live Gemini"
    page = Path(__file__).with_name("web.html").read_text()
    page = page.replace("__TOKEN__", token).replace("__MODE__", mode)
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
                self.path != "/review"
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
                if request != {}:
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                self.send_error(400, "Expected an empty JSON object.")
                return
            self.respond(200, "application/x-ndjson; charset=utf-8")

            def emit(label, value):
                event = json.dumps({"label": label, "value": value})
                self.wfile.write((event + "\n").encode())
                self.wfile.flush()

            model = None
            if offline:
                from offline import ScriptedModel
                model = ScriptedModel()
            agent = make_agent(source, model_name, key, model=model)
            try:
                asyncio.run(review(agent, QUESTION, emit=emit))
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_):
            pass

    # One review at a time; deliberately not a hosted multi-user service.
    with HTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"{mode}: {origin}\nSource: {Path(repo).resolve()}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default="sample")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument(
        "--model", default=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    )
    args = parser.parse_args()
    try:
        serve(args.repo, args.model, args.offline, args.port)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Cannot start: {error}\n")

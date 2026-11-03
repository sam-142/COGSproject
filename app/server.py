"""A local web page over both Cogs, for the accounting team.

Drop in this month's Brex statement (and earlier months), press Run, and get back:
  - the updated statement, with subscription memos filled in (the auto-coder);
  - the review report (the auto-coder);
  - a Slack draft for every charge still without a memo (the chase-list builder).

This app contains no Cog logic and imports no Cog code. It runs each Cog exactly
as a person would from the terminal, through its pixi tasks, and reads the files
they write:

    auto-coder          pixi run code <statement> --history <earlier...> --out <dir>
    chase-list builder  pixi run draft <the auto-coder's .upload.csv> --out <dir>

So each Cog runs in its own environment, and the page can't drift from what the
command line does.

Kept deliberately local:
  - it listens on 127.0.0.1 only, so nothing outside this computer can reach it;
  - the page loads nothing from the internet, so statement data never leaves the machine;
  - every request must carry a random per-session token, so another website open
    in the same browser can't send files to it;
  - uploads and results live in a temporary folder, deleted however it is stopped
    (Ctrl+C, closing the terminal, a kill signal).

Standard library only.

    pixi run --manifest-path app/pixi.toml ui [--context DIR] [--log FILE] [--port 8765] [--no-browser]
"""
import argparse
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import webbrowser
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parent.parent
AUTO_CODER = REPO / "cogs" / "recurring-subscription-auto-coder-cog" / "pixi.toml"
CHASE_LIST = REPO / "cogs" / "chase-list-builder-cog" / "pixi.toml"
PAGE = Path(__file__).with_name("static") / "index.html"
MAX_UPLOAD = 50 * 1024 * 1024          # 50 MB per run: far more than a year of statements
COG_TIMEOUT = 300                       # seconds; the first run of a Cog may install its environment


class CogError(Exception):
    """A Cog run failed; the message is the Cog's own error line."""


def _cog_env():
    """The environment for a Cog run, without this app's own pixi/conda settings,
    so each Cog runs in its own environment and nothing leaks across."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PIXI_", "CONDA_"))}
    env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep)
                                  if f"{os.sep}.pixi{os.sep}envs{os.sep}" not in p)
    return env


def run_cog(manifest, task, args):
    """`pixi run <task> <args>` in a Cog. Paths in args must be absolute."""
    cmd = ["pixi", "run", "-q", "--manifest-path", str(manifest), task, *map(str, args)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=_cog_env(),
                           cwd=REPO, timeout=COG_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise CogError(f"{manifest.parent.name} took longer than {COG_TIMEOUT}s") from None
    if r.returncode != 0:
        # The Cogs print one "error: ..." line for things a person can fix (a
        # missing column, a bad context folder). Show that, never a whole log.
        lines = [l for l in r.stderr.splitlines() if l.startswith("error:")]
        raise CogError(lines[-1][len("error:"):].strip() if lines
                       else f"{manifest.parent.name} failed (exit {r.returncode})")
    return r


class App:
    """State for one running server: the token, the settings, the work folder, the runs."""

    def __init__(self, context_dir=None, log_path=None, workdir=None):
        self.token = secrets.token_urlsafe(24)
        self.context_dir = Path(context_dir) if context_dir else None
        self.log_path = Path(log_path) if log_path else None
        self.workdir = Path(workdir or tempfile.mkdtemp(prefix="cogs-app-"))
        self.runs = {}                  # run id -> {file name: path}
        self.lock = threading.Lock()

    def page(self):
        context = str(self.context_dir) if self.context_dir else "the Cogs' defaults (no real context)"
        log = str(self.log_path) if self.log_path else "none (every charge without a memo is drafted)"
        return (PAGE.read_text(encoding="utf-8")
                .replace("{{TOKEN}}", self.token)
                .replace("{{CONTEXT}}", _html(context))
                .replace("{{LOG}}", _html(log)))

    def run(self, statement, history):
        """statement: (filename, bytes); history: [(filename, bytes)]."""
        run_id = secrets.token_hex(6)
        base = self.workdir / run_id
        month = _save(base / "inputs", statement, "statement")
        earlier = [_save(base / "inputs" / f"history-{i}", f, f"history-{i}") for i, f in enumerate(history)]
        context = ["--context", self.context_dir] if self.context_dir else []

        auto_out = base / "auto-coder"
        run_cog(AUTO_CODER, "code", [month, *(["--history", *earlier] if earlier else []),
                                     "--out", auto_out, *context])
        auto = json.loads((auto_out / f"{month.stem}.recurring.json").read_text(encoding="utf-8"))
        upload = auto_out / f"{month.stem}.upload.csv"

        chase_out = base / "chase-list"
        log = ["--log", self.log_path] if self.log_path else ["--no-log"]
        run_cog(CHASE_LIST, "draft", [upload, "--out", chase_out, *context, *log])
        chase_json = next(chase_out.glob("*.chase.json"))
        chase = json.loads(chase_json.read_text(encoding="utf-8"))

        files = {p.name: p for folder in (auto_out, chase_out) for p in folder.iterdir() if p.is_file()}
        with self.lock:
            self.runs[run_id] = files
        return _response(run_id, auto, chase, files)

    def file(self, run_id, name):
        with self.lock:
            return self.runs.get(run_id, {}).get(name)

    def close(self):
        shutil.rmtree(self.workdir, ignore_errors=True)


def _html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _save(folder, upload, fallback):
    """Write an uploaded file under its own (sanitised) name. Only CSVs are accepted."""
    filename, data = upload
    name = Path(filename or "").name or f"{fallback}.csv"
    if not name.lower().endswith(".csv"):
        raise ValueError(f"{name} isn't a CSV file")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    return path


# File suffix -> (label, description, shown as a main download?)
LABELS = {
    ".upload.csv": ("Updated statement", "The Brex statement with subscription memos filled in. Upload this to QuickBooks.", True),
    ".recurring-review.csv": ("Review report", "Every subscription charge, why it counts as one, and what to check.", True),
    ".drafts.md": ("Slack drafts", "Every drafted message, grouped by channel, for review before sending.", True),
    ".chase-list.csv": ("Chase list", "Every charge and whether it was drafted, skipped or needs routing.", False),
    ".quickbooks.csv": ("QuickBooks entries", "One row per subscription charge, in QuickBooks' nine fields.", False),
    ".recurring.json": ("Auto-coder results (JSON)", "Everything the auto-coder worked out, for tools.", False),
    ".chase.json": ("Chase-list results (JSON)", "Everything the chase-list builder worked out, for tools.", False),
}


def _label(name):
    for suffix, info in LABELS.items():
        if name.endswith(suffix):
            return info
    return name, "", False


def _response(run_id, auto, chase, files):
    order = list(LABELS)
    rank = lambda n: next((i for i, s in enumerate(order) if n.endswith(s)), len(order))
    downloads = []
    for name in sorted(files, key=rank):
        label, about, main = _label(name)
        downloads.append({"name": name, "label": label, "about": about, "main": main})

    def merchant(tx):
        p = tx["parsed"]
        return p.get("merchant_name") or p["merchant_descriptor"]

    flagged = [{"merchant": merchant(tx), "amount": f"{tx['parsed']['amount']:.2f}",
                "date": tx["parsed"]["transaction_date"], "note": tx["inferred"]["coding"]["review"]}
               for tx in auto["transactions"]
               if tx["inferred"]["coding"]["status"] == "ready" and tx["inferred"]["coding"].get("review")]

    by_id = {tx["id"]: tx for tx in chase["transactions"]}
    drafts = []
    for d in chase["drafts"]:
        p = by_id[d["transaction_id"]]["parsed"]
        drafts.append({"channel": d["channel"], "needs_routing": d["needs_routing"], "text": d["text"],
                       "merchant": p.get("merchant_name") or p["merchant_descriptor"],
                       "cardholder": p.get("cardholder") or "",
                       "amount": f"{p['amount']:.2f}", "date": p["transaction_date"]})

    a, c = auto["run"]["counts"], chase["run"]["counts"]
    return {
        "run": run_id,
        "downloads": downloads,
        "counts": {
            "transactions": a["transactions"],
            "memos": sum(1 for tx in auto["transactions"]
                         if tx["inferred"]["coding"]["status"] == "ready"
                         and tx["inferred"]["coding"]["from"]["MEMO"] == "template"),
            "flagged": len(flagged),
            "drafts": c["chase"].get("draft", 0),
            "needs_routing": c["chase"].get("needs-routing", 0),
            "history_months": a["history_months"],
        },
        "missing": [m["vendor"] for m in auto["expected_but_missing"]],
        "flagged": flagged,
        "drafts": drafts,
        "warnings": ([f"Auto-coder: {w}" for w in auto["run"]["warnings"]]
                     + [f"Chase-list builder: {w}" for w in chase["run"]["warnings"]]),
    }


def _parse_multipart(content_type, body):
    """-> {field name: [(filename, bytes), ...]} from a multipart/form-data body."""
    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body)
    fields = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if name:
            fields.setdefault(name, []).append((part.get_filename(), part.get_payload(decode=True) or b""))
    return fields


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "cogs-app"

        def log_message(self, fmt, *args):      # keep the terminal quiet; nothing sensitive logged
            pass

        def _send(self, status, body, content_type, extra=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            # The page may only talk to this server, and nothing may load it in a frame.
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                             "frame-ancestors 'none'")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status, data):
            self._send(status, json.dumps(data).encode(), "application/json")

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/":
                return self._send(HTTPStatus.OK, app.page().encode(), "text/html; charset=utf-8")
            parts = url.path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "download":
                if parse_qs(url.query).get("token", [""])[0] != app.token:
                    return self._json(HTTPStatus.FORBIDDEN, {"error": "bad token"})
                path = app.file(parts[1], parts[2])
                if path is None or not path.exists():
                    return self._json(HTTPStatus.NOT_FOUND, {"error": "no such file"})
                kind = {".csv": "text/csv", ".json": "application/json", ".md": "text/markdown"}.get(
                    path.suffix, "text/plain")
                return self._send(HTTPStatus.OK, path.read_bytes(), f"{kind}; charset=utf-8",
                                  {"Content-Disposition": f'attachment; filename="{path.name}"'})
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self):
            if urlparse(self.path).path != "/run":
                return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            if self.headers.get("X-Token") != app.token:
                return self._json(HTTPStatus.FORBIDDEN, {"error": "bad token"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_UPLOAD:
                return self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "files too large"})
            ctype = self.headers.get("Content-Type", "")
            if not ctype.startswith("multipart/form-data"):
                return self._json(HTTPStatus.BAD_REQUEST, {"error": "expected an upload"})
            fields = _parse_multipart(ctype, self.rfile.read(length))
            statements = [f for f in fields.get("statement", []) if f[1]]
            if len(statements) != 1:
                return self._json(HTTPStatus.BAD_REQUEST, {"error": "add exactly one statement for the month"})
            history = [f for f in fields.get("history", []) if f[1]]
            try:
                return self._json(HTTPStatus.OK, app.run(statements[0], history))
            except (CogError, ValueError) as e:
                return self._json(HTTPStatus.BAD_REQUEST, {"error": str(e)})

    return Handler


def serve(app, port):
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))


def _ignore_signals():
    for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGHUP", None)):
        if sig is not None:
            signal.signal(sig, signal.SIG_IGN)


def _path(p):
    # pixi runs tasks from app/, so a relative path the user typed is resolved
    # against where they typed it (pixi sets INIT_CWD to that).
    p = Path(p).expanduser()
    return p if p.is_absolute() else Path(os.environ.get("INIT_CWD", ".")) / p


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ui", description=__doc__.split("\n\n")[0])
    ap.add_argument("--context", help="folder of real context files, passed to both Cogs")
    ap.add_argument("--log", help="the chase-list builder's chase log; already-sent charges aren't drafted again")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true", help="don't open the page automatically")
    args = ap.parse_args(argv)

    if shutil.which("pixi") is None:
        sys.exit("error: pixi isn't on the PATH; the app runs the Cogs through pixi")
    for manifest in (AUTO_CODER, CHASE_LIST):
        if not manifest.exists():
            sys.exit(f"error: can't find {manifest}")
    context_dir = _path(args.context) if args.context else None
    if context_dir and not context_dir.is_dir():
        sys.exit(f"error: --context folder not found: {context_dir}")

    app = App(context_dir, _path(args.log) if args.log else None)
    server = serve(app, args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Running at {url}  (this computer only)", flush=True)
    print("Press Ctrl+C to stop. Uploaded files and results are deleted when it stops.", flush=True)

    # Ctrl+C, closing the terminal and `kill` all stop it the same way, so the
    # temporary folder with the uploaded statements is always deleted.
    def stop(signum, frame):
        _ignore_signals()               # a second signal mustn't interrupt the clean-up
        raise KeyboardInterrupt
    for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGHUP", None)):
        if sig is not None:
            signal.signal(sig, stop)

    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.", flush=True)
    finally:
        # The uploaded statements must not be left behind, even if more signals
        # arrive while stopping (pixi and the terminal can both send one).
        for _ in range(5):
            try:
                _ignore_signals()
                app.close()
                server.server_close()
                break
            except KeyboardInterrupt:
                continue


if __name__ == "__main__":
    main()

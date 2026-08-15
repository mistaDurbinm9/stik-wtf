#!/usr/bin/env python3
"""stik.wtf node helper — the one tiny service beside Caddy.

Endpoints (Caddy proxies /hook and /api/* here, serves everything else static):
  POST /hook        GitHub push webhook -> git pull + hugo rebuild
  GET  /api/count   increment + return the hit counter ({"n": 123}); ?peek=1 reads only
  GET  /api/uptime  node uptime in days ({"days": 47})

Env: HOOK_SECRET (GitHub webhook secret), SITE_DIR (repo checkout, default /srv/site).
Run: HOOK_SECRET=... python3 serve.py            (listens on 127.0.0.1:8787)
Test: python3 serve.py --selftest

ponytail: single process, counter in a plain file — fine for a personal site;
move to sqlite if it ever sees real concurrency.
"""
import hashlib
import hmac
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SITE_DIR = os.environ.get("SITE_DIR", "/srv/site")
COUNT_FILE = os.path.join(SITE_DIR, ".hits")
LOCK = threading.Lock()


def bump_counter(peek=False, path=None):
    path = path or COUNT_FILE
    with LOCK:
        try:
            n = int(open(path).read().strip() or 0)
        except (FileNotFoundError, ValueError):
            n = 0
        if not peek:
            n += 1
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                f.write(str(n))
            os.replace(tmp, path)
    return n


def uptime_days():
    with open("/proc/uptime") as f:
        return int(float(f.read().split()[0]) // 86400)


def rebuild():
    subprocess.run(["git", "pull", "--ff-only"], cwd=SITE_DIR, check=True, timeout=120)
    subprocess.run(["hugo", "--quiet"], cwd=SITE_DIR, check=True, timeout=120)


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/count"):
            self._json(200, {"n": bump_counter(peek="peek=1" in self.path)})
        elif self.path == "/api/uptime":
            self._json(200, {"days": uptime_days()})
        else:
            self._json(404, {"err": "not found"})

    def do_POST(self):
        if self.path != "/hook":
            return self._json(404, {"err": "not found"})
        secret = os.environ.get("HOOK_SECRET", "")
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        sig = self.headers.get("X-Hub-Signature-256", "")
        want = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not (secret and hmac.compare_digest(sig, want)):
            return self._json(403, {"err": "bad signature"})
        try:
            rebuild()
            self._json(200, {"ok": True})
        except subprocess.SubprocessError as e:
            self._json(500, {"err": str(e)})

    def log_message(self, fmt, *args):  # quiet; Caddy has the real access log
        pass


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "hits")
        assert bump_counter(path=p) == 1
        assert bump_counter(path=p) == 2
        assert bump_counter(peek=True, path=p) == 2
        assert bump_counter(path=p) == 3
    sig = "sha256=" + hmac.new(b"s", b"body", hashlib.sha256).hexdigest()
    assert hmac.compare_digest(sig, "sha256=" + hmac.new(b"s", b"body", hashlib.sha256).hexdigest())
    print("selftest ok")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        selftest()
    else:
        ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()

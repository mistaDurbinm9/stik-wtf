#!/usr/bin/env python3
"""stik.wtf node helper — the one tiny service beside Caddy.

Endpoints (Caddy proxies /hook and /api/* here, serves everything else static):
  POST /hook           GitHub push webhook -> git pull + hugo rebuild
  GET  /api/count      increment + return the hit counter ({"n": 123}); ?peek=1 reads only
  GET  /api/uptime     node uptime in days ({"days": 47})
  GET  /api/guestbook  last 200 entries, oldest first ({"entries": [...]})
  POST /api/guestbook  sign it: JSON {name, msg, website}; honeypot field "website"
                       must be empty; one post per IP per 5 minutes
  GET  /api/chat       ?since=<ts> -> {"msgs": [...], "online": n}; polling counts as
                       presence (online = IPs seen in the last 60s)
  POST /api/chat       JSON {name, msg, website}; honeypot; no URLs allowed;
                       1 msg / 10s and 30 msgs / hour per IP

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
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SITE_DIR = os.environ.get("SITE_DIR", "/srv/site")
COUNT_FILE = os.path.join(SITE_DIR, ".hits")
GB_FILE = os.environ.get("GB_FILE", "/var/lib/stik/guestbook.jsonl")
CHAT_FILE = os.environ.get("CHAT_FILE", "/var/lib/stik/chat.jsonl")
LOCK = threading.Lock()
GB_LAST_POST = {}   # ponytail: in-memory per-IP rate limits, reset on restart — fine here
CHAT_LAST = {}      # ip -> last message ts (10s gap)
CHAT_HOURLY = {}    # ip -> [count, window_start] (30/hour)
CHAT_SEEN = {}      # ip -> last poll ts, for the "online" count
URL_RE = None  # compiled lazily below


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


def gb_list(path=None):
    try:
        with open(path or GB_FILE, encoding="utf-8") as f:
            return [json.loads(line) for line in f.readlines()[-200:]]
    except FileNotFoundError:
        return []


def gb_add(name, msg, path=None):
    path = path or GB_FILE
    entry = {"name": (name or "").strip()[:40] or "anonymous",
             "msg": (msg or "").strip()[:500],
             "t": int(time.time())}
    if not entry["msg"]:
        return None
    with LOCK:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    return entry


def chat_list(since=0.0, path=None):
    try:
        with open(path or CHAT_FILE, encoding="utf-8") as f:
            msgs = [json.loads(line) for line in f.readlines()[-200:]]
        return [m for m in msgs if m["t"] > since]
    except FileNotFoundError:
        return []


def chat_add(name, msg, path=None):
    path = path or CHAT_FILE
    entry = {"name": (name or "").strip()[:24] or "anon",
             "msg": (msg or "").strip()[:300],
             "t": round(time.time(), 3)}
    if not entry["msg"]:
        return None
    with LOCK:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        # ponytail: naive rotation — rewrite when the file gets long
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 600:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.writelines(lines[-300:])
            os.replace(tmp, path)
    return entry


def uptime_seconds():
    with open("/proc/uptime") as f:
        return int(float(f.read().split()[0]))


def rebuild():
    subprocess.run(["git", "pull", "--ff-only"], cwd=SITE_DIR, check=True, timeout=120)
    subprocess.run(["hugo", "--quiet", "--minify"], cwd=SITE_DIR, check=True, timeout=120)


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _client_ip(self):
        return (self.headers.get("CF-Connecting-IP")
                or (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
                or self.client_address[0])

    def do_GET(self):
        if self.path.startswith("/api/count"):
            self._json(200, {"n": bump_counter(peek="peek=1" in self.path)})
        elif self.path == "/api/uptime":
            s = uptime_seconds()
            self._json(200, {"seconds": s, "days": s // 86400})
        elif self.path == "/api/guestbook":
            self._json(200, {"entries": gb_list()})
        elif self.path.startswith("/api/chat"):
            since = 0.0
            if "since=" in self.path:
                try:
                    since = float(self.path.split("since=")[1].split("&")[0])
                except ValueError:
                    pass
            now = time.time()
            CHAT_SEEN[self._client_ip()] = now
            online = sum(1 for t in CHAT_SEEN.values() if now - t < 60)
            self._json(200, {"msgs": chat_list(since), "online": online})
        else:
            self._json(404, {"err": "not found"})

    def do_POST(self):
        if self.path == "/api/chat":
            import re
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            except (ValueError, TypeError):
                return self._json(400, {"err": "bad json"})
            if (body.get("website") or "").strip():
                return self._json(200, {"ok": True})  # honeypot
            msg = (body.get("msg") or "").strip()
            if re.search(r"https?://|www\.", msg, re.I):
                return self._json(400, {"err": "no links in chat — the wall is for links"})
            ip = self._client_ip()
            now = time.time()
            if now - CHAT_LAST.get(ip, 0) < 10:
                return self._json(429, {"err": "slow down — one message per 10s"})
            count, start = CHAT_HOURLY.get(ip, [0, now])
            if now - start > 3600:
                count, start = 0, now
            if count >= 30:
                return self._json(429, {"err": "hourly limit hit — touch grass, come back"})
            entry = chat_add(body.get("name"), msg)
            if not entry:
                return self._json(400, {"err": "say something"})
            CHAT_LAST[ip] = now
            CHAT_HOURLY[ip] = [count + 1, start]
            return self._json(200, {"ok": True, "msg": entry})
        if self.path == "/api/guestbook":
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            except (ValueError, TypeError):
                return self._json(400, {"err": "bad json"})
            if (body.get("website") or "").strip():
                return self._json(200, {"ok": True})  # honeypot: lie politely to bots
            ip = self._client_ip()
            now = time.time()
            if now - GB_LAST_POST.get(ip, 0) < 300:
                return self._json(429, {"err": "one entry per five minutes — the book isn't going anywhere"})
            entry = gb_add(body.get("name"), body.get("msg"))
            if not entry:
                return self._json(400, {"err": "say something"})
            GB_LAST_POST[ip] = now
            return self._json(200, {"ok": True, "entry": entry})
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
    with tempfile.TemporaryDirectory() as d:
        g = os.path.join(d, "gb", "guestbook.jsonl")
        assert gb_list(path=g) == []
        assert gb_add("", "", path=g) is None                      # empty msg rejected
        e = gb_add("x" * 99, "hello " * 200, path=g)               # caps applied
        assert len(e["name"]) == 40 and len(e["msg"]) == 500
        assert gb_add(None, "hi", path=g)["name"] == "anonymous"
        assert len(gb_list(path=g)) == 2
    with tempfile.TemporaryDirectory() as d:
        c = os.path.join(d, "chat.jsonl")
        assert chat_add("", "", path=c) is None
        m1 = chat_add("x" * 50, "y" * 400, path=c)
        assert len(m1["name"]) == 24 and len(m1["msg"]) == 300
        assert chat_add(None, "hello", path=c)["name"] == "anon"
        assert len(chat_list(path=c)) == 2
        assert len(chat_list(since=m1["t"], path=c)) == 1   # only the later message
        for i in range(700):
            chat_add("r", f"rot{i}", path=c)
        assert sum(1 for _ in open(c)) <= 600               # rotation kicked in
    print("selftest ok")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        selftest()
    else:
        ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()

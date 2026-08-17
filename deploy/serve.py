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
  POST /api/apply         whitelist application; honeypot; 1 per IP per 10 min.
                          Emails the owner a capability link if SMTP_* env is set.
  GET  /api/apply/get     ?id=&t=  -> the application, only with its secret token
  POST /api/apply/decide  JSON {id, t, decision: approve|deny, note}

Email (optional — everything works without it, applications just queue up):
  SMTP_HOST (default smtp.gmail.com), SMTP_PORT (587), SMTP_USER, SMTP_PASS, MAIL_TO.
  With Gmail use an app password, and put it in the systemd unit, not in this file.

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
import re
import secrets
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SITE_DIR = os.environ.get("SITE_DIR", "/srv/site")
COUNT_FILE = os.path.join(SITE_DIR, ".hits")
GB_FILE = os.environ.get("GB_FILE", "/var/lib/stik/guestbook.jsonl")
CHAT_FILE = os.environ.get("CHAT_FILE", "/var/lib/stik/chat.jsonl")
APPS_FILE = os.environ.get("APPS_FILE", "/var/lib/stik/applications.jsonl")
POWER_FILE = os.environ.get("POWER_FILE", "/var/lib/stik/power.json")
RING_FILE = os.environ.get("RING_FILE", os.path.join(SITE_DIR, "data", "ring.json"))
SITE_URL = os.environ.get("SITE_URL", "https://stik.wtf")
LOCK = threading.Lock()
GB_LAST_POST = {}   # ponytail: in-memory per-IP rate limits, reset on restart — fine here
CHAT_LAST = {}      # ip -> last message ts (10s gap)
CHAT_HOURLY = {}    # ip -> [count, window_start] (30/hour)
CHAT_SEEN = {}      # ip -> last poll ts, for the "online" count
APPLY_LAST = {}     # ip -> last application ts (10 min gap)
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


# ---- whitelist applications ----
APP_FIELDS = ("mcname", "platform", "discord", "age", "found", "why", "experience")
APP_LIMITS = {"mcname": 32, "platform": 12, "discord": 40, "age": 12,
              "found": 120, "why": 800, "experience": 800}


def apply_add(body, path=None):
    """Validate + store one application. Returns the record, or None if unusable."""
    path = path or APPS_FILE
    rec = {k: (str(body.get(k) or "")).strip()[:APP_LIMITS[k]] for k in APP_FIELDS}
    if not rec["mcname"] or not rec["why"]:
        return None
    rec.update(id=secrets.token_hex(4), token=secrets.token_urlsafe(24),
               t=int(time.time()), status="new", note="", decided_t=0)
    with LOCK:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


def apply_all(path=None):
    try:
        with open(path or APPS_FILE, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def apply_get(app_id, token, path=None):
    for rec in apply_all(path):
        if rec["id"] == app_id and secrets.compare_digest(rec["token"], token):
            return rec
    return None


def apply_decide(app_id, token, decision, note="", path=None):
    """Rewrite the log with this application's status changed. Idempotent per decision."""
    path = path or APPS_FILE
    if decision not in ("approve", "deny"):
        return None
    with LOCK:
        recs = apply_all(path)
        hit = None
        for rec in recs:
            if rec["id"] == app_id and secrets.compare_digest(rec["token"], token):
                rec["status"] = "approved" if decision == "approve" else "denied"
                rec["note"] = (note or "").strip()[:500]
                rec["decided_t"] = int(time.time())
                hit = rec
        if hit:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                for rec in recs:
                    f.write(json.dumps(rec) + "\n")
            os.replace(tmp, path)
    return hit


def send_mail(subject, body):
    """Best-effort notification. No SMTP configured -> return False, never raise."""
    user, pw, to = (os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS"),
                    os.environ.get("MAIL_TO"))
    if not (user and pw and to):
        return False
    import smtplib
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_FROM", user)   # e.g. tyler@stik.wtf via a Gmail alias
    msg["To"] = to
    msg.set_content(body)
    try:
        host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        port = int(os.environ.get("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls()
            s.login(user, pw)
            s.send_message(msg)
        return True
    except Exception as e:                      # notification must never break the form
        print("mail failed:", e, flush=True)
        return False


def apply_email_body(rec):
    link = "%s/apply/review/?id=%s&t=%s" % (SITE_URL, rec["id"], rec["token"])
    lines = ["New whitelist application for play.stik.wtf", "",
             "Minecraft name: " + rec["mcname"],
             "Platform:       " + (rec["platform"] or "-"),
             "Discord:        " + (rec["discord"] or "-"),
             "Age:            " + (rec["age"] or "-"),
             "Found via:      " + (rec["found"] or "-"), "",
             "Why they want in:", rec["why"], ""]
    if rec["experience"]:
        lines += ["Experience / what they build:", rec["experience"], ""]
    lines += ["Review, approve or deny:", link, "",
              "(That link is the only key to this application — anyone with it can decide.)"]
    return "\n".join(lines)


# ---- the ask box: a small model, answering only from this site's own pages ----
# A 1.5B model on a 2013 Xeon invents things when left to its own memory, so it is never
# asked to know anything: the matching page text is retrieved and pasted in front of it,
# and it is told to answer from that or say it doesn't know.
BOT_URL = os.environ.get("BOT_URL", "http://192.168.1.134:8080/v1/chat/completions")
ASK_LAST = {}                      # ip -> ts, one question per 30s
ASK_COOLDOWN = 30
CHUNKS_CACHE = {"t": 0.0, "data": []}


def site_chunks(now=None):
    """Every content page as (title, url, text), refreshed every 10 minutes."""
    now = now if now is not None else time.time()
    if now - CHUNKS_CACHE["t"] < 600 and CHUNKS_CACHE["data"]:
        return CHUNKS_CACHE["data"]
    chunks = []
    root = os.path.join(SITE_DIR, "content")
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                raw = open(full, encoding="utf-8").read()
            except OSError:
                continue
            title, body = fn[:-3], raw
            if raw.startswith("---"):
                end = raw.find("---", 3)
                if end > 0:
                    front, body = raw[3:end], raw[end + 3:]
                    for line in front.splitlines():
                        if line.lower().startswith("title:"):
                            title = line.split(":", 1)[1].strip().strip('"')
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            url = "/" + rel[:-3].replace("_index", "").replace("index", "").strip("/")
            text = " ".join(body.split())
            if len(text) > 40:
                chunks.append({"title": title, "url": url.rstrip("/") + "/", "text": text[:900]})
    CHUNKS_CACHE.update(t=now, data=chunks)
    return chunks


STOPWORDS = {"the", "a", "an", "is", "are", "do", "does", "what", "how", "who", "why",
             "can", "i", "you", "your", "my", "to", "of", "on", "in", "for", "and", "it"}
# words that mean the same thing to a reader but not to a keyword scorer
SYNONYMS = {"hardware": ["xeon", "cpu", "ram", "ssd", "specs"],
            "specs": ["xeon", "cpu", "ram", "ghz"],
            "power": ["watts", "draw"],
            "join": ["whitelist", "apply"],
            "code": ["git", "forge", "repo"],
            "shop": ["store", "neoaquatics"]}


def retrieve(question, k=3, chunks=None):
    chunks = site_chunks() if chunks is None else chunks
    words = [w for w in re.findall(r"[a-z0-9]+", question.lower()) if w not in STOPWORDS]
    for w in list(words):
        words.extend(SYNONYMS.get(w, []))
    if not words or not chunks:
        return []
    scored = []
    for c in chunks:
        hay = (c["title"] + " " + c["text"]).lower()
        hits = sum(hay.count(w) for w in words)
        if not hits:
            continue
        # Coverage dominates frequency: a page touching every word of the question beats
        # a one-line update that happens to repeat a single word. ("what hardware is the
        # node" should reach the homelab page, not two changelog entries about the node.)
        coverage = sum(1 for w in words if w in hay)
        title_hits = sum(1 for w in words if w in c["title"].lower())
        scored.append((coverage * 100 + title_hits * 20 + min(hits, 20), c))
    scored.sort(key=lambda s: -s[0])
    return [c for _s, c in scored[:k]]


GREETINGS = {"hi", "hey", "hello", "yo", "sup", "howdy", "hiya", "oi", "hallo",
             "good morning", "good evening", "gm", "wsg", "whats up", "what's up"}


def demarkdown(text):
    """The model copies markdown out of the pages; the answer is prose, so flatten it."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)   # [label](url) -> label
    text = re.sub(r"[`*]", "", text)                       # bold/italic/code marks
    text = re.sub(r"^[#>\s-]+", "", text, flags=re.M)      # headings, quotes, bullets
    return " ".join(text.split())


def ask_bot(question, timeout=60):
    """Returns (answer, sources). Never raises — the box degrades to an apology."""
    import urllib.request
    plain = question.strip().strip("!?.").lower()
    if plain in GREETINGS or len(plain) < 3:
        return ("hey. I'm stik's little robot — I've read this site and nothing else. "
                "Ask me about the homelab, the minecraft server, the projects, or how to "
                "join anything.", [])
    found = retrieve(question)
    if not found:
        return ("I couldn't find a page about that — I only know what's written on this "
                "site. Try the homelab, the minecraft server, the forge, or the shop.", [])
    context = "\n\n".join("## %s (%s)\n%s" % (c["title"], c["url"], c["text"]) for c in found)
    payload = {
        "messages": [
            {"role": "system", "content":
             "You are stik's little robot: a small friendly bot on stik.wtf, a personal "
             "website. Answer the question using ONLY the page text given to you. If it "
             "isn't there, say so plainly. Be warm and casual, like a person who knows the "
             "site well. One to three sentences of plain prose — never markdown, never "
             "links, never bullet points, never repeat the page text verbatim. The reader "
             "is shown the source pages separately, so just answer in your own words."},
            {"role": "user", "content": "Pages:\n%s\n\nQuestion: %s" % (context, question)},
        ],
        "max_tokens": 120, "temperature": 0.3,
    }
    req = urllib.request.Request(BOT_URL, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        answer = demarkdown(data["choices"][0]["message"]["content"])
    except Exception as e:
        print("ask failed:", e, flush=True)
        return ("The little robot is asleep or overloaded — try again in a minute.", found)
    return (answer[:600], found)


# ---- service status ----
# Checked on the LAN, not through the tunnel: this answers "is the service up?", not
# "is Cloudflare up?". Cached so a popular page can't turn into a port-scan.
SERVICES = [
    {"key": "minecraft", "name": "minecraft", "host": "192.168.1.68", "port": 25660,
     "url": "/projects/minecraft-server/"},
    {"key": "forge", "name": "git forge", "host": "192.168.1.61", "port": 3000,
     "url": "https://git.stik.wtf"},
    {"key": "store", "name": "neoaquatics", "host": "192.168.1.70", "port": 3000,
     "url": "https://neoaquatics.com"},
    {"key": "site", "name": "this site", "host": "127.0.0.1", "port": 80, "url": "/"},
]
STATUS_CACHE = {"t": 0.0, "data": []}
STATUS_TTL = 60


def probe(host, port, timeout=1.5):
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def services_status(now=None):
    now = now if now is not None else time.time()
    if now - STATUS_CACHE["t"] < STATUS_TTL and STATUS_CACHE["data"]:
        return STATUS_CACHE["data"]
    out = [{"key": s["key"], "name": s["name"], "url": s["url"],
            "up": probe(s["host"], s["port"])} for s in SERVICES]
    STATUS_CACHE.update(t=now, data=out)
    return out


# ---- what changed: the site's own git log ----
CHANGES_CACHE = {"t": 0.0, "data": []}


def recent_changes(limit=12, now=None):
    now = now if now is not None else time.time()
    if now - CHANGES_CACHE["t"] < 300 and CHANGES_CACHE["data"]:
        return CHANGES_CACHE["data"]
    try:
        out = subprocess.run(
            ["git", "log", "-n", str(limit), "--no-merges", "--date=short",
             "--pretty=format:%h\x1f%ad\x1f%s"],
            cwd=SITE_DIR, capture_output=True, text=True, timeout=10, check=True).stdout
        rows = []
        for line in out.splitlines():
            bits = line.split("\x1f")
            if len(bits) == 3:
                rows.append({"sha": bits[0], "date": bits[1], "subject": bits[2][:120]})
        CHANGES_CACHE.update(t=now, data=rows)
        return rows
    except (subprocess.SubprocessError, OSError):
        return CHANGES_CACHE["data"]


# ---- traffic history: one bucket per day, written as the counter ticks ----
HITS_HIST = os.environ.get("HITS_HIST", "/var/lib/stik/hits-history.json")


def hits_record(total, path=None, now=None):
    """Remember the running total per day so we can show a daily-visits sparkline."""
    path = path or HITS_HIST
    now = now if now is not None else time.time()
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    with LOCK:
        try:
            with open(path, encoding="utf-8") as f:
                hist = json.load(f)
        except (FileNotFoundError, ValueError):
            hist = {}
        hist[day] = total                       # last total seen that day
        for old in sorted(hist)[:-120]:         # keep ~4 months
            hist.pop(old, None)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(hist, f)
        os.replace(tmp, path)
    return hist


def hits_series(path=None):
    """Per-day visit counts, derived from the running totals."""
    try:
        with open(path or HITS_HIST, encoding="utf-8") as f:
            hist = json.load(f)
    except (FileNotFoundError, ValueError):
        return []
    days = sorted(hist)
    series, prev = [], None
    for d in days:
        total = hist[d]
        series.append({"day": d, "visits": total if prev is None else max(0, total - prev)})
        prev = total
    return series


# ---- the shared pixel canvas ----
# 64x64 grid stored as one character per cell (index into PALETTE, '.' = empty).
# Whole board is 4KB of text, so it ships in a single response and needs no diffing.
CANVAS_FILE = os.environ.get("CANVAS_FILE", "/var/lib/stik/canvas.txt")
CANVAS_W = CANVAS_H = 64
CANVAS_COOLDOWN = 30                       # seconds between pixels, per visitor
PALETTE = ["#14120f", "#f5f2ea", "#ffffff", "#B026FF", "#6b16a3", "#ff2e88",
           "#ff6b35", "#ffd23f", "#7BBE4A", "#2f8f4e", "#00e5ff", "#2b6cb0",
           "#79553a", "#8a857b", "#c9c4b8", "#ff9ecd"]
CANVAS_LAST = {}                           # ip -> ts of last placed pixel


def canvas_read(path=None):
    try:
        with open(path or CANVAS_FILE, encoding="utf-8") as f:
            grid = f.read().strip()
        if len(grid) == CANVAS_W * CANVAS_H:
            return grid
    except FileNotFoundError:
        pass
    return "." * (CANVAS_W * CANVAS_H)


def canvas_place(x, y, colour, path=None):
    """Paint one cell. Returns the new grid, or None if the request was nonsense."""
    path = path or CANVAS_FILE
    try:
        x, y, colour = int(x), int(y), int(colour)
    except (TypeError, ValueError):
        return None
    if not (0 <= x < CANVAS_W and 0 <= y < CANVAS_H and 0 <= colour < len(PALETTE)):
        return None
    with LOCK:
        grid = canvas_read(path)
        i = y * CANVAS_W + x
        grid = grid[:i] + chr(ord("a") + colour) + grid[i + 1:]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(grid)
        os.replace(tmp, path)
    return grid


def canvas_payload(path=None):
    grid = canvas_read(path)
    return {"w": CANVAS_W, "h": CANVAS_H, "palette": PALETTE, "grid": grid,
            "placed": sum(1 for c in grid if c != "."), "cooldown": CANVAS_COOLDOWN}


# ---- the "own metal" webring ----
# Members live in the site repo (data/ring.json), so adding one is a git push like any
# other content change; only the hop itself is dynamic.
def ring_members(path=None):
    try:
        with open(path or RING_FILE, encoding="utf-8") as f:
            return json.load(f).get("members", [])
    except (FileNotFoundError, ValueError, AttributeError):
        return []


def ring_hop(slug, direction, members=None):
    """Where does <slug> go when it hops <direction>? None if we don't know them."""
    members = ring_members() if members is None else members
    urls = [m.get("url") for m in members if m.get("url")]
    slugs = [m.get("slug") for m in members if m.get("url")]
    if not urls or slug not in slugs:
        return None
    i = slugs.index(slug)
    if direction == "next":
        return urls[(i + 1) % len(urls)]
    if direction in ("prev", "previous"):
        return urls[(i - 1) % len(urls)]
    if direction == "random":
        if len(urls) == 1:
            return urls[0]
        pick = i
        while pick == i:                      # never bounce someone back to themselves
            pick = secrets.randbelow(len(urls))
        return urls[pick]
    return None


# ---- power metering ----
# Sources push watts here; we integrate them into kWh. A sample only counts toward
# energy if the previous one is recent (<5 min), so downtime never invents usage.
def power_state(path=None):
    try:
        with open(path or POWER_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {"sources": {}, "kwh": 0.0, "since": int(time.time())}


def power_push(source, watts, detail=None, path=None, now=None):
    path = path or POWER_FILE
    now = now if now is not None else time.time()
    try:
        watts = float(watts)
    except (TypeError, ValueError):
        return None
    if not (0 <= watts < 5000):          # a home rig is not a data centre
        return None
    with LOCK:
        st = power_state(path)
        prev = st["sources"].get(source)
        if prev and 0 < now - prev["t"] < 300:
            dt_h = (now - prev["t"]) / 3600.0
            avg = (prev["watts"] + watts) / 2.0        # trapezoid: kinder to spikes
            st["kwh"] = round(st["kwh"] + avg * dt_h / 1000.0, 6)
        st["sources"][source] = {"watts": round(watts, 1), "t": now,
                                 "detail": detail or {}}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f)
        os.replace(tmp, path)
    return st


def power_report(path=None, now=None):
    """What the footer shows: live sources (stale ones dropped) and total energy."""
    now = now if now is not None else time.time()
    st = power_state(path)
    live, total = {}, 0.0
    for name, s in st["sources"].items():
        if now - s["t"] < 300:                          # quiet for 5 min = powered off
            live[name] = {"watts": s["watts"], "detail": s.get("detail", {})}
            total += s["watts"]
    return {"sources": live, "watts": round(total, 1),
            "kwh": round(st["kwh"], 3), "since": st["since"]}


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

    def _redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Cache-Control", "no-store")   # the ring must never go stale
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _client_ip(self):
        return (self.headers.get("CF-Connecting-IP")
                or (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
                or self.client_address[0])

    def do_GET(self):
        if self.path.startswith("/ring/"):
            parts = [p for p in self.path.split("?")[0].strip("/").split("/") if p]
            # /ring/<slug>/<next|prev|previous|random>
            if len(parts) == 3:
                dest = ring_hop(parts[1], parts[2])
                if dest:
                    return self._redirect(dest)
            return self._redirect(SITE_URL + "/ring/")     # lost hops land on the index
        if self.path == "/api/canvas":
            payload = canvas_payload()
            payload["wait"] = max(0, int(CANVAS_COOLDOWN - (time.time() - CANVAS_LAST.get(self._client_ip(), 0))))
            return self._json(200, payload)
        if self.path == "/api/status":
            return self._json(200, {"services": services_status(),
                                    "changes": recent_changes(),
                                    "hits": hits_series()})
        if self.path.startswith("/api/count"):
            n = bump_counter(peek="peek=1" in self.path)
            if "peek=1" not in self.path:
                try:
                    hits_record(n)
                except OSError:
                    pass
            self._json(200, {"n": n})
        elif self.path == "/api/uptime":
            s = uptime_seconds()
            self._json(200, {"seconds": s, "days": s // 86400, "power": power_report()})
        elif self.path == "/api/guestbook":
            self._json(200, {"entries": gb_list()})
        elif self.path.startswith("/api/apply/get"):
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query)
            rec = apply_get((q.get("id") or [""])[0], (q.get("t") or [""])[0])
            if not rec:
                return self._json(404, {"err": "no such application"})
            safe = {k: rec[k] for k in APP_FIELDS}
            safe.update(id=rec["id"], t=rec["t"], status=rec["status"],
                        note=rec["note"], decided_t=rec["decided_t"])
            self._json(200, safe)
        elif self.path.startswith("/api/chat"):
            since = 0.0
            if "since=" in self.path:
                try:
                    since = float(self.path.split("since=")[1].split("&")[0])
                except ValueError:
                    pass
            now = time.time()
            if "since=" in self.path:  # only chat-page pollers count as present
                CHAT_SEEN[self._client_ip()] = now
            online = sum(1 for t in CHAT_SEEN.values() if now - t < 60)
            self._json(200, {"msgs": chat_list(since), "online": online})
        else:
            self._json(404, {"err": "not found"})

    def do_POST(self):
        if self.path == "/api/ask":
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            except (ValueError, TypeError):
                return self._json(400, {"err": "bad json"})
            q = (body.get("q") or "").strip()[:300]
            if not q:
                return self._json(400, {"err": "say something"})
            ip = self._client_ip()
            now = time.time()
            wait = ASK_COOLDOWN - (now - ASK_LAST.get(ip, 0))
            if wait > 0:
                return self._json(429, {"err": "one question per %ds — it thinks slowly" % ASK_COOLDOWN})
            answer, sources = ask_bot(q)
            if sources:                      # only real model calls cost a cooldown
                ASK_LAST[ip] = now
            return self._json(200, {"answer": answer,
                                    "sources": [{"title": s["title"], "url": s["url"]} for s in sources]})
        if self.path == "/api/canvas":
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            except (ValueError, TypeError):
                return self._json(400, {"err": "bad json"})
            ip = self._client_ip()
            now = time.time()
            wait = CANVAS_COOLDOWN - (now - CANVAS_LAST.get(ip, 0))
            if wait > 0:
                return self._json(429, {"err": "wait %ds" % int(wait + 1), "wait": int(wait + 1)})
            if canvas_place(body.get("x"), body.get("y"), body.get("c")) is None:
                return self._json(400, {"err": "off the board"})
            CANVAS_LAST[ip] = now
            payload = canvas_payload()
            payload["wait"] = CANVAS_COOLDOWN
            return self._json(200, payload)
        if self.path == "/api/power":
            secret = os.environ.get("POWER_TOKEN", "")
            given = self.headers.get("X-Power-Token", "")
            if not (secret and hmac.compare_digest(given, secret)):
                return self._json(403, {"err": "bad power token"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            except (ValueError, TypeError):
                return self._json(400, {"err": "bad json"})
            src = (body.get("source") or "").strip()[:16]
            if not src or power_push(src, body.get("watts"), body.get("detail")) is None:
                return self._json(400, {"err": "need source and a plausible watts"})
            return self._json(200, {"ok": True, "power": power_report()})
        if self.path == "/api/apply":
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            except (ValueError, TypeError):
                return self._json(400, {"err": "bad json"})
            if (body.get("website") or "").strip():
                return self._json(200, {"ok": True})        # honeypot
            ip = self._client_ip()
            now = time.time()
            if now - APPLY_LAST.get(ip, 0) < 600:
                return self._json(429, {"err": "one application per 10 minutes — I only need the one"})
            rec = apply_add(body)
            if not rec:
                return self._json(400, {"err": "minecraft name and a reason are both required"})
            APPLY_LAST[ip] = now
            mailed = send_mail("whitelist application: " + rec["mcname"], apply_email_body(rec))
            print("application %s from %s (mailed=%s)" % (rec["id"], rec["mcname"], mailed), flush=True)
            return self._json(200, {"ok": True, "queued": True})
        if self.path == "/api/apply/decide":
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            except (ValueError, TypeError):
                return self._json(400, {"err": "bad json"})
            rec = apply_decide(body.get("id", ""), body.get("t", ""),
                               body.get("decision", ""), body.get("note", ""))
            if not rec:
                return self._json(404, {"err": "no such application, or bad decision"})
            return self._json(200, {"ok": True, "status": rec["status"], "mcname": rec["mcname"]})
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
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "apps.jsonl")
        assert apply_add({"mcname": "x"}, path=a) is None          # reason required
        assert apply_add({"why": "hi"}, path=a) is None            # name required
        r1 = apply_add({"mcname": "notch", "why": "build things", "platform": "java"}, path=a)
        r2 = apply_add({"mcname": "steve", "why": "mine things"}, path=a)
        assert r1["status"] == "new" and r1["id"] != r2["id"] and r1["token"] != r2["token"]
        assert apply_get(r1["id"], r1["token"], path=a)["mcname"] == "notch"
        assert apply_get(r1["id"], "wrong-token", path=a) is None  # token is the key
        assert apply_get("nope", r1["token"], path=a) is None
        assert apply_decide(r1["id"], r1["token"], "sideways", path=a) is None
        ok = apply_decide(r1["id"], r1["token"], "approve", note="seems fine", path=a)
        assert ok["status"] == "approved" and ok["note"] == "seems fine"
        assert apply_get(r1["id"], r1["token"], path=a)["status"] == "approved"
        assert apply_get(r2["id"], r2["token"], path=a)["status"] == "new"  # untouched
        assert len(apply_all(path=a)) == 2                          # rewrite kept both
        assert "/apply/review/?id=" in apply_email_body(r1)
        assert send_mail("x", "y") is False                         # no SMTP env -> no crash
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "power.json")
        t0 = 1_000_000.0
        assert power_push("node", "not-a-number", path=p) is None
        assert power_push("node", 99999, path=p) is None             # implausible, rejected
        power_push("node", 100, path=p, now=t0)
        assert power_report(path=p, now=t0)["kwh"] == 0.0            # first sample: no span
        for i in range(1, 61):                                       # 60 pushes, 60s apart
            power_push("node", 100, path=p, now=t0 + 60 * i)
        now = t0 + 3600
        r = power_report(path=p, now=now)
        assert abs(r["kwh"] - 0.1) < 1e-6, r                         # an hour at 100W = 0.1 kWh
        assert r["sources"]["node"]["watts"] == 100 and r["watts"] == 100
        gap = now + 99999                                            # node was off for a day
        power_push("node", 100, path=p, now=gap)
        assert abs(power_report(path=p, now=gap)["kwh"] - 0.1) < 1e-6  # gap adds nothing
        power_push("pc", 300, path=p, now=gap)
        assert power_report(path=p, now=gap)["watts"] == 400         # both live, summed
        stale = power_report(path=p, now=gap + 600)                  # 10 min of silence
        assert stale["sources"] == {} and stale["watts"] == 0        # powered off, honestly
        assert abs(stale["kwh"] - 0.1) < 1e-6                        # energy total survives
    ring = [{"slug": "a", "url": "https://a.example"},
            {"slug": "b", "url": "https://b.example"},
            {"slug": "c", "url": "https://c.example"}]
    assert ring_hop("a", "next", ring) == "https://b.example"
    assert ring_hop("c", "next", ring) == "https://a.example"        # wraps forward
    assert ring_hop("a", "prev", ring) == "https://c.example"        # wraps backward
    assert ring_hop("a", "previous", ring) == "https://c.example"    # both spellings
    assert ring_hop("a", "random", ring) != "https://a.example"      # never yourself
    assert ring_hop("nobody", "next", ring) is None                  # strangers get the index
    assert ring_hop("a", "sideways", ring) is None
    assert ring_hop("a", "next", []) is None                         # empty ring
    solo = [{"slug": "a", "url": "https://a.example"}]
    assert ring_hop("a", "next", solo) == "https://a.example"        # a ring of one
    assert ring_hop("a", "random", solo) == "https://a.example"      # ...doesn't hang
    assert isinstance(ring_members(path="/nonexistent/ring.json"), list)
    with tempfile.TemporaryDirectory() as d:
        cv = os.path.join(d, "canvas.txt")
        blank = canvas_read(cv)
        assert len(blank) == CANVAS_W * CANVAS_H and set(blank) == {"."}
        assert canvas_place(-1, 0, 0, path=cv) is None                 # off the board
        assert canvas_place(0, CANVAS_H, 0, path=cv) is None
        assert canvas_place(0, 0, len(PALETTE), path=cv) is None       # no such colour
        assert canvas_place("x", 0, 0, path=cv) is None
        g = canvas_place(0, 0, 3, path=cv)
        assert g[0] == "d" and canvas_payload(cv)["placed"] == 1       # colour 3 -> 'd'
        g = canvas_place(63, 63, 0, path=cv)
        assert g[-1] == "a" and canvas_payload(cv)["placed"] == 2
        canvas_place(0, 0, 5, path=cv)                                 # overwrite, not add
        assert canvas_payload(cv)["placed"] == 2
        assert len(canvas_read(cv)) == CANVAS_W * CANVAS_H             # size never drifts
    with tempfile.TemporaryDirectory() as d:
        hh = os.path.join(d, "hits.json")
        base = 1_700_000_000
        day = 86400
        hits_record(10, path=hh, now=base)                             # day 1 ends at 10
        hits_record(30, path=hh, now=base + day)                       # day 2 ends at 30
        hits_record(45, path=hh, now=base + 2 * day)
        s = hits_series(hh)
        assert [r["visits"] for r in s] == [10, 20, 15], s             # deltas, not totals
        assert hits_series("/nonexistent.json") == []
        for i in range(200):                                           # pruning holds
            hits_record(i, path=hh, now=base + i * day)
        assert len(hits_series(hh)) <= 120
    print("selftest ok")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        selftest()
    else:
        ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()

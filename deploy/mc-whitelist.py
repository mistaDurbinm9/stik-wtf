#!/usr/bin/env python3
"""Whitelist approved applicants, from inside the Minecraft container.

Runs on CT 901. Pulls the approved-names list from stik.wtf over the public internet
(which this container can already reach) and applies it through RCON on its own
localhost. The web container is never allowed to talk to the game server:

    CT 902 (public web)  <--- pulled by ---  CT 901 (game)  --- localhost --->  RCON

That direction matters. If the public-facing box were ever compromised, the worst it
could do is get somebody whitelisted; it can't reach the game console at all. The
container's firewall (inbound drop, no LAN egress) stays exactly as it was.

Config: /etc/mc-whitelist.env  ->  QUEUE_URL, ADMIN_TOKEN, RCON_PASS
State:  /var/lib/mc-whitelist-done  (names already added, so logs stay quiet)
Test:   mc-whitelist.py --once --print
"""
import json
import os
import re
import socket
import struct
import sys
import urllib.request

QUEUE_URL = os.environ.get("QUEUE_URL", "https://stik.wtf/api/whitelist-queue")
TOKEN = os.environ.get("ADMIN_TOKEN", "")
RCON_HOST = os.environ.get("RCON_HOST", "127.0.0.1")
RCON_PORT = int(os.environ.get("RCON_PORT", "25575"))
RCON_PASS = os.environ.get("RCON_PASS", "")
DONE_FILE = os.environ.get("DONE_FILE", "/var/lib/mc-whitelist-done")
MCNAME = re.compile(r"[A-Za-z0-9_]{2,16}$")


def rcon(command, timeout=6):
    """Source RCON: length, request id, type, body, two nulls. 3 = login, 2 = command."""
    def pack(rid, rtype, body):
        payload = struct.pack("<ii", rid, rtype) + body.encode("utf8") + b"\x00\x00"
        return struct.pack("<i", len(payload)) + payload

    def read(sock):
        head = sock.recv(4)
        if len(head) < 4:
            return (None, "")
        size = struct.unpack("<i", head)[0]
        data = b""
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                break
            data += chunk
        rid, _type = struct.unpack("<ii", data[:8])
        return (rid, data[8:-2].decode("utf8", "replace"))

    with socket.create_connection((RCON_HOST, RCON_PORT), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(pack(1, 3, RCON_PASS))
        rid, _ = read(s)
        if rid == -1 or rid is None:
            raise RuntimeError("rcon auth rejected")
        s.sendall(pack(2, 2, command))
        _rid, body = read(s)
        return body.strip()


def done_names():
    try:
        return {l.strip() for l in open(DONE_FILE, encoding="utf-8") if l.strip()}
    except FileNotFoundError:
        return set()


def mark_done(name):
    os.makedirs(os.path.dirname(DONE_FILE), exist_ok=True)
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(name + "\n")


def main():
    verbose = "--print" in sys.argv
    if not (TOKEN and RCON_PASS):
        print("ADMIN_TOKEN/RCON_PASS not set", file=sys.stderr)
        return 1
    req = urllib.request.Request(QUEUE_URL + "?t=" + TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            names = json.load(r).get("names", [])
    except Exception as e:
        print("queue unreachable:", e, file=sys.stderr)
        return 1

    already = done_names()
    todo = [n for n in names if MCNAME.match(n) and n not in already]
    if verbose:
        print("approved: %d, new: %d" % (len(names), len(todo)))
    for name in todo:
        try:
            said = rcon("whitelist add %s" % name)
        except Exception as e:
            print("rcon failed for %s: %s" % (name, e), file=sys.stderr)
            return 1
        print("whitelisted %s: %s" % (name, said), flush=True)
        mark_done(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

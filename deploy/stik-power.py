#!/usr/bin/env python3
"""Sample the node's power draw from RAPL and push it to stik.wtf's helper.

Runs on the PROXMOX HOST (not in a container) — RAPL lives in the host's sysfs.
Reports package + DRAM energy for every CPU socket, which on this box is the large
majority of the draw. It is not a wall measurement: drives, fans, the board itself and
PSU losses are not included, so the site labels it "cpu+ram".

Install:
  cp stik-power.py /usr/local/bin/ && chmod +x /usr/local/bin/stik-power.py
  # /etc/stik-power.env  (0600):  POWER_TOKEN=...   PUSH_URL=http://<ct902-ip>/api/power
  systemd timer every 60s — see deploy/DEPLOY.md
Test:  stik-power.py --once --print
"""
import glob
import json
import os
import sys
import time
import urllib.request

SAMPLE_SECONDS = 2.0


def read_energy():
    """Every RAPL domain we care about: per-socket package totals and their DRAM."""
    out = {}
    for sock in sorted(glob.glob("/sys/class/powercap/intel-rapl:[0-9]")):
        try:
            name = open(os.path.join(sock, "name")).read().strip()      # package-N
            out[name] = int(open(os.path.join(sock, "energy_uj")).read())
            for sub in sorted(glob.glob(os.path.join(sock, "intel-rapl:*"))):
                sub_name = open(os.path.join(sub, "name")).read().strip()
                if sub_name == "dram":                                   # cores are inside package
                    out[name + "-dram"] = int(open(os.path.join(sub, "energy_uj")).read())
        except (OSError, ValueError):
            continue
    return out


def sample_watts(seconds=SAMPLE_SECONDS):
    a = read_energy()
    time.sleep(seconds)
    b = read_energy()
    detail, total = {}, 0.0
    for k in a:
        if k not in b:
            continue
        delta = b[k] - a[k]
        if delta < 0:              # 32/64-bit counter wrapped; skip this round
            continue
        w = delta / 1e6 / seconds
        detail[k] = round(w, 1)
        total += w
    return round(total, 1), detail


def main():
    watts, detail = sample_watts()
    if "--print" in sys.argv:
        for k in sorted(detail):
            print("%-18s %6.1f W" % (k, detail[k]))
        print("%-18s %6.1f W" % ("TOTAL (cpu+ram)", watts))
    url = os.environ.get("PUSH_URL")
    token = os.environ.get("POWER_TOKEN")
    if not (url and token):
        print("PUSH_URL/POWER_TOKEN unset — measured only", file=sys.stderr)
        return 0 if watts else 1
    body = json.dumps({"source": "node", "watts": watts, "detail": detail}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "X-Power-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            if "--print" in sys.argv:
                print("pushed:", r.status)
    except Exception as e:
        print("push failed:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Give approved applicants their roles and a welcome DM, once they join the Discord.

Runs on CT 902 beside the site (it reads the applications file directly). Every minute it
looks for approved applications whose Discord handle now belongs to a member of the guild,
grants them Whitelisted plus Java and/or Bedrock to match what they said on the form, and
sends them a DM.

Why polling and not a gateway bot: a bot cannot DM anyone who doesn't already share a
server with it, so the DM can only happen after they join anyway. Polling the member list
does the same job with a systemd timer instead of a daemon holding a websocket open.

Config: /etc/discord-agent.env  ->  DISCORD_TOKEN, GUILD_ID, ROLE_*, INVITE_URL
State:  /var/lib/stik/discord-done  (application ids already handled)
Test:   discord-agent.py --dry-run     (matches and reports, changes nothing)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://discord.com/api/v10"
TOKEN = os.environ.get("DISCORD_TOKEN", "")
GUILD_ID = os.environ.get("GUILD_ID", "")
ROLE_WHITELISTED = os.environ.get("ROLE_WHITELISTED", "")
ROLE_JAVA = os.environ.get("ROLE_JAVA", "")
ROLE_BEDROCK = os.environ.get("ROLE_BEDROCK", "")
APPS_FILE = os.environ.get("APPS_FILE", "/var/lib/stik/applications.jsonl")
DONE_FILE = os.environ.get("DISCORD_DONE", "/var/lib/stik/discord-done")
MC_HOST = os.environ.get("MC_HOST", "play.stik.wtf")


def api(path, method="GET", body=None):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bot " + TOKEN,
                 "Content-Type": "application/json",
                 "User-Agent": "DiscordBot (https://stik.wtf, 1.0)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def all_members():
    """Every member, 1000 at a time. Small server, so this is cheap."""
    out, after = [], "0"
    while True:
        page = api("/guilds/%s/members?limit=1000&after=%s" % (GUILD_ID, after))
        if not page:
            break
        out.extend(page)
        if len(page) < 1000:
            break
        after = page[-1]["user"]["id"]
    return out


def normalise(handle):
    """'@Name', 'Name#1234', ' name ' all reduce to the same lookup key."""
    h = (handle or "").strip().lstrip("@").lower()
    return h.split("#")[0].strip()


def find_member(handle, members):
    want = normalise(handle)
    if not want:
        return None
    for m in members:
        u = m.get("user", {})
        names = {(u.get("username") or "").lower(),
                 (u.get("global_name") or "").lower(),
                 (m.get("nick") or "").lower()}
        if want in {n for n in names if n}:
            return m
    return None


def done_ids():
    try:
        return {l.strip() for l in open(DONE_FILE, encoding="utf-8") if l.strip()}
    except FileNotFoundError:
        return set()


def mark_done(app_id):
    os.makedirs(os.path.dirname(DONE_FILE), exist_ok=True)
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(app_id + "\n")


def roles_for(platform):
    want = [ROLE_WHITELISTED]
    p = (platform or "").lower()
    if p in ("java", "both", ""):
        want.append(ROLE_JAVA)
    if p in ("bedrock", "both"):
        want.append(ROLE_BEDROCK)
    return [r for r in want if r]


def welcome_text(rec):
    return ("you're in.\n\n"
            "**%s** is whitelisted on **%s** — hop on whenever.\n"
            "I've given you the roles for your channels in here too.\n\n"
            "It's a small vanilla+ world, Java and Bedrock together. Say hi in chat.\n"
            "— stik (https://stik.wtf)" % (rec.get("mcname", "you"), MC_HOST))


def main():
    dry = "--dry-run" in sys.argv
    if not (TOKEN and GUILD_ID and ROLE_WHITELISTED):
        print("DISCORD_TOKEN / GUILD_ID / ROLE_WHITELISTED not set", file=sys.stderr)
        return 1
    try:
        apps = [json.loads(l) for l in open(APPS_FILE, encoding="utf-8") if l.strip()]
    except FileNotFoundError:
        apps = []
    already = done_ids()
    pending = [a for a in apps
               if a.get("status") == "approved" and a.get("discord")
               and a.get("id") not in already]
    if not pending:
        if dry:
            print("nothing pending")
        return 0

    members = all_members()
    print("pending: %d, guild members: %d" % (len(pending), len(members)))

    for rec in pending:
        member = find_member(rec["discord"], members)
        if not member:
            print("  %s (%s): not in the server yet, will retry"
                  % (rec["mcname"], rec["discord"]))
            continue
        uid = member["user"]["id"]
        want = [r for r in roles_for(rec.get("platform")) if r not in member.get("roles", [])]
        if dry:
            print("  %s (%s): would add %d role(s) and DM user %s"
                  % (rec["mcname"], rec["discord"], len(want), uid))
            continue
        for role in want:
            try:
                api("/guilds/%s/members/%s/roles/%s" % (GUILD_ID, uid, role), method="PUT")
                time.sleep(0.4)                       # be gentle with the rate limit
            except urllib.error.HTTPError as e:
                print("  role %s failed for %s: %s" % (role, rec["mcname"], e), file=sys.stderr)
        try:
            channel = api("/users/@me/channels", method="POST", body={"recipient_id": uid})
            api("/channels/%s/messages" % channel["id"], method="POST",
                body={"content": welcome_text(rec)})
            print("  %s: roles granted, welcome sent" % rec["mcname"])
        except urllib.error.HTTPError as e:
            # DMs closed is common and not an error worth retrying forever
            print("  %s: roles granted, DM refused (%s)" % (rec["mcname"], e), file=sys.stderr)
        mark_done(rec["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

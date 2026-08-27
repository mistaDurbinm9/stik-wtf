# stik.wtf — handoff

Written 2026-08-20 at the end of the build sessions. Everything below is live unless it
says otherwise. `SITE_PLAN.md` is what the site is for, `DESIGN.md` is how it looks,
`deploy/DEPLOY.md` is how it runs. This file is the map.

## What this is

Tyler's personal site. Hugo + hand-written CSS, no framework, ~22KB a page, served from
his own Proxmox node at home through a Cloudflare tunnel. The whole point is that he owns
the machine: the site, a Minecraft server, a git forge, a storefront and a small language
model all run on one dual-Xeon box in his house.

**Publishing is a git push.** Push to GitHub master and a webhook rebuilds the live site
in ~15 seconds. Never edit files on the server.

## Working on it

```sh
git clone https://github.com/mistaDurbinm9/stik-wtf     # or git.stik.wtf/stik/stik-wtf
hugo server                                              # local preview
git push                                                 # deploys in ~15s
git push forge master                                    # mirror to his own forge
```

Content is markdown under `content/`. Adding an update = one new file in
`content/updates/` with `project:` frontmatter naming a project slug; the Now page and the
home page pick it up automatically. Adding a page sprite = `sprite: <name>` in frontmatter,
where the name matches a partial in `layouts/partials/sprites/`.

## The shape of it

| Path | What it is |
| --- | --- |
| `/` | hero, project cards, latest updates, chat teaser |
| `/projects/*` | one page per project: AI workspace, Minecraft, homelab, neoaquatics |
| `/now/` | auto-composed from update entries; never hand-maintained |
| `/apply/` | Minecraft whitelist application → email → `/apply/review/?id=&t=` |
| `/chat/` | shoutbox (human to human), polling, presence count |
| `/canvas/` | shared 64×64 pixel board, one pixel per visitor per 30s |
| `/guestbook/`, `/wall/`, `/ring/` | old-web furniture: signing, 88x31 buttons, his own webring |
| `/status/` | live service probes, visits sparkline, git changelog |
| `/asked/?t=<ADMIN_TOKEN>` | private: what people asked the bot |

## The one moving part

`deploy/serve.py` on CT 902 is the only dynamic service — webhook rebuild, hit counter,
uptime, guestbook, shoutbox, canvas, applications, power, webring hops, the ask box.
Plain stdlib Python, one file, with a `--selftest` that must stay green:

```sh
python deploy/serve.py --selftest      # run before every serve.py change
```

Storage is flat files in `/var/lib/stik/`. There is no database and doesn't need to be.

## Things that will bite you

- **Cloudflare 403s the default `Python-urllib` user agent.** Any script fetching
  stik.wtf must set its own `User-Agent`. This cost a debugging round once already.
- **CT 900 is Outis, the AI workspace. Do not touch it.** The site's own model lives in
  CT 906.
- **CT 901 (Minecraft) is firewalled on purpose** — inbound dropped except game ports, no
  LAN egress at all. Never route into it. The whitelist agent there *pulls* from the site
  and uses its own localhost RCON, so a compromise of the public web box can at worst
  whitelist someone rather than reach a console.
- **llama.cpp on this node needs `-DGGML_BMI2=OFF`.** The Xeon E5-2690 v2 has AVX and
  F16C but no BMI2/AVX2; the default build dies with SIGILL.
- **`[hidden]` needs `display: none !important`** in this stylesheet, because `.card` and
  `.gb-form` set `display` and would otherwise beat the attribute.
- **Fixed overlays must be `pointer-events: none`** except their controls. The ask dock
  once owned the bottom 78px of phone screens and ate taps meant for form fields.
- **Only `a.card` and `.btn` press on `:active`.** Container cards that merely hold a form
  must not move, or long-press text selection breaks on touch.
- Forgejo theme edits need the `?b=N` cache-buster bumped — see `deploy/forgejo/README.md`.

## Automation that runs itself

- Approving an application whitelists the player within 60s and, if they're in the Discord,
  grants their roles and DMs them.
- Node and workstation push power readings every minute; the footer shows live watts and a
  running kWh total.
- The forge mirrors to GitHub; the site rebuilds on push.

## What's left

- **Content is the gap.** The update log is the one thing that only Tyler can write, and
  it's the first thing to rot. Project pages could use screenshots — there are still no
  images on the site at all.
- Contact page has no YouTube link yet (he edits gaming montages; the channel is
  @SleepDeprived-adjacent — ask him).
- The `own metal` webring has one member: him. It grows by inviting self-hosters.
- Pending: XXIIVV webring PR #1127, a reply from astrid (insect.christmas), shring
  membership (email drafted, may not be sent).
- Possible next: a media corner for his montages, badge wall growth as trades come in.

## Tone

Read `content/about.md` before writing any copy. Lowercase-ish, dry, specific, no
marketing voice, no em-dash-heavy AI cadence. He notices. Numbers and real details beat
adjectives: "384GB of DDR3, ~70W of it just remembering things" is the register.

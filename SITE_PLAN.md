# stik.wtf — Site Plan

*Living document. Drafted 2026-08-14 from the first planning session; the author greenlit
building the same day. Design specifics live in [DESIGN.md](DESIGN.md) — the portable
design system other projects point at.*

## Audience & message

Everyone shows up: friends/community, people who found a project (the Minecraft server, the
AI workspace, the store) and want to know who's behind it, future employers/clients, and
potential collaborators.

**The one takeaway for all of them: "I build real things."** The projects are the message —
self-hosted, running, visible. The site's job is to show them, not talk about them.
Personality is welcome but rides on top ("playful on a clean base").

## Content model

Everything is markdown files with frontmatter. No content in templates, no database.

Launch sections:

- **Home** — who this is, what's running right now, where to go.
- **About** — written once, touched rarely.
- **Projects** — the core. First-class page per project. At launch:
  - AI workspace (the main software project; future ai.stik.wtf — page exists before the
    service is public)
  - Minecraft server (play.stik.wtf — live and joinable)
  - The homelab / Proxmox node itself (the infrastructure running everything is itself
    proof-of-work)
  - neoaquatics.com (described and linked here; it remains its own project/tenant — this
    site never reads from its repo)
- **Now** — auto-composed from the most recent update-log entries across all projects, plus
  a one-line blurb. Not hand-maintained; it can never be "forgotten."
- **Contact / links** — how to reach the author, plus everywhere else they exist.

A **project page** = frontmatter (`title`, `status` one-liner, `links`) + a short description
body + a dated **update log** (one small markdown file per entry) + optional media.

Content layout (decided at build time, 2026-08-14 — updates are one flat folder, tied to
their project by a `project:` frontmatter key; flatter than the original sketch and simpler
for both Hugo queries and the Sveltia admin):

    content/
      about.md
      contact.md
      now.md
      projects/<slug>.md                    # status, links, summary, description
      updates/YYYY-MM-DD-<slug>.md          # short dated entry; frontmatter: project: <slug>

**Built for weekly-ish bursts.** An update is one tiny markdown file ("got Geyser working").
The Now page and project pages surface the newest entries; during quiet stretches they show
recent milestones without any "last updated N days ago" framing — quiet reads as calm, not
abandoned.

Explicitly deferred (YAGNI until the itch is real): a writing/blog section, non-code
interest pages. The update log may grow into a blog naturally; don't pre-build one.

## Update workflow

Three ways to publish, all ending in a git commit to the content repo:

1. **Admin UI** — Sveltia CMS at `stik.wtf/admin`: log in with GitHub, edit/add entries and
   upload images in a form UI, save → commits to the repo. Works on phone (nice-to-have,
   covered for free).
2. **Tell Claude** — content is markdown in git, so Claude Code can write an update entry
   and push it. No extra tooling needed.
3. **Any editor + git push** — always works, nothing to be up.

Publish path: push to GitHub → webhook pings the container → `git pull && hugo` → live in
well under a minute. Media uploads land in the repo; Hugo's image processing resizes at
build time.

## Design direction

**Neobrutalist base, retro easter eggs.** ("Old-web design with modern flow.")

- Thick borders, hard offset shadows, visible boxes/structure, one loud accent color,
  honest typography, clean responsive grid.
- Both light and dark from day one, following system preference.
- Personality lives in details: microcopy, small touches — employer-safe at a glance.
- Post-launch easter eggs from the web-revival end: an 88x31 badge wall, a guestbook-style
  page. Genuine artifacts, used sparingly.
- Hand-written CSS. No framework — the aesthetic is simple boxes and the site is small.
- Open: accent color (author picks during build).

## Stack (decided)

- **Hugo** (extended, single Go binary) — static site generator. Zero runtime dependencies,
  builds in milliseconds, will still run in a decade. Templates + image processing built in.
- **Content repo on GitHub** — this repo, pushed to a remote. (Open: public vs private —
  public shows the work.)
- **Sveltia CMS** — static JS admin at `/admin` committing to the GitHub repo; media uploads
  included. Its GitHub OAuth handled by a tiny Cloudflare Worker (standard, boring pattern;
  we're on Cloudflare already).
- **The container**: small LXC on the Proxmox node — Caddy (or nginx) serving Hugo's
  `public/`, plus a ~20-line webhook listener (or a cron `git pull`) that rebuilds on push.
- **Cloudflare Tunnel** from the container → apex + `www`, orange-cloud. Zero inbound ports.
  `play.stik.wtf` untouched, ever. No DNS changes without the author. Container specs and
  tunnel connector decided with the author at deploy time (per CLAUDE.md).

Why this over the alternatives considered: Grav (one-container PHP CMS) is simpler on day
one but runs a live PHP admin to patch and secure forever, and its git story is bolted on;
Eleventy + hosted Pages CMS rots with npm and depends on a third-party service. Static
output + files-in-git is the boring, durable choice and makes the "tell Claude" path native.

## Build order

**v1 — small and launchable:**

1. Hugo skeleton: base layout, light+dark themes, Home, About, Contact.
2. Project content model + the four project pages (status, links, description, 1–2 seed
   update entries each).
3. Now page aggregating recent updates.
4. Deploy: container on the node, Caddy + tunnel, webhook rebuild. Live at apex + www.

**v1.x — same-week follow-ups:**

5. ~~Interactivity layer~~ **shipped 2026-08-14**: pixel-sprite system (hover spark, click
   burst, ambient fish, `wtf` summons a school — rules in DESIGN.md), live Minecraft status
   widget with copy-IP (client-side via api.mcsrvstat.us for now — optionally swap to a
   self-hosted ping endpoint on the node at deploy), 404 page, pixel favicon.
6. Sveltia admin + OAuth worker (the site launches without it; git and Claude paths work
   from day one).
7. Media polish: image pipeline, first screenshots/clips on project pages.

**Later, when earned:**

8. Retro easter eggs: badge wall, guestbook-style page, a REAL hit counter (needs a tiny
   endpoint on the node — pairs naturally with the deploy-time webhook listener), maybe a
   footer uptime line fed by the node.
9. Writing section — only if update entries start wanting to be essays.

## Standing rules (from CLAUDE.md, restated so this doc is self-contained)

- Never touch `play.stik.wtf` DNS. No DNS changes without the author.
- Separate from Outis and neoaquatics — same node, different tenant.
- Content stays editable without touching layout code, forever.

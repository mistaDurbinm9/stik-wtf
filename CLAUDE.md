# stik.wtf — the author's personal site

**Status: BEING DEFINED.** No stack, no design, no code yet — deliberately. The first planning
session produces `SITE_PLAN.md` (the living plan); until that exists, there is nothing to build.
Do not scaffold a framework before the plan says which one and why.

## Purpose, in the author's own framing (2026-08-14)

A place for people to learn about the author: who they are, the projects they build (living
there, visible, each with its own presence), what they're working on and doing — including but
not limited to those. The site is the author's public surface.

## What IS already decided (infrastructure — do not relitigate)

- **Self-hosted on the author's Proxmox node**: its own container, served via Cloudflare Tunnel
  (zero inbound ports, origin hidden). The web proxy (orange-cloud) is fine for this site.
- DNS is on Cloudflare already. `play.stik.wtf` (Minecraft) stays DNS-only/grey-cloud — this
  project never touches that record. **No DNS changes without the author.**
- **This project is SEPARATE from Outis and from the neoaquatics storefront.** Their repos and
  docs are not task sources here. Shared reality: same node, different tenant.

## The domain and the node today (as of 2026-08-14 — verify with the author, don't assume)

**stik.wtf's subdomain map** — the site must coexist with these, and can link to them:
- apex + `www` → THIS SITE (to be built; orange-cloud via the tunnel).
- `play.stik.wtf` → the author's Minecraft server (Fabric + Geyser, self-hosted on the node,
  migrated 2026-08-14). DNS-only/grey forever; never touched by this project.
- `ai.stik.wtf` → planned: the author's self-hosted AI workspace (their main software project,
  a separate repo), interim access behind Cloudflare Access, invite-only.
- The author also runs `neoaquatics.com` (a storefront, its own project/tenant).

**The server (Proxmox node)** already hosts: an AI-inference container (CPU llama serving for
the author's AI project) and the Minecraft container (16GB heap, 32GB cap); a storefront tenant
is planned. This site is one more SMALL tenant — a website container's resource needs are
negligible next to those, so plan freely; container specs and the tunnel connector get decided
with the author at deploy time.

## Design constraints to honor when planning

- **Low-friction updates or it rots**: "what I'm working on" changes weekly; if updating
  requires writing code, the site fossilizes. Content should live as files (markdown or
  similar) editable without touching layout code.
- Lean: a personal site in a small container — boring, durable tech over framework fashion.
- The plan decides everything else: stack, structure, look, what sections exist at launch
  versus later.

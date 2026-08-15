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

## Design constraints to honor when planning

- **Low-friction updates or it rots**: "what I'm working on" changes weekly; if updating
  requires writing code, the site fossilizes. Content should live as files (markdown or
  similar) editable without touching layout code.
- Lean: a personal site in a small container — boring, durable tech over framework fashion.
- The plan decides everything else: stack, structure, look, what sections exist at launch
  versus later.

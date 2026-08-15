---
sprite: server
title: The Homelab
status: live
weight: 30
summary: The Proxmox node that runs everything on this site — including this site.
---
The infrastructure is itself a project. A Proxmox node runs every service here in its own
container, published through Cloudflare Tunnel with **zero open inbound ports**.

## On the node

- **Minecraft server** — Fabric + Geyser, 16GB heap in a 32GB-cap container
- **AI inference** — CPU llama serving for the [AI workspace](/projects/ai-workspace/)
- **This site** — Hugo, rebuilt on every push

The node itself:

- Intel Xeon E5-2690 v2 @ 3.00GHz
- 384GB RAM (yes, really — server pulls are a cheat code)
- 1TB SSD (new — this site lives here) + 500GB HDD + 240GB HP SSD
- Proxmox VE, one container per service, zero open inbound ports

## The workstation

Where everything gets built (and played):

- Intel Core i9-14900K
- 32GB RAM
- NVIDIA RTX 5080 **and** RTX 3090 — yes, both
- Samsung 990 PRO 4TB

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

Full node specs: getting written down next time I'm in front of it.
<!-- TODO(author): node hardware — CPU, RAM, storage — fill at deploy -->

## The workstation

Where everything gets built (and played):

- Intel Core i9-14900K
- 32GB RAM
- NVIDIA RTX 5080 **and** RTX 3090 — yes, both
- Samsung 990 PRO 4TB

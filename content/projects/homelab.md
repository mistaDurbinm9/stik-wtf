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
- **[git.stik.wtf](https://git.stik.wtf)** — my own git forge, skinned to match this site.
  [This site's source lives there](https://git.stik.wtf/stik/stik-wtf); pushes mirror out
  to GitHub
- **[Neoaquatics](/projects/neoaquatics/)** — the storefront, its own tenant
- **AdGuard** — DNS filtering for the whole house
- **This site** — Hugo, rebuilt on every push

The node itself:

- **2× Intel Xeon E5-2690 v2** — dual socket, 20 cores / 40 threads
- **384GB DDR3-1600 ECC** — 24 × 16GB Hynix registered DIMMs (`HMT42GR7MFR4A-PB`), every
  slot on both boards filled, still running full rated speed (~60 GB/s aggregate,
  benchmarked). Server pulls are a cheat code.
- 1TB SSD (new — this site lives on it) + 2TB HDD (backup target — every container,
  weekly, plus the workstation's off-box backups) + 240GB HP SSD
- Dedicated **10GbE ConnectX-3 link** straight to the workstation — measured 9.1 Gb/s
  RAM-to-RAM, because a spec you haven't benchmarked is a rumor
- Proxmox VE, one container per service, zero open inbound ports

## The workstation

Where everything gets built (and played):

- **Intel Core i9-14900K** (8P + 16E, 24 cores / 32 threads) — 6.1 GHz max boost,
  power limits unlocked, undervolted on a custom V/F curve, ring at 4.5 GHz. Stock
  settings are a suggestion.
- **32GB G.Skill Trident Z5** (SK Hynix dies) — a DDR5-6400 kit overclocked to
  **7000 MT/s** at CL34-42-42-58 2T, and yes, it's stable

### The tune, in numbers

Because "undervolted with unlocked limits" is a vibe until you can read the profile.
Straight from the BIOS:

**CPU**

| | |
| --- | --- |
| P-core boost, by core usage | **6.1 GHz** (1–4 cores) · **5.9 GHz** (5–8 cores), Adaptive Boost + MCE remove-all-limits |
| V/F curve offsets | **−45 mV** at points 7 & 8, **−25 mV** at 9, **−15 mV** at 10 & 11 — undervolt the top of the curve, keep the idle end stock |
| Voltage mode | Adaptive SVID · LLC Level 4 · AC/DC load line 0.40 / 0.98 · CEP off |
| Power limits | PL1 = PL2 = **4095 W**, ICCMAX **400 A** — the cooler is the power limit |
| VRM | 600 kHz fixed switching, duty & phase control on Extreme |
| AVX2 | −1 ratio offset, TVB set to boost-until-target |

**Memory**

| | |
| --- | --- |
| Speed | **DDR5-7000** out of a 6400 XMP kit |
| Primaries | **34-42-42-42-58** |
| The good secondaries | tREFI maxed at **65535** · tRFC2 400 · tWR 48 · tFAW 16 · tRRD 8/4 |
| Tertiaries | tRDRD & tWRWR sg/dg at 16/8 |
| Voltages | VDD/VDDQ **1.48 V** · memory controller **1.40 V** |
- NVIDIA RTX 5080 **and** RTX 3090 — yes, both
- Samsung 990 PRO 4TB

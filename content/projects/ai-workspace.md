---
sprite: llama
title: Metis
status: building
weight: 10
summary: My main software project — Metis, a self-hosted AI workspace to build entire projects in.
---
My main software project, and the most ambitious thing on this site. It has a name:
**Metis** — a self-hosted AI workspace. Not just a chat window; a full workspace to
build projects in.

The goal, stated out loud: stand next to, and eventually surpass, the agent harnesses I
use today — the Codex and Claude Code class of tools. And do it on my own hardware:
inference is CPU llama serving on [the node](/projects/homelab/), no cloud API in the loop.

It started as a fork of
[Odysseus](https://github.com/odysseus-dev/odysseus), an open-source self-hosted
AI workspace, and it's been diverging ever since. The name keeps the mythology straight:
Metis is the cunning Odysseus was famous for.

## The brains

Four seats, one machine:

- **The teacher** — the big model, always on, living in the node's 384GB. It plans,
  reviews, and takes the escalated hard problems. The node reads at about nine tokens a
  second, so the teacher gets handed distilled problems, not raw transcripts.
- **The interactive model** — the one I actually talk to. Always resident, never swapped
  out; when it hits something heavy it escalates to the teacher instead.
- **The worker fleet** — parallel background agents sharing one copy of the weights.
- **The broker** — a 4B model I train myself on the workstation's 3090. Workers say what
  they want in plain intent, the broker proposes the actual tool call, and the harness
  decides whether it runs.

Seats get won, not picked: candidates for a seat run the same measured test battery on
the node, and the cleanest row takes the chair. The teacher seat's contest is running as
I write this — open models up to 397B parameters, ~305GB resident in RAM — which is what
all that DDR3 was for.

## The loop

Metis trains its own broker. Authored tasks run as real turns, every row banks with full
provenance, training happens on the 3090, and a candidate only counts if it clears a
held-out eval with measured headroom — including beating a plain BM25 baseline, the
cheap referee. Even then it only shadow-serves until I flip routing to it. One tap,
reversible.

## The house rule

Models propose, the harness disposes, I approve. No model ever holds the dispatcher.

It'll live at `ai.stik.wtf`. While it's cooking, access is invite-only.

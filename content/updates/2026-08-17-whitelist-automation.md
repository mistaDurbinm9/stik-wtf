---
title: Approvals do the whole job now
date: 2026-08-17
project: minecraft-server
---
Approving a whitelist application used to end with me typing a command into a console.
Now the game server checks the site every minute and whitelists approved players over its
own local RCON, and a Discord agent hands out roles and a DM when they join. The direction
matters: the firewalled game container *pulls* from the site — nothing can push in — so
even a fully compromised web box could at worst let someone in the door, never reach the
console.

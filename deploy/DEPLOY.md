# Go-live runbook — stik.wtf on the node

Done together with the author at the node. Steps marked **[AUTHOR]** touch DNS or accounts
and are theirs to approve/execute. `play.stik.wtf` is never touched.

## 1. Container

Proxmox LXC, Debian 12: 1 vCPU, 512MB–1GB RAM, 8GB disk (static site — this is generous).
Unprivileged, no inbound ports forwarded (the tunnel dials out).

## 2. Install

```
apt install git caddy python3 curl
# hugo EXTENDED from github releases (apt's is often old/non-extended):
curl -L -o hugo.deb https://github.com/gohugoio/hugo/releases/latest/download/hugo_extended_<ver>_linux-amd64.deb && apt install ./hugo.deb
# cloudflared per Cloudflare's apt repo instructions
```

## 3. Site

```
git clone https://github.com/mistaDurbinm9/stik-wtf /srv/site
cd /srv/site && hugo --minify
cp deploy/Caddyfile /etc/caddy/Caddyfile && systemctl reload caddy
```

## 4. serve.py (webhook + counter + uptime) — systemd unit

`/etc/systemd/system/stik-helper.service`:

```ini
[Unit]
Description=stik.wtf node helper
After=network.target

[Service]
Environment=SITE_DIR=/srv/site
Environment=HOOK_SECRET=<generate: openssl rand -hex 24>
ExecStart=/usr/bin/python3 /srv/site/deploy/serve.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`systemctl enable --now stik-helper`

## 5. Tunnel **[AUTHOR]**

```
cloudflared tunnel login          # author's Cloudflare account
cloudflared tunnel create stik-site
cloudflared tunnel route dns stik-site stik.wtf        # [AUTHOR] apex, orange-cloud
cloudflared tunnel route dns stik-site www.stik.wtf    # [AUTHOR] www, orange-cloud
```

Tunnel config: ingress `stik.wtf` + `www.stik.wtf` → `http://localhost:80`, then 404.
Run cloudflared as a service. **No other DNS records change.**

## 6. GitHub webhook

Repo → Settings → Webhooks → Add: URL `https://stik.wtf/hook`, content type JSON,
secret = the HOOK_SECRET from step 4, just push events.

## 7. Optional, same visit **[AUTHOR]**

- Email routing: Cloudflare Email Routing → `hello@stik.wtf` (or author's pick) forwarding
  to their inbox — adds MX/TXT at the apex. Then update `content/contact.md`.
- The hit counter and uptime line light up on their own once serve.py is running.

## 8. Smoke test

```
curl -sI https://stik.wtf | head -3          # 200
curl -s https://stik.wtf/api/count           # {"n":1} — visitor zero is us
curl -s https://stik.wtf/api/uptime          # {"days":0}
```

Then push a trivial commit → site updates itself within seconds. Check /wall/, /404 page,
the Minecraft page's live status, and one page on a phone.

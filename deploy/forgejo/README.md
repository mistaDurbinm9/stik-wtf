# Forgejo theme — git.stik.wtf

`stik-override.css` is the stik.wtf skin for the Forgejo instance (CT 905). It is **not**
a complete theme: it's appended to Forgejo's stock `forgejo-auto` theme so nothing breaks
when only some variables are overridden.

## Rebuild + deploy

```sh
curl -s -o /tmp/base.css https://git.stik.wtf/assets/css/theme-forgejo-auto.css
cat /tmp/base.css deploy/forgejo/stik-override.css > /tmp/theme-stik.css
# → CT 905: /var/lib/gitea/custom/public/assets/css/theme-stik.css  (owner git:git)
# then: systemctl restart forgejo
```

Also deployed to CT 905 (`/var/lib/gitea/custom/templates/`):
- `home.tmpl` → `templates/home.tmpl` — the signed-out landing page, replacing Forgejo's
  marketing copy with the site's hero.
- `footer_content.tmpl` → `templates/base/footer_content.tmpl` — replaces the
  "Powered by Forgejo / version / render time" footer. **Note:** in this version that
  template owns the `<footer>` wrapper itself, so the override must include it.

Config in `/etc/gitea/app.ini` (backups: `app.ini.bak-<date>`, `app.ini.bak-brand`):
`APP_NAME = stik.wtf code`, `[ui] DEFAULT_THEME = stik`. The `SHOW_FOOTER_*` keys are set
but this build ignores them — hence the footer template. Custom logo + favicon live in
`/var/lib/gitea/custom/public/assets/img/` (the mascot and the site favicon, from
`static/`).

## Notes for whoever edits this next

- **Re-run the base fetch after a Forgejo upgrade.** The stock theme is embedded in the
  binary; a new version can add variables this file doesn't know about.
- Two deliberate departures from [DESIGN.md](../../DESIGN.md), both because a forge is a
  dense application rather than a page: borders are 2px (not 3px), and hard shadows are
  reserved for buttons — stacked "attached" panels can't carry a shadow without drawing a
  line through the middle of what reads as one box.
- Specificity: Fomantic's own `.ui.ui.ui` doubling outranks base rules. `!important`
  appears on exactly one property (button `box-shadow`) because Forgejo ships
  `.page-content .ui.button{box-shadow:none!important}` and the press effect is the
  site's signature interaction.
- Static assets are served with `Cache-Control: private, max-age=21600` and the URL's
  `?v=` only changes on Forgejo upgrades — after editing, hard-refresh to see changes.

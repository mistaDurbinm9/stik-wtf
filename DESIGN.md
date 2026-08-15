# stik design system — v1

The visual language of stik.wtf, written to be portable: point any project (neoaquatics,
the Outis redesign) or any model at this file. Reference implementation:
[`assets/css/main.css`](assets/css/main.css) in this repo.

**One sentence:** old-web bones, modern flow — neobrutalism as the base, web-revival
artifacts as rare easter eggs.

## The one rule: the box

Everything interactive or containerized is an honest box:

```css
border: 3px solid var(--ink);
border-radius: 2px;                      /* nearly square — boxes don't apologize */
box-shadow: 6px 6px 0 var(--shadow);     /* hard offset. NO blur. ever. */
```

Forbidden everywhere: blurred shadows, gradients, glassmorphism, rounded-pill corners,
decorative borders thinner than 2px. If a box can't commit to a border, it isn't a box —
use plain spacing instead.

## Tokens

| Token | Light | Dark | Role |
|---|---|---|---|
| `--bg` | `#f5f2ea` warm paper | `#131217` | page background |
| `--surface` | `#ffffff` | `#1d1b23` | cards, boxes |
| `--ink` | `#14120f` | `#f2efe6` | text AND borders — always the same color |
| `--muted` | `#5f5a52` | `#a5a1ae` | secondary text |
| `--accent` | `#B026FF` | `#B026FF` | THE color (see below) |
| `--accent-ink` | `#ffffff` | `#ffffff` | text sitting on accent |
| `--shadow` | = `--ink` | = `--accent` | hard shadows; **dark mode glows accent** |

Rules the tokens encode:

- **One accent.** Exactly one loud color per site. It never gets a palette of friends.
- **Ink is unified**: borders and text are the same near-black (light) / near-white (dark).
  Gray borders are how a design goes mushy.
- **Backgrounds are slightly warm/tinted**, never pure `#fff`/`#000` page backgrounds —
  surfaces sit ON the background, so the two must differ visibly.
- **Dark mode is a swap, not a redesign**: flip ink/surfaces, keep the accent, and move the
  shadow from ink to accent (hard black shadows vanish on dark; accent shadows glow).

## Type

- Font: system stack (`system-ui, -apple-system, "Segoe UI", sans-serif`). No webfonts —
  fast, boring, durable. Mono (`ui-monospace, …`) for dates, badges, addresses, code.
- Headings: weight **900**, tight leading (1.1), slight negative letter-spacing. The
  heaviest weight the stack has — neobrutalist headers are loud or nothing.
- Body: 1rem / 1.6 line-height. `max-width: ~46–70ch` for prose.
- Hero scale: `clamp(2.6rem, 8vw, 4rem)`.

## Components (recipes)

**Link (in prose):** inherit text color; `text-decoration: underline 3px var(--accent)`.
Hover: background becomes accent, text becomes `--accent-ink`. Links look marker-highlighted,
not blue.

**Button (`.btn`):** a small box (border + shadow per The One Rule), weight 800, surface
background. Arrow suffix `→` for navigation actions.

**Card (`.card`):** a box with 16px padding; whole card is the link target; title row
carries the status badge.

**Badge (`.badge`):** mono, uppercase, 0.7rem, 2px border, letter-spaced. Status colors:
`live` = accent background, `building` = page background. Add states per project as needed —
badge stays a box.

**Update row (`.update`):** mono date column + body; rows separated by full 3px ink rules
(top border each row, bottom on the last). Reads like a ledger, not a feed.

**Focus:** `:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }` —
never remove outlines.

**Selection:** `::selection` is accent on accent-ink. Small delight, zero cost.

## Motion

Motion is mechanical, not animated — no transitions needed, state changes just snap:

- Hover on a box: `translate(2px, 2px)` and shrink the shadow to 4px — the box moves
  *toward* its shadow.
- Active/press: translate the full 6px, shadow to 0 — the box lands flat. That's the click.
- Nothing else moves — no fades, slides, parallax, or scroll effects — with ONE exception:
  pixel sprites (next section), which animate in discrete frames.

## Pixel sprites

The web-revival layer, animated. Rules that keep sprites on-theme instead of tacky:

- **`steps()` only, ever.** Frame flips and stepped movement. A sprite that tweens smoothly
  breaks the entire mechanical illusion — it must tick like a game running at 2–10fps.
- **Authoring:** inline SVG grids of 1×1 `<rect>`s with `shape-rendering="crispEdges"`,
  scaled up 3×. Two frames is enough for life (tail flip, blink).
- **Halo:** every free-roaming sprite carries a 1px bg-colored silhouette behind it (game
  sprites do this for a reason) so it stays legible over borders, text, and either theme.
  Baked-color adoptables use the paper tone for the halo so they read on foreign sites too.
- **Palette:** accent + ink + bg only. Sprites obey the one-accent rule like everything else.
- **The mascot is stik** — a pixel stick figure (the handle, literally). Chosen over the
  fish because a mascot should be identity-level, not hobby-level: variants carry the
  facets (the onewheel ride today; hard-hat and fish-holding variants are fair game later).
  Rider in ink, wheel in accent.
- **Vocabulary on stik.wtf** (reference impl: `layouts/partials/pix-stik.html`,
  `layouts/partials/pix-fish.html`, sprite blocks in `assets/css/main.css`,
  `assets/js/site.js`):
  - hover spark: 2-frame pixel blink at a button's corner
  - click burst: pixels scatter in `steps(5)` and vanish — 6 on buttons, 3 anywhere else;
    the whole page is tactile, buttons just more so
  - stik's ride: 2-frame bob on the onewheel, rolling along the bottom edge on
    ~1-in-5 page loads — the ambient slot belongs to the mascot
  - the fish: demoted with honor — a wall adoptable alongside stik, the 404 critter, and
    typing `w t f` (or tapping any fish sprite on the site — the touch path; every egg
    needs one, but it must never hijack navigation) still summons a school of eight
    (a school of stick figures is nonsense)
  - stik speaks: tapping any stik sprite (wall adoptable, blocky variant, even the rider
    mid-roll) pops a mono speech bubble with rotating one-liners — a box like every other
    box, gone in ~2.5s. The mascot has a voice; the fish has a school; they don't swap.
- **Page sprites:** each page may carry ONE small themed sprite, floated at the title,
  chosen via `sprite:` in frontmatter (content-editable, no layout edits). stik.wtf's set:
  blocky-stik mining (minecraft — the mascot goes cube-headed; themed variants beat
  borrowed characters), llama (AI — it IS llama serving), server rack with blinking LED
  (homelab), fish tank with bubbles (neoaquatics), ticking clock (now), envelope with
  notification pixel (contact). Margin decorations (the Minecraft floating islands) are
  allowed only where real empty margin exists — hidden below ~1120px viewport width. The
  islands carry a baked Minecraft palette (grass/dirt/stone) under the same artifact
  exemption as the badges: an artifact depicting a thing wears that thing's colors.
- **Ration the ambience:** at most one ambient sprite event per page load, one page sprite
  per page. Easter eggs stay eggs by being rare.
- **`prefers-reduced-motion: reduce` disables every sprite.** Non-negotiable.
- Porting: each project picks its own creature (neoaquatics has obvious candidates); the
  spark/burst mechanics port as-is.

## Layout

- Single centered column, `max-width: 780px`, 20px side padding. Grids inside it:
  `repeat(auto-fill, minmax(240px, 1fr))`.
- Whitespace does the hierarchy; boxes do the emphasis. Never nest a box in a box more
  than one level deep.

## Web-revival easter eggs (the "between" part)

Rare, genuine, confined to their own corner — never in the core navigation/reading path.
If it's everywhere, it's a theme, not an easter egg. The vocabulary on stik.wtf:

- **The wall** (`/wall`, linked only from the footer): the 88x31 badge strip, the site's
  own copyable button, and the adoptable fish. Badges are hand-made 88x31 SVGs with the
  palette **baked in** (artifacts are static images — they do not theme-swap), monospace
  type, 2px borders, `crispEdges`. A site's own button + "send me yours" is the genuine
  reciprocal-linking tradition, not decoration.
- **Under-construction banner**: caution stripes in accent/ink (not hazard yellow — the
  artifact adapts to the system palette), shown automatically on `status: building` pages.
- **Hit counter + uptime line**: real numbers from the author's own server or nothing —
  never faked. Hidden until the backing endpoint exists.
- Future, author-gated: guestbook, joining a real webring, a friends link-roll on the wall.

## Accessibility floor (non-negotiable)

- Text on accent must clear WCAG AA (4.5:1). `#B026FF` takes **white** text, not black.
- `--muted` on `--bg` must clear AA for body-size text.
- Visible focus states everywhere; color never the only signal (badges carry words).
- Respect `prefers-color-scheme`; both modes are first-class.

## Porting guide — for other projects and other models

Reusing this system (neoaquatics storefront, Outis redesign):

**Keep (this IS the system):** the box rule, unified ink, one-accent rule, hard shadows,
the motion mechanics, mono-for-metadata, weight-900 headings, the dark-mode swap
(including shadow→accent), the accessibility floor.

**Swap per project (this is the brand):**
- `--accent` (+ recheck `--accent-ink` contrast). stik.wtf: purple `#B026FF`.
  In the family so far: neoaquatics.com runs a committed-dark terminal variant — near-black
  blue bg, emerald accent family, all-mono, zero-radius `.EXE` window chrome. Same bones
  (mono metadata, uppercase labels, hard edges, one accent hue), own creature. Outis picks
  its own when its turn comes.
- Background temperature (`--bg`/`--surface` tint) — warm paper here; a storefront might
  run cooler.
- Density: a storefront needs tighter cards and product grids — keep the box, shrink the
  padding and shadow (2px border / 4px shadow is the compact variant).

**Don't:** add a second accent, soften shadows "just for this one component", introduce a
webfont without a reason that survives a night's sleep, or mix this with another design
language on the same page.

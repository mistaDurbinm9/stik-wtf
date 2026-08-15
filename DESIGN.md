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
- Nothing else moves. No fades, no slides, no parallax, no scroll effects.

## Layout

- Single centered column, `max-width: 780px`, 20px side padding. Grids inside it:
  `repeat(auto-fill, minmax(240px, 1fr))`.
- Whitespace does the hierarchy; boxes do the emphasis. Never nest a box in a box more
  than one level deep.

## Web-revival easter eggs (the "between" part)

Rare, genuine, post-launch: an 88x31 badge wall, a guestbook-style page. Rules: real
artifacts only (actual 88x31 GIFs, not modern imitations), confined to their own corner,
never in the core navigation/reading path. One or two total. If it's everywhere, it's a
theme, not an easter egg.

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
  Suggestion-shaped, not decided: neoaquatics wants an aquatic accent; Outis picks its own.
- Background temperature (`--bg`/`--surface` tint) — warm paper here; a storefront might
  run cooler.
- Density: a storefront needs tighter cards and product grids — keep the box, shrink the
  padding and shadow (2px border / 4px shadow is the compact variant).

**Don't:** add a second accent, soften shadows "just for this one component", introduce a
webfont without a reason that survives a night's sleep, or mix this with another design
language on the same page.

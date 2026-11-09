# InvoiAI interface system

> Ticket 13 design foundation. Source of truth for tokens, primitives, motion,
> and the Lottie policy. The token values live in
> `frontend/src/styles/design-tokens.css`; do not redefine them elsewhere.

## Intent

InvoiAI is an AP control room, not a generic analytics dashboard. It should feel composed and decisive: show the current state, the owner, and the next safe action before secondary detail.

## Visual language

- **Foundation:** ink navy `#10152D` on paper `#F7F9FF`, with white working surfaces.
- **Action:** Invoi blue `#315CF6`; reserve mint `#93F3CA` for confirmed/healthy fills, never as text on white.
- **Type:** DM Sans for scanning, controls, tables and operational headings. Playfair Display for display moments only (marketing hero, page titles, auth headlines). No new font without design review.
- **Space:** 8px rhythm, 16px standard surface radius, 44px minimum control height.
- **Motion:** 150–250ms opacity, colour, border, shadow and transform transitions only; none when reduced motion is requested.

## Semantic tokens

| Group | Token | Value | Use |
|---|---|---|---|
| Surface | `--surface-page` | `#F7F9FF` | App canvas |
| Surface | `--surface-raised` | `#FFFFFF` | Cards, forms, tables |
| Surface | `--surface-sunken` | `#EEF2FF` | Selected rows, wells |
| Surface | `--surface-inverse` | `#10152D` | Inverse panels |
| Ink | `--ink-primary` | `#10152D` | Body and headings |
| Ink | `--ink-secondary` | `#5D6886` | Supporting text |
| Accent | `--accent-primary` | `#315CF6` | Actions and links |
| Accent | `--accent-hover` | `#2447D8` | Hover/pressed |
| Accent | `--accent-confirmed` | `#0F6B4A` | Healthy text |
| Border | `--border-subtle` | `#DCE3F7` | Default dividers |
| Border | `--border-strong` | `#BFCBFF` | Emphasis |
| Danger | `--danger` | `#B4232F` | Errors and destructive actions |
| Warning | `--warning` | `#8A5A00` | Warnings |
| Success | `--success` | `#0F6B4A` | Confirmed states |
| Focus | `--focus-ring` | `#315CF6` | 3px keyboard outline |
| Radius | `--radius-sm…xl` | 8/12/16/22px | Surface scale |
| Elevation | `--elevation-1…3` | 1px → 48px blur | Rest/hover/overlay |
| Motion | `--motion-fast/base/slow` | 150/200/250ms | Interaction timing |

Legacy names (`--bg`, `--surface`, `--ink`, `--muted`, `--accent`, `--border`,
`--error`, `--display`, `--ia-*`) are aliases defined once in the token file so
existing components keep working while new code uses the semantic names.

### Measured contrast (WCAG 2.1, 2026-11-09)

| Pair | Ratio |
|---|---|
| Ink `#10152D` on page `#F7F9FF` | 17.09:1 |
| Ink on raised `#FFFFFF` | 17.99:1 |
| Muted `#5D6886` on raised | 5.54:1 |
| Muted on page | 5.26:1 |
| Muted on sunken `#EEF2FF` | 4.96:1 |
| Accent `#315CF6` on raised | 5.26:1 |
| White on accent | 5.26:1 |
| Danger `#B4232F` on raised | 6.52:1 |
| Success `#0F6B4A` on raised | 6.52:1 |
| Warning `#8A5A00` on raised | 5.93:1 |
| Ink on mint `#93F3CA` | 13.63:1 |
| White `--on-accent` on accent | 5.26:1 |
| White `--on-danger` on danger | 7.25:1 |

Dark specimen pairs: ink `#F2F5FF` on page `#0B1024` 17.31:1; muted
`#C3CCE6` on raised `#141A33` 10.69:1; accent `#8FA8FF` on raised 7.52:1;
danger `#FF9AA2` on raised 8.48:1; `--on-accent` `#10152D` on accent 7.89:1;
`--on-danger` `#2B0A0D` on danger 9.02:1.

Use `--on-accent`, `--on-danger`, and `--on-success` for text on filled status
surfaces. Never hardcode `white` on a dark-theme accent fill.

All normal-text pairs meet or exceed 4.5:1. Mint is fill-only; mint text on
white fails contrast and is not used.

## Primitives and contrast limits

- `.ds-glass` — translucent raised surface with `backdrop-filter` and an opaque
  `@supports` fallback. Use for chrome and decoration: navigation, top bars,
  scrims, marketing moments.
- `.ds-gloss` — a subtle specular highlight over a solid surface. Use on cards
  and hero art. It never replaces the solid background.
- `.ds-data-surface` — opaque working surface for tables, forms, review and
  approval panels.
- `.ds-elevation-1/2/3`, `.ds-motion`, and the global `:focus-visible` ring.

**Never put blur behind dense text, table values, form fields, review content,
or approval content.** Those screens use `.ds-data-surface` or an opaque card.
A translucent effect may sit behind chrome (sidebar/topbar) or a decorative
panel, never behind the financial value a user is deciding on.

## Applied screen

The dashboard (`/dashboard`) is the representative product screen:

- The topbar uses `.ds-glass`; the dark sidebar stays opaque so its navigation labels retain contrast.
- Overview module cards use `.ds-gloss` over an opaque card.
- Usage, document and activity cards use `.ds-data-surface`; data, form, review and approval content never sits on glass.
- The token primitives and focus ring are global; legacy screen colors remain in migration and are not described as tokenized until converted.
- Keyboard focus uses the shared 3px ring; reduced motion collapses
  transitions to 0.01ms.

## Working-surface rules

1. A page gets one large title, one supporting sentence, and at most one primary action.
2. Cards carry a clear label and action. Hover is affordance, never required information.
3. Tables preserve their headers and horizontally scroll on narrow screens.
   Table values stay on opaque surfaces with tabular numerals.
4. Forms keep labels above inputs, 44px minimum control height, visible focus,
   and inline error text tied to the field.
5. Review and approval screens use opaque panels, explicit status text, and a
   single next action. Blur, gloss, and decorative motion stay out of the
   decision area.
6. Every interactive control has a visible keyboard focus ring.
7. Error, warning, and success states pair labels/icons with colour.

## Lottie policy

- Lottie is allowed only for meaningful onboarding, success, or empty states.
- It must be local, licensed, lazy-loaded, and must respect reduced motion.
- Remote iframes are not allowed. The previous LottieFiles embeds on login,
  signup and the landing hero were replaced with a local static SVG
  (`frontend/src/components/ui/MotionMark.tsx`). No animation dependency was
  added.
- Do not add 3D, GSAP, Framer Motion, or a Lottie runtime without a specific
  state that needs motion and a design review.

## Evidence

- Token source: `frontend/src/styles/design-tokens.css`
- Specimen: `design-system/invoiai/evidence/token-preview.html`
- Screenshots: `design-system/invoiai/evidence/desktop-light.png`,
  `desktop-dark.png`, `mobile-light.png`, `reduced-motion.png`
- Checks: contrast table above; keyboard focus uses the shared ring; reduced
  motion collapses transitions; mobile specimen is captured at 520px, where
  the mobile breakpoint is active and the invoice table scrolls independently.

## Known follow-ups

- Product routes remain light-only. `[data-ds-theme="dark"]` exists for the
  reference specimen until every hardcoded colour is tokenised.
- Some legacy screens still carry hardcoded warm colours from the pre-token
  generation. They are migrated screen by screen; new work must use tokens.

---
version: alpha
name: DEMOEMA Glassmorphism
description: Dark M&A intelligence platform — aurora-glass aesthetic, dense data grids, premium financial UI. Source-of-truth pour les agents IA codeurs.
colors:
  bg-base: "#050507"
  bg-layer-1: "#0a0a0d"
  bg-layer-2: "#111114"
  bg-layer-3: "#16161b"
  bg-elevated: "#161620"
  text-primary: "#e8e8ec"
  text-secondary: "#a1a1aa"
  text-tertiary: "#6b6b75"
  text-muted: "#4a4a52"
  accent-blue: "#60a5fa"
  accent-purple: "#a78bfa"
  accent-cyan: "#67e8f9"
  accent-emerald: "#34d399"
  accent-amber: "#fbbf24"
  accent-rose: "#fb7185"
  accent-indigo: "#818cf8"
  border-subtle: "#0fffffff"
  border-soft: "#1affffff"
  border-mid: "#28ffffff"
typography:
  display:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: 700
    letterSpacing: -0.02em
  h1:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: 700
    letterSpacing: -0.02em
  h2:
    fontFamily: Outfit
    fontSize: 18px
    fontWeight: 700
    letterSpacing: -0.01em
  h3:
    fontFamily: Outfit
    fontSize: 14px
    fontWeight: 600
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: Inter
    fontSize: 12.5px
    fontWeight: 500
  caption:
    fontFamily: Inter
    fontSize: 11.5px
    fontWeight: 500
  micro:
    fontFamily: Inter
    fontSize: 10.5px
    fontWeight: 600
    letterSpacing: 0.08em
  mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: 500
    fontFeature: '"tnum" 1'
rounded:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 10px
  xl: 12px
  pill: 999px
spacing:
  xxs: 2px
  xs: 4px
  sm: 6px
  md: 10px
  lg: 14px
  xl: 18px
  xxl: 28px
components:
  glass:
    backgroundColor: "rgba(17, 17, 20, 0.55)"
    backdrop: "blur(24px) saturate(140%)"
    borderColor: "{colors.border-subtle}"
    rounded: "{rounded.xl}"
  glass-2:
    backgroundColor: "rgba(10, 10, 13, 0.70)"
    backdrop: "blur(32px) saturate(150%)"
    borderColor: "{colors.border-soft}"
    rounded: "{rounded.xl}"
  btn:
    backgroundColor: "rgba(255, 255, 255, 0.03)"
    textColor: "{colors.text-secondary}"
    borderColor: "{colors.border-soft}"
    rounded: "{rounded.md}"
    padding: "6px 10px"
    typography: "{typography.body-sm}"
  btn-hover:
    backgroundColor: "rgba(255, 255, 255, 0.06)"
    textColor: "{colors.text-primary}"
    borderColor: "{colors.border-mid}"
  btn-primary:
    backgroundColor: "linear-gradient(135deg, rgba(96, 165, 250, 0.18), rgba(167, 139, 250, 0.18))"
    textColor: "#cfe1fb"
    borderColor: "rgba(96, 165, 250, 0.35)"
    rounded: "{rounded.md}"
  btn-primary-hover:
    backgroundColor: "linear-gradient(135deg, rgba(96, 165, 250, 0.28), rgba(167, 139, 250, 0.28))"
    textColor: "#ffffff"
    borderColor: "rgba(96, 165, 250, 0.55)"
  btn-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    borderColor: "transparent"
  btn-ghost-hover:
    backgroundColor: "rgba(255, 255, 255, 0.05)"
    borderColor: "{colors.border-soft}"
  btn-icon:
    height: 28px
    width: 28px
    padding: 0
  chip:
    backgroundColor: "rgba(255, 255, 255, 0.025)"
    textColor: "{colors.text-secondary}"
    borderColor: "{colors.border-soft}"
    rounded: "{rounded.pill}"
    padding: "4px 9px"
    typography: "{typography.caption}"
  chip-active:
    backgroundColor: "rgba(96, 165, 250, 0.12)"
    textColor: "#cfe1fb"
    borderColor: "rgba(96, 165, 250, 0.40)"
  sheet-panel:
    backgroundColor: "{colors.bg-layer-1}"
    borderColor: "{colors.border-soft}"
    width: "min(960px, 94vw)"
  sheet-backdrop:
    backgroundColor: "rgba(0, 0, 0, 0.5)"
    backdrop: "blur(6px)"
  tooltip:
    backgroundColor: "{colors.bg-layer-3}"
    borderColor: "{colors.border-mid}"
    rounded: "{rounded.lg}"
    padding: "10px 12px"
    typography: "{typography.caption}"
  card-pipe:
    backgroundColor: "{colors.bg-layer-2}"
    borderColor: "{colors.border-soft}"
    rounded: "{rounded.lg}"
    padding: "12px"
  score-halo-high:
    backgroundColor: "rgba(52, 211, 153, 0.10)"
    textColor: "{colors.accent-emerald}"
    rounded: "{rounded.pill}"
  score-halo-mid:
    backgroundColor: "rgba(251, 191, 36, 0.10)"
    textColor: "{colors.accent-amber}"
    rounded: "{rounded.pill}"
  score-halo-low:
    backgroundColor: "rgba(251, 113, 133, 0.10)"
    textColor: "{colors.accent-rose}"
    rounded: "{rounded.pill}"
  cite-marker:
    backgroundColor: "rgba(96, 165, 250, 0.15)"
    textColor: "{colors.accent-blue}"
    borderColor: "rgba(96, 165, 250, 0.30)"
    rounded: "{rounded.xs}"
    typography: "{typography.mono}"
  kbd:
    backgroundColor: "rgba(255, 255, 255, 0.06)"
    textColor: "{colors.text-secondary}"
    borderColor: "{colors.border-soft}"
    rounded: "{rounded.xs}"
    typography: "{typography.mono}"
---

## Overview

DEMOEMA est une plateforme M&A propriétaire (origination + DD + scoring). L'esthétique combine **glassmorphism profond**, **aurora background** subtil, et **densité data Bloomberg-style** — premium, sombre, calme.

**Principes** :
- **Hiérarchie par opacité, pas par couleur** : 4 niveaux de texte (`primary` → `muted`), 3 niveaux de bord (`subtle` → `mid`). Les couleurs accentuelles sont rares et porteuses de sens (succès / alerte / sélection).
- **Profondeur par flou (`backdrop-filter`), pas par ombre** : `glass` avec `blur(24px) saturate(140%)`. Les éléments superposés gagnent en luminosité (`bg-layer-1` → `bg-layer-3`).
- **Numérique = monospace tabular** : tout chiffre financier (CA, score, mandats) en `JetBrains Mono` avec `font-variant-numeric: tabular-nums`. Alignement vertical = lisibilité.
- **Mouvement minimal** : `dem-fade-up` (8px / 350ms), `dem-slide-in` (drawer), `dem-pulse-dot` (live state). Respecter `prefers-reduced-motion`.

## Colors

Palette anchored sur des **neutres très foncés** (`#050507` → `#161620`) plus **6 accents vifs** utilisés exclusivement pour signaux M&A.

| Token | Hex | Usage |
|---|---|---|
| `bg-base` | `#050507` | Body / aurora canvas |
| `bg-layer-1` | `#0a0a0d` | Drawer (`sheet-panel`) |
| `bg-layer-2` | `#111114` | Cards pipeline |
| `bg-layer-3` | `#16161b` | Tooltips / popups élevés |
| `bg-elevated` | `#161620` | Modals centrés |
| `text-primary` | `#e8e8ec` | Titres, valeurs financières clés |
| `text-secondary` | `#a1a1aa` | Body, descriptions |
| `text-tertiary` | `#6b6b75` | Labels uppercase, métadonnées |
| `text-muted` | `#4a4a52` | Placeholders, séparateurs |
| `accent-blue` | `#60a5fa` | **Citations / sélection** (lien primaire) |
| `accent-purple` | `#a78bfa` | **AI / streaming** (caret, orbe, reasoning) |
| `accent-cyan` | `#67e8f9` | **Tool calls running** / events |
| `accent-emerald` | `#34d399` | **Succès** : score high, healthy |
| `accent-amber` | `#fbbf24` | **Warning** : score mid, late filing |
| `accent-rose` | `#fb7185` | **Alerte** : red flag, sanction, urgent |

## Typography

**2 familles** : `Inter` (sans), `JetBrains Mono` (numérique). Heading via `Outfit` (variable `--font-outfit`). Anti-aliasing + `cv11 ss01 ss03` font-features actifs.

**Scale ratio dense** (12pt système, pas Material) : `10.5 / 11.5 / 12 / 12.5 / 14 / 18 / 24 / 26`. Letter-spacing négatif sur les displays (`-0.02em`), positif sur les caps (`0.08em`).

## Layout & Spacing

Grille **fluide responsive**, pas de breakpoints durs hors mobile (`@media (pointer: coarse)`). Padding card standard : `14px 18px`. Gap entre éléments inline : `6px` (chip) → `14px` (section).

**Touch targets** : `min 44×44px` sur mobile (`@media (pointer: coarse)`).

## Elevation & Depth

Pas de `box-shadow` opaques. Profondeur via :
1. `backdrop-filter: blur()` (24px standard, 32px pour glass-2)
2. `border` 1px à opacité variable (`subtle` < `soft` < `mid`)
3. **Halos lumineux** sur hover : `box-shadow: 0 8px 30px -12px rgba(96, 165, 250, 0.20)` (card-lift)

## Shapes

Coins arrondis échelonnés `4 → 6 → 8 → 10 → 12 → pill`. Tout est arrondi — pas d'angles vifs.

## Components

### `glass` / `dem-glass`
Surface vitre standard. Tous les containers principaux (cards, sections, headers) doivent l'utiliser. **Ne jamais utiliser `bg-white` direct.**

### `btn` / `dem-btn` (+ variantes)
- `dem-btn` — neutre, état repos
- `dem-btn-primary` — gradient bleu→violet, action principale (Pitch, Sauver, Lancer DD)
- `dem-btn-ghost` — pas de bord, pour actions secondaires inline
- `dem-btn-icon` — 28×28 carré pour close (×) / icônes seules

### `chip` / `dem-chip`
Pour filtres, suggestions, métadonnées rapides. État actif = `dem-chip-active` (bordure bleue, fond bleu-tinted).

### `sheet-panel` + `sheet-backdrop`
Drawer côté droit `min(960px, 94vw)`. Slide-in 250ms cubic-bezier(.2, .8, .2, 1). Esc + click backdrop ferment. **Pattern utilisé** : `TargetSheet`, `PersonSheet`.

### `score-halo` (high / mid / low)
Badge rond pour scores M&A. Mapping :
- `>= 70` → `high` (emerald)
- `40-69` → `mid` (amber)
- `< 40` → `low` (rose)

### `tool-call`
Bloc copilot live streaming. État `running` (cyan pulsing dot) → `done` (emerald dot fixe).

### `cite-marker`
Référence bibliographique inline (`[1]`, `[2]`). Style mono superscript, hover bleu plein.

### `reasoning-trace`
Traces du LLM. Border-left violet 30% opacity, content mono 12px tertiary.

### `pipe-col` + `pipe-card`
Kanban deal pipeline. Variant `urgent` → bord rose + halo subtil.

### `aurora-bg`
Background fixed décoratif. **Toujours premier child du shell**, `pointer-events: none`, `z-index: 0`.

## Do's and Don'ts

### ✅ Do

- **Toujours** consulter `DESIGN.md` avant ajout de couleur/composant. Réutilise les tokens existants.
- **Toujours** utiliser `dem-mono` ou classe Tailwind `font-mono` pour valeurs numériques (CA, scores, mandats, sirens).
- **Toujours** utiliser CSS vars (`var(--accent-blue)`) plutôt que hex direct — assure cohérence cross-composants et permet thème futur.
- **Toujours** respecter l'ordre des layers : `bg-base` (aurora) < `bg-layer-1` (drawer) < `bg-layer-2` (card) < `bg-layer-3` (tooltip).
- **Toujours** prévoir l'état `:hover` avec transition `.12s ease` minimum sur tout élément cliquable.
- **Toujours** tester contraste WCAG AA (4.5:1 body, 3:1 large) — `npx @google/design.md lint DESIGN.md` valide automatiquement.

### ❌ Don't

- **Ne jamais** introduire un framework UI tiers (Material, Chakra, Bloomberg-styled libs comme lucide). Stack actuelle = Tailwind + composants custom `dem-*`.
- **Ne jamais** utiliser `bg-white`, `bg-gray-100`, `text-black` direct. Toujours via tokens.
- **Ne jamais** réécrire `frontend/src/app/page.tsx` ou `globals.css` sans vérifier que les classes `dem-*` et `sheet-*` restent fonctionnelles (cf. incident PR #11 hakim — refonte Bloomberg incompatible avec PersonSheet/TargetSheet).
- **Ne jamais** utiliser `box-shadow` opaque (`rgba(0,0,0,X)`) — préférer halos accent (`rgba(accent, 0.10-0.20)`).
- **Ne jamais** mélanger `backdrop-filter: blur` avec `transform` sur le même élément (Safari bug, perfo dégradée).
- **Ne jamais** créer une nouvelle classe `.glass*` ou `.dem-*` sans l'ajouter ici dans `## Components` + dans `globals.css`.
- **Ne jamais** désactiver `prefers-reduced-motion` — anim courtes (.12-.35s) déjà gérées dans `globals.css:87-93`.

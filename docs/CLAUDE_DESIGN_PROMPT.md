# 🎨 Prompt design DEMOEMA Front — Futuriste + Pro

> Prompt à donner à **claude.ai/design** (ou tout autre LLM design tool comme v0.dev,
> Bolt.new, lovable.dev). Objectif : générer le frontend Next.js 15 de DEMOEMA
> avec une esthétique **futuriste + professionnelle** mid-cap M&A intelligence.

---

## 🎯 Vision design — "Bloomberg Terminal × Apple Vision Pro × Linear × Tesla UI"

**Le sentiment qu'on doit ressentir** :

> *"On est en 2030. Cette plateforme ressemble à ce qu'aurait fait Tesla si Tesla
> faisait du M&A. Hyper data-dense comme un Bloomberg Terminal, mais avec
> l'esthétique spatiale d'un Vision Pro. Précision suisse de Linear, vitesse
> brutale de Vercel. Quand un dirigeant CAC40 ouvre l'app, il doit penser
> 'ces gens sont 5 ans en avance sur tous mes concurrents'."*

### Inspirations visuelles concrètes

| Référence | À piquer |
|---|---|
| **Linear** (linear.app) | Densité info, keyboard-first, transitions imperceptibles |
| **Vercel Dashboard** | Minimalisme premium, cards parfaitement alignées |
| **Bloomberg Terminal** | Information density, tableaux verticaux compacts |
| **Apple Vision Pro / visionOS** | Glassmorphism, spatial depth (3D layered), aurora backgrounds |
| **Tesla Cybertruck UI** | Geometric brutalism, mono fonts, rectangles affirmés |
| **Cyberpunk 2077 NetRunner** | Neon glows, scan lines subtiles, data streams |
| **Anthropic Console** | Sobre, premium, AI-native (sources/citations visibles) |
| **Replit / Raycast** | Command palette, fluidité spatiale |
| **Bloomberg LP** | Profondeur navigation par tabs latéraux |

---

# DEMOEMA — Plateforme d'Origination M&A Intelligence

## 🎯 Contexte produit

DEMOEMA = **EdRCF 6.0** : SaaS B2B d'origination M&A propriétaire pour boutiques
M&A FR (10-50 employés). Ciblage : **mid-cap français** (10M-1B€ EV).

**Problème résolu** : trouver les cibles M&A pertinentes parmi 5M entreprises FR
+ croiser 144 sources data + scorer 0-100 + alerter sur événements capitalistiques
+ DD compliance instantanée + cartographier réseau dirigeants.

**Concurrents évincés** : Mergermarket (€50K/an), Dealogic (€80K/an),
PitchBook (€30K/an). DEMOEMA prix cible 199-500€/mois (Pro).

## 👤 Persona utilisateur

**Anne Dupont, 38 ans, Senior Associate boutique M&A Paris 8e** :
- Vient du M&A advisory de **Lazard / Rothschild / Bryan Garnier**
- Habituée à Mergermarket (qu'elle déteste : interface 2008)
- Workflow : 5-15 cibles sourcées/semaine, 2 fiches DD complètes/jour
- Cherche : **vitesse**, **densité info**, **propriétaire** (zéro leak client),
  **export PDF présentable au CEO**
- N'utilise PAS la souris (raccourcis clavier obligatoires : Cmd+K, /, ?, Esc)

## 🧱 Stack technique imposée

```yaml
framework: Next.js 15 (App Router, Server Components)
language: TypeScript 5.x strict mode
styling: Tailwind v4 (config inline @theme block)
animations: Framer Motion 11
ui_kit: shadcn/ui (Button, Card, Sheet, Dialog, CommandPalette, Tooltip)
data_fetching: TanStack Query 5 + React Suspense
tables: TanStack Table 8 (virtualized)
graphs: ForceGraph2D + react-force-graph-2d
charts: Recharts (responsive)
3d: Three.js / react-three-fiber (subtle accents only)
icons: Lucide-react + Tabler icons
fonts:
  primary: Inter Variable (sans-serif)
  mono: JetBrains Mono Variable (data, SIREN)
  display: Geist Mono Variable (headlines)
auth: Supabase JWT + RLS
api: REST FastAPI + SSE streaming
deployment: Cloudflare Workers (frontend) + Hetzner VPS (backend)
```

## 🎨 Design System

### Palette principale (Dark default)

```css
/* Backgrounds — profondeur spatiale */
--bg-base: #050507;           /* zinc-950 plus profond, presque noir absolu */
--bg-layer-1: #0a0a0d;        /* surface card layer 1 */
--bg-layer-2: #111114;        /* layer 2 (modal, sidebar) */
--bg-layer-3: #1a1a1f;        /* layer 3 (popover) */

/* Aurora gradient backgrounds (pour pages vides ou hero) */
--aurora-1: linear-gradient(135deg,
            rgba(59, 130, 246, 0.08) 0%,
            rgba(168, 85, 247, 0.05) 50%,
            rgba(236, 72, 153, 0.08) 100%);

/* Borders — ultra-subtils */
--border-subtle: rgba(255, 255, 255, 0.06);
--border-default: rgba(255, 255, 255, 0.1);
--border-active: rgba(59, 130, 246, 0.4);

/* Brand — neon accents */
--accent-blue: #60a5fa;       /* primary actions */
--accent-purple: #a78bfa;     /* AI / Copilot */
--accent-emerald: #34d399;    /* score >= 70, success */
--accent-amber: #fbbf24;      /* score 50-69, warning */
--accent-rose: #fb7185;       /* score < 30, danger */
--accent-cyan: #67e8f9;       /* live data, real-time */

/* Text */
--text-primary: #f4f4f5;       /* zinc-100 */
--text-secondary: #a1a1aa;     /* zinc-400 */
--text-tertiary: #71717a;      /* zinc-500 */
--text-disabled: #52525b;      /* zinc-600 */

/* Glow halos (signature DEMOEMA) */
--glow-score-high: 0 0 24px rgba(52, 211, 153, 0.4),
                   0 0 48px rgba(52, 211, 153, 0.1);
--glow-score-medium: 0 0 16px rgba(251, 191, 36, 0.3);
--glow-score-low: 0 0 12px rgba(251, 113, 133, 0.3);
--glow-ai: 0 0 32px rgba(167, 139, 250, 0.3);
```

### Typography

```
H1 (page title)        : Geist Mono 48px / 1.1 / -0.04em / 600
H2 (section)           : Inter Display 32px / 1.2 / -0.03em / 600
H3 (card title)        : Inter 18px / 1.3 / -0.01em / 500
Body                   : Inter 14px / 1.6 / 0
Small                  : Inter 12px / 1.5 / 0.01em
Mono (SIREN, codes)    : JetBrains Mono 13px / 1.4 / 0
Number display (KPI)   : Geist Mono 56px / 1 / -0.05em / 700 (+ tabular-nums)
```

### Spacing & Layout

```
Density mode = "compact" par défaut (Bloomberg style)
Scale : 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 px
Container max-width : 1920px (4K-friendly)
Grid : 12 colonnes, gap 16px
Card padding : 16px (compact) / 24px (comfortable mode)
```

### Effets signatures DEMOEMA

#### 1. **Glassmorphism profond**
```tsx
className="bg-zinc-950/40 backdrop-blur-2xl border border-white/[0.06]
           shadow-[0_8px_32px_rgba(0,0,0,0.4)]"
```

#### 2. **Aurora background subtil** (pages d'accueil, hero)
```tsx
<div className="absolute inset-0 -z-10
                bg-[radial-gradient(circle_at_top_right,
                rgba(59,130,246,0.08),transparent_50%),
                radial-gradient(circle_at_bottom_left,
                rgba(168,85,247,0.05),transparent_50%)]" />
```

#### 3. **Score halo ring** (signature visuelle)
```tsx
<div className={cn(
  "rounded-full p-3 transition-all duration-300",
  score >= 70 && "shadow-[0_0_24px_rgba(52,211,153,0.4)] ring-2 ring-emerald-500/30",
  score >= 50 && score < 70 && "shadow-[0_0_16px_rgba(251,191,36,0.3)] ring-2 ring-amber-500/30",
  score < 50 && "shadow-[0_0_12px_rgba(251,113,133,0.3)] ring-2 ring-rose-500/30"
)}>
  <span className="font-mono text-lg tabular-nums">{score}</span>
</div>
```

#### 4. **Animated borders** (CTA premium, AI actions)
```tsx
<button className="relative overflow-hidden rounded-lg group">
  <span className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-pink-500/20
                   animate-shimmer bg-[length:200%_100%]" />
  <span className="relative z-10 px-4 py-2">Activate Copilot</span>
</button>
```

#### 5. **Number count-up** (Framer Motion sur stats)
```tsx
<motion.span
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  className="font-mono text-5xl tabular-nums"
>
  <CountUp from={0} to={1247} duration={1.2} />
</motion.span>
```

#### 6. **Scan line subtle** (sur tables temps réel — Feed Signaux)
```tsx
<div className="relative overflow-hidden">
  <div className="absolute top-0 left-0 right-0 h-px
                  bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent
                  animate-scan-line" />
  {/* table content */}
</div>
```

#### 7. **3D depth on cards** (visionOS style)
```tsx
<motion.div
  whileHover={{ y: -2, rotateX: 2, rotateY: -1 }}
  style={{ transformStyle: "preserve-3d", perspective: 1000 }}
  className="bg-zinc-900/40 backdrop-blur-2xl border border-white/[0.06]
             rounded-xl p-6 will-change-transform"
>
```

#### 8. **Particle accent** (sur events critiques uniquement, sparingly)
```tsx
{event.severity === "CRITICAL" && (
  <div className="absolute -top-1 -right-1">
    <span className="relative flex h-3 w-3">
      <span className="animate-ping absolute inline-flex h-full w-full
                       rounded-full bg-rose-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500" />
    </span>
  </div>
)}
```

---

## 📄 Pages à designer (par priorité)

### 1. **Intelligence Targets** ⭐ PRIORITÉ #1

Layout :
```
┌─────────────────────────────────────────────────────────────┐
│ [DEMOEMA logo]   Search ⌘K   |  Avatar  Notifs   ?   ⚙️   │ ← header 56px
├──┬──────────────────────────────────────────────────────────┤
│  │ ╔══════════════════════════════════════════════════════╗ │
│ N│ ║ Intelligence Targets    [Export CSV] [Saved] [+ New]║ │
│ a│ ║ 1,247 cibles HOT  ·  median score 73  ·  +23 today  ║ │
│ v│ ╚══════════════════════════════════════════════════════╝ │
│  │ ┌─Filters─┐  ┌──────────Table virtualisée────────────┐ │
│  │ │ Score   │  │ Denom    SIREN  NAF  Score Ca  Top  …│ │
│  │ │ ───●─── │  │ ████████████████████████████████████ │ │
│  │ │ Sector  │  │ ████████████████████████████████████ │ │
│  │ │ ☑ Tech  │  │ Acme SAS  838.. 24.10  82●  47M  …   │ │
│  │ │ ☑ Pharma│  │ Beta Pha  432.. 21.20  91●  124M ⚠️  │ │
│  │ │ Dept    │  │ ...                                   │ │
│  │ │ Effectif│  │ [Hover row → preview Sheet droite]    │ │
│  │ └─────────┘  └────────────────────────────────────────┘ │
│  │              [Pagination keyset · Cursor next]          │
└──┴──────────────────────────────────────────────────────────┘
```

**Sidebar gauche (Filters panel)** :
- Glass card sticky `top: 80px`
- Sections : Score / Secteur / Géo / Taille / Signaux / Compliance
- Toggles avec animations spring (Framer Motion)
- Icons Lucide colorisés par section
- Reset all en bas + count "47 filtres actifs" si > 0

**Main table** :
- Header sticky avec sort icons
- Rows alternées `bg-white/[0.01]` / transparent
- Score badge halo (emerald/amber/rose) selon range
- Hover row → overlay subtle `bg-blue-500/[0.04]` + show preview Sheet droite (300ms delay)
- Click denomination → navigate to fiche
- Right-click → context menu (Save / Compare / Add to list / Export PDF)
- **Number formatting** : `47M €` (compact), `1.2 Md €` (compact bn), `1,247` (count tabular-nums)

**Footer table** :
- Total count + median score + cursor pagination
- Bouton "Load more" avec spinner gradient
- Skeleton 5 rows pendant fetch

### 2. **Fiche Entreprise** (drill-down)

Layout 3 colonnes :
```
┌─Tabs vertical─┬─────Main 800px─────┬─Activity sidebar──┐
│ • Overview    │ ╔═══════════════╗  │ Suivi équipe       │
│   Dirigeants  │ ║ ACME SAS      ║  │ ◯ Alice viewed it  │
│   Signaux M&A │ ║ siren 838...  ║  │ ◯ Bob added note   │
│   Finances    │ ║ Score 82 🟢   ║  │                    │
│ ⚠ Compliance  │ ║ [● Suivre]    ║  │ Mes notes          │
│   Contentieux │ ╚═══════════════╝  │ ┌────────────────┐ │
│   Marchés pub │  KPI cards 4 cols  │ │ ...            │ │
│   Réseau      │  Mini-map + tabs   │ └────────────────┘ │
└───────────────┴─────────────────────┴────────────────────┘
```

**Header card** :
- Big denomination (Geist Mono 36px)
- Below : SIREN (mono) + statut pill + date_creation
- Score badge XL avec halo (signature ring effect)
- Action buttons : "Suivre" (toggle), "Compare", "Export PDF" (gradient bg)

**Tab Overview** :
- 4 KPI cards : CA dernier (count-up), Effectif, EBITDA, Capitaux propres
  Avec sparkline tendance 5 ans (Recharts mini)
- Card identité (siren, naf libellé, forme juridique, date_creation, siege_adresse)
- Mini-map siège (MapLibre, dark style "MapTiler basic-dark")
- **Score breakdown** : Recharts radar chart 9 dims (Mandats, SCI, Financier, etc.)

**Tab Signaux M&A** :
- Timeline verticale Framer Motion `staggerChildren: 0.05`
- Cartes events glassmorphism :
  - Icon gradient circulaire selon type (OPA → ⚡, fusion → 🔀, etc.)
  - Title bold + description 200 chars + source link "Voir BALO →"
  - Timestamp "il y a 2h" relative + absolu en hover tooltip
- Filtres top : severity / type / date range

**Tab Compliance** :
- 🚨 Big banner rouge si red flags HIGH (avec gradient `from-rose-500/20 to-red-500/10`)
- Liste sanctions OpenSanctions avec details JSONB expand
- Liste AMF signals (HIGH severity highlighted)
- Carte "ICIJ Offshore matches" si has_offshore_match (avec détails Panama/Pandora)
- Procédures collectives historique + flèche vers BODACC source

**Tab Réseau** :
- Embed ForceGraph2D (compact 600px) avec siren=X focused
- Click nœud → navigation

### 3. **Feed Signaux M&A** (events temps réel)

Layout :
```
┌─Filters horizontal───────────────────────────────────┐
│ Severity: [All ▾]  Type: [All ▾]  Date: [7d ▾]  …   │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│ ⚡ CRITICAL  TotalEnergies — OPA sur SunPower         │
│            "Annonce d'offre publique d'achat..."     │
│            siren 542 051 180  ·  il y a 14 min       │
│            [Source BALO ↗]  [Add to watchlist]       │
├──────────────────────────────────────────────────────┤
│ 💰 HIGH      Capgemini — Augmentation capital 250M€   │
│            ...                                        │
└──────────────────────────────────────────────────────┘
```

**Card event** :
- Icon gradient circulaire animé (subtle pulse pour CRITICAL)
- Title bold + description tronquée
- Cible (denomination cliquable) + SIREN mono
- Source link external
- Severity badge top-right avec halo
- Animation entry : `slideInFromRight 400ms`

**Stream** : TanStack Query infinite scroll + skeleton glow pendant fetch.

### 4. **Compliance / Due Diligence**

Mode rapport :
- Input large search SIREN (autocomplete trigram)
- Generate button → loader gradient particules
- Output rapport sectionnel avec ancres (sticky TOC à droite)
- Bouton "Export PDF" → génère PDF design-matched (pas un PDF moche)

### 5. **Graphe Réseau Dirigeants**

Plein écran avec contrôles flottants :
- ForceGraph2D dark theme avec rendering custom :
  - Nœuds entreprise = cercles cyan glow
  - Nœuds dirigeant = cercles amber avec halo si pro_ma_score>=70
  - Edges = lignes orange pulsantes si mandats croisés (animation flow)
- Top : search + filtre depth (1/2/3) + reset zoom
- Right panel : focus node details + co-mandataires list
- Bottom-left : legend
- Toggle "Hide unmandated" / "Show offshore matches in red"

### 6. **Copilot IA** (chat AI)

Layout chat-like, mais signature DEMOEMA :
- Bubble user droite + AI gauche avec icon gradient
- Streaming SSE word-by-word (typing effect natif Anthropic)
- Refs cliquables (siren / person_uid) → modale Sheet fiche
- Suggestions de prompts en dessous (chips cliquables)
- Avatar AI = orbe gradient animé subtil (visionOS particle)
- Input avec Cmd+Enter submit + send button avec animated glow

Suggestions starter :
- "Top 50 cibles M&A chimie spécialisée IDF, CA > 20M"
- "Compare X et Y sur 5 dimensions"
- "Dirigeants en commun entre deux groupes"
- "Cibles avec patrimoine immobilier > 5M€"

### 7. **Dashboard** (page d'accueil)

Hero plein écran :
- Aurora background subtle
- Big stat cards 4 cols (count-up animés) :
  ```
  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
  │ 1,247      │ │ 23         │ │ 3          │ │ 47K        │
  │ Cibles HOT │ │ Signaux 24h│ │ Alertes DD │ │ OSINT enrch│
  │ +12% / 7j  │ │ live ●     │ │ urgent ⚠   │ │ +200 / nuit│
  └────────────┘ └────────────┘ └────────────┘ └────────────┘
  ```
- France map heatmap (densité cibles HOT par dept) — D3 + topojson
- Top 10 secteurs activité M&A (bar chart Recharts)
- Recent signals feed (mini, click → page Feed)
- Quick search SIREN avec preview hover

---

## 🧩 Composants génériques (10 à designer)

```tsx
// 1. Score badge avec halo signature
<ScoreBadge value={82} size="md" tooltip />

// 2. Card cible compacte
<TargetCard target={target} onClick={...} />

// 3. Card événement timeline
<SignalEventCard event={event} severity="HIGH" />

// 4. Avatar dirigeant
<DirigeantAvatar person={p} showRedFlag />

// 5. Pills red flags compact
<RedFlagsBadge flags={['sanction', 'icij', 'procedure']} />

// 6. Filter panel sidebar
<FilterPanel sections={[{label, items, type}]} />

// 7. Table TanStack avec keyset pagination
<KeysetTable cursor={cursor} columns={cols} />

// 8. Breadcrumb lineage
<LineageBreadcrumb path={['Targets', 'Acme', 'Dupont']} />

// 9. Empty state élégant
<EmptyState icon={<Inbox />} title="..." description cta />

// 10. Command palette Cmd+K
<CommandPalette commands={[]} />
```

Tous avec :
- Variants (default, hover, active, disabled, loading, error)
- Props TypeScript stricts
- Storybook stories
- Tests Vitest minimal

---

## ⚙️ Interactions & Keyboard

```
⌘K        → Command palette (search global)
⌘E        → Export CSV vue actuelle
⌘N        → New alert / saved search
⌘P        → Print / Export PDF fiche
⌘\        → Toggle sidebar
/         → Focus search bar
?         → Help / shortcuts cheatsheet
Esc       → Close modal / blur input
↑↓        → Navigate table rows (highlight focus)
Enter     → Open focused row
Cmd+Enter → Submit form
Tab       → Navigate filters
```

Hover row table → preview Sheet droite après 800ms (cancel si mouseleave).

---

## 📱 Responsive

- **Desktop (≥1280px)** : 3-col layout (sidebar + main + side panel)
- **Tablet (768-1279px)** : 2-col, sidebar drawer overlay
- **Mobile (<768px)** : single col, bottom nav tabs (PWA)

PWA installable avec splash screen Lottie radar.

---

## ♿ Accessibility (WCAG AAA target)

- Keyboard navigation complète
- Focus rings visibles `ring-2 ring-blue-500/50 ring-offset-2 ring-offset-zinc-950`
- Aria labels exhaustifs sur icon-only buttons
- Contraste 7:1 (texte / bg) — déjà ok dark
- Screen reader announce sur sort change, filter change, page change
- Reduced motion : respect `prefers-reduced-motion`

---

## 🎬 Animations Framer Motion

```tsx
// Page transition
<motion.main
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -8 }}
  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }} // Apple ease
/>

// List stagger
<motion.div variants={containerVariants} initial="hidden" animate="show">
  {items.map((item, i) => (
    <motion.div key={item.id} variants={itemVariants} custom={i} />
  ))}
</motion.div>

// Hover lift
<motion.div
  whileHover={{ y: -4, scale: 1.01 }}
  transition={{ type: "spring", stiffness: 400, damping: 25 }}
/>
```

Custom easing curves :
- `--ease-spatial: cubic-bezier(0.16, 1, 0.3, 1)` (visionOS)
- `--ease-precise: cubic-bezier(0.4, 0, 0.2, 1)` (Linear)
- `--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55)`

---

## 🚀 Livrables attendus

1. **Repo Next.js 15** prêt à `pnpm install && pnpm dev`
2. **`tailwind.config.ts`** avec design tokens DEMOEMA
3. **`src/components/ui/`** : 10 composants génériques + Storybook
4. **`src/app/`** : 7 pages avec layout par défaut
5. **`src/lib/api.ts`** : client API typed (mock data)
6. **`README.md`** : design system documentation + screenshots
7. **Mock data** : top 50 cibles + 100 dirigeants + 200 events

## 🎨 Mock data réelle (utiliser pour les screenshots)

```typescript
const mockCibles: Cible[] = [
  { siren: "838291045", denomination: "Acme Industries SAS",
    naf: "24.10Z", naf_libelle: "Sidérurgie", siege_dept: "75",
    ca_dernier: 47_000_000, effectif_tranche: "100-249",
    pro_ma_score: 82, top_dirigeant: "Marc Dubois",
    has_balo_recent: false, has_compliance_red_flag: false },

  { siren: "432198765", denomination: "Beta Pharma Holding",
    naf: "21.20Z", naf_libelle: "Fabrication produits pharma",
    siege_dept: "78", ca_dernier: 124_000_000, effectif_tranche: "250-499",
    pro_ma_score: 91, top_dirigeant: "Dr Sophie Marin",
    has_balo_recent: true, has_compliance_red_flag: true,
    red_flags: ["icij_offshore_panama", "amf_listes_noires"] },

  { siren: "891234567", denomination: "Carbon Capture Tech",
    naf: "71.12B", naf_libelle: "Ingénierie études techniques",
    siege_dept: "38", ca_dernier: 8_400_000, effectif_tranche: "10-19",
    pro_ma_score: 76, top_dirigeant: "Thomas Weber",
    is_innovation_company: true, has_publications: true },

  { siren: "567891234", denomination: "Delta Patrimoine SCI",
    naf: "68.20A", naf_libelle: "Location logements", siege_dept: "92",
    ca_dernier: null, effectif_tranche: "0-9", pro_ma_score: 88,
    is_asset_rich: true, patrimoine_total_eur: 47_000_000 },

  { siren: "489123456", denomination: "Edenred France",
    naf: "64.20Z", naf_libelle: "Holdings", siege_dept: "92",
    ca_dernier: 2_100_000_000, lei: "549300...", isin: "FR0010908533",
    pro_ma_score: 79, is_listed: true, balo_operations_recent: 12 }
];

const mockSignaux: SignalEvent[] = [
  { signal_uid: "balo_2026_04_29_001",
    signal_type: "balo_operation", operation_type: "opa",
    severity: "CRITICAL", date_event: "2026-04-29T08:14:00Z",
    siren: "542051180", denomination: "TotalEnergies",
    title: "Annonce d'OPA sur SunPower Corp",
    description: "TotalEnergies dépose une offre publique d'achat...",
    source_url: "https://www.journal-officiel.gouv.fr/balo/..." },
  // ... 199 autres
];
```

---

## ✅ Checklist done

- [ ] 7 pages designées avec hover/loading/empty/error states
- [ ] 10 composants UI génériques avec props strict + Storybook
- [ ] Design tokens Tailwind v4 inline `@theme`
- [ ] Animations Framer Motion fluides (60fps)
- [ ] Glow halos signatures (score, AI, real-time)
- [ ] Aurora backgrounds subtils sur hero
- [ ] Mode dark + light optionnels
- [ ] Mobile responsive (PWA installable)
- [ ] Accessibility AAA
- [ ] Keyboard shortcuts implémentés
- [ ] Mock data réaliste (top 50 cibles + signaux)
- [ ] Code prêt à brancher sur API FastAPI DEMOEMA
- [ ] README design system + screenshots Storybook

## 🎬 Tone à éviter

❌ **Pas de** :
- Skeuomorphism (icônes 3D bloated)
- Glow excessifs partout (réservé aux signatures : score, AI, real-time)
- Animations longues (> 400ms = lent)
- Whitespace excessif (Bloomberg style = dense)
- Couleurs vives type Figma corporate (palette DEMOEMA = neon subtil sur dark)
- Stock illustrations Unsplash bateau
- Headers énormes type startup landing 2020 (h1 80px+)
- Curseurs custom type Webflow

✅ **Vise** :
- Densité info Bloomberg
- Élégance spatiale visionOS
- Précision Linear
- Vitesse Vercel
- Sobriété Anthropic Console
- Discrètes touches futuriste (glow signature, sub scan-lines, count-up nums)

---

> Briefing v1 — 29/04/2026. À itérer après premier mockup pour affiner.

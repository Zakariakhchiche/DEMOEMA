# 🎨 Prompt design DEMOEMA Front — AI-first Chat Interface

> Prompt à donner à **claude.ai/design** (ou v0.dev / lovable.dev / Bolt.new).
> Vision **TOTALEMENT REPENSÉE 29/04/2026** : passage d'un dashboard SaaS classique
> à une **interface chat-first AI-native** où l'utilisateur pose des questions et
> reçoit des fiches entreprises en réponse.

---

# 🎯 LE PRODUIT EN UNE PHRASE

> **DEMOEMA est un ChatGPT pour le M&A français** : tu poses une question naturelle
> (ou tu cherches un SIREN), l'IA te répond avec des **fiches entreprises** dénormalisées
> directement dans la conversation. Outil **simple et efficace** qui remplace
> Mergermarket / Dealogic via une UX 2030.

## Comparables

| Référence | À piquer |
|---|---|
| **Perplexity AI** | Search + sources cliquables, streaming réponse |
| **ChatGPT (canvas)** | Conversation persistante, cards inline |
| **Glean** (workplace AI) | Search d'entreprise via langage naturel |
| **Cursor / Phind** | Sidebar conversations + contexte multi-turn |
| **Linear Command Palette** | Vitesse + densité + keyboard-first |
| **Anthropic Console** | Sobriété AI-native, refs visibles |
| **Notion AI** | Inline AI dans interface productive |

---

# 🖼️ Layout principal — UNE SEULE VRAIE INTERFACE

```
┌──────────────────────────────────────────────────────────────────┐
│ DEMOEMA  ⌘K Search  Workspace ▾    🔔  Avatar                    │  56px
├────────────┬─────────────────────────────────────────────────────┤
│            │  Aurora gradient subtle background                  │
│ + New      │                                                      │
│            │     ┌──────────────────────────────────────────┐    │
│ Today      │     │  USER MESSAGE                            │    │
│ ▸ Lazard   │     │  "Cibles M&A chimie spé IDF >20M€ avec   │    │
│   bench    │     │   procédure collective récente"          │    │
│ ▸ Acme DD  │     └──────────────────────────────────────────┘    │
│ ▸ Carbon C │                                                      │
│            │     ┌──────────────────────────────────────────┐    │
│ Last 7d    │     │ ✨ AI    Voici 47 cibles matchant tes     │    │
│ ▸ ...      │     │          critères :                       │    │
│            │     └──────────────────────────────────────────┘    │
│ Last 30d   │                                                      │
│ ▸ ...      │     ┌─────────TARGET CARD ────────────────────┐     │
│            │     │ Acme SAS  ·  Score 82 ●                  │     │
│            │     │ siren 838291045  ·  CA 47M€              │     │
│ Saved      │     │ NAF 24.10Z  ·  IDF 75  ·  150 emp        │     │
│ ▸ Top IDF  │     │ Top: Marc Dubois (pro_ma 78)             │     │
│ ▸ Pharma   │     │ ⚠️ Procédure collective ouverte 12/03/26 │     │
│            │     │ [📊 Fiche]  [💾 Sauver]  [+ Compare]    │     │
│ [Settings] │     └──────────────────────────────────────────┘     │
│            │                                                      │
│            │     ┌─────────TARGET CARD ────────────────────┐     │
│            │     │ Beta Pharma Holding · Score 91 ●         │     │
│            │     │ ...                                       │     │
│            │     └──────────────────────────────────────────┘     │
│            │                                                      │
│            │     [▸ 45 autres résultats]                          │
│            │     [▸ Affiner: Score>=70 / Sans red flags / etc.]   │
│            │                                                      │
│            │     ┌──────────────────────────────────────────┐    │
│            │     │ USER MESSAGE                              │    │
│            │     │  "Compare Acme et Beta sur 5 critères"    │    │
│            │     └──────────────────────────────────────────┘    │
│            │                                                      │
│            │     [Streaming AI response with comparison table]   │
│            │                                                      │
├────────────┴─────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ 💬  Pose ta question ou recherche un SIREN...            │    │
│ │                                                           │    │
│ │  📎 [Joindre liste sirens.csv]  🔍 Filters  ⚡ Send →   │    │
│ └──────────────────────────────────────────────────────────┘    │
│  Suggestions: "Top cibles tech IDF" · "DD compliance Acme" · ... │
└──────────────────────────────────────────────────────────────────┘
```

## Layout = TROIS zones, c'est tout

1. **Sidebar gauche (260px)** : conversations + saved searches + paramètres
2. **Main center (fluide, max 920px)** : conversation + cards entreprises inline
3. **Footer fixe (input chat)** : input avec attach + filters chip + send

**C'est tout.** Pas de header complexe, pas de sidebar droite, pas de tabs. Tout passe par la conversation.

---

# 🧩 LES 4 ÉCRANS (au lieu de 7)

### 1. **Chat principal** ⭐ 90% des interactions

L'écran décrit ci-dessus. C'est où l'utilisateur passe son temps.

L'IA peut :
- Retourner des **cibles** sous forme de TargetCards inline
- Retourner des **dirigeants** sous forme de PersonCards inline
- Retourner des **comparaisons** en tables Recharts inline
- Retourner des **graphiques** (sparklines, bar charts) inline
- Retourner des **alertes compliance** en banners rouges
- Retourner du **texte synthétique** (analyse, résumé)
- **Streamer** la réponse word-by-word (SSE)
- Citer ses **sources** (siren cliquable, BODACC link, AMF link)

### 2. **Fiche détaillée** (modal Sheet ou route /target/:siren)

Quand l'utilisateur clique "Fiche" sur une card, ouverture en **Sheet droite plein écran** (overlay sur le chat) avec :
- Header : denomination XL + score halo + actions
- Contenu : tabs verticales (Overview, Dirigeants, Signaux, Compliance, Contentieux, Réseau)
- Le chat reste visible derrière (semi-blur), peut continuer la conversation pendant qu'on consulte
- ESC ferme la Sheet, retour au chat

### 3. **Graphe Réseau** (route /graph)

Plein écran ForceGraph2D — pour les sessions exploratoires "qui connaît qui".
Lien depuis chat ("@show graph") ou depuis fiche.

### 4. **Settings / Workspace** (modal)

Préférences user (theme, density, notifications, API keys EdRCF, etc.).

**C'est tout.** 4 écrans, point.

---

# 🎨 Design System (inchangé)

> Garde tout le design system de la version précédente (glassmorphism profond,
> aurora bg, score halos, animations Framer Motion, palette neon subtile sur dark,
> typo Inter + JetBrains Mono + Geist Mono).

### Palette (rappel)

```css
--bg-base: #050507;              /* presque noir absolu */
--bg-layer-1: #0a0a0d;
--bg-layer-2: #111114;
--accent-blue: #60a5fa;          /* primary */
--accent-purple: #a78bfa;        /* AI / Copilot */
--accent-emerald: #34d399;       /* score >= 70 */
--accent-amber: #fbbf24;         /* score 50-69 */
--accent-rose: #fb7185;          /* score < 30, red flags */
--accent-cyan: #67e8f9;          /* live data, real-time */
```

### Effets signatures (rappel)

1. **Glass deep** : `bg-zinc-950/40 backdrop-blur-2xl border border-white/[0.06]`
2. **Aurora bg** : radial gradients 5-10% opacity blue/purple
3. **Score halo** : ring + box-shadow gradient selon range
4. **3D depth on cards** : `rotateX(2deg) rotateY(-1deg)` on hover
5. **Number count-up** Framer Motion sur les KPIs
6. **Scan line** subtle pour real-time
7. **Animated shimmer** sur AI thinking state

---

# 🧱 Components UI (5 essentiels seulement)

```tsx
// 1. Message bubble (USER vs AI avec orbe gradient)
<ChatMessage role="user|ai" content={...} streaming={false} />

// 2. Target card inline (apparaît dans la conversation)
<TargetCard
  target={target}
  variant="inline" // dans le chat
  onView={() => openSheet(target)}
  onSave={() => addToWorkspace(target)}
  onCompare={() => addToCompareList(target)}
/>

// 3. Person card inline (dirigeant)
<PersonCard person={p} variant="inline" />

// 4. Chat input avec attachments + filters chips + send
<ChatInput
  onSubmit={(prompt, attachments, filters) => ...}
  suggestions={["Top cibles tech IDF", "DD Acme", ...]}
/>

// 5. Conversation sidebar
<ConversationsSidebar
  conversations={[...]}
  groupBy="date" // Today, Last 7d, Last 30d
  savedSearches={[...]}
  onNew={() => ...}
/>
```

Plus 1 component pour la fiche détaillée (Sheet overlay) et 1 pour le graphe.

**Total : 5-7 composants UI**, pas 10+.

---

# 💬 Pattern de conversation (UX critique)

### Exemples de prompts → réponses

#### Exemple 1 — Search cibles
```
USER: "Top cibles M&A chimie spécialisée IDF avec CA > 20M€"

AI: J'ai trouvé 47 cibles correspondant à tes critères.
    [Stream les 5 premières cards inline]

    [TargetCard 1] Acme Industries SAS · Score 82 · CA 47M€
    [TargetCard 2] Beta Chimie SA · Score 79 · CA 35M€
    [TargetCard 3] ...

    💡 Veux-tu affiner par :
    [Score >= 70] [Sans red flags] [Avec dirigeant 60+] [Holding patrimoniale]

    [Voir 42 autres résultats ↓]
```

#### Exemple 2 — Recherche directe SIREN
```
USER: "838291045"

AI: Acme Industries SAS détectée.
    [TargetCard avec preview]

    💡 Demande :
    [📊 Fiche complète]  [👥 Dirigeants]  [⚖️ DD Compliance]
    [📈 Évolution finance]  [🌐 Réseau]
```

#### Exemple 3 — Comparaison
```
USER: "Compare Acme et Beta sur 5 critères"

AI: Voici la comparaison Acme vs Beta :
    [Comparison table inline]
    │ Critère      │ Acme   │ Beta    │
    │──────────────│────────│─────────│
    │ pro_ma_score │ 82 🟢  │ 91 🟢   │
    │ CA 2025      │ 47M€   │ 124M€   │
    │ EBITDA       │ 8.2M€  │ 18.5M€  │
    │ Effectif     │ 150    │ 280     │
    │ Red flags    │ Aucun  │ ⚠️ ICIJ │
    [Mini bar chart inline]

    Recommandation : Acme moins risqué (no red flag), mais Beta a 2.6x le CA
    → arbitrer selon mandat client.
```

#### Exemple 4 — Question complexe (multi-step)
```
USER: "Trouve-moi des dirigeants 60+ avec holding patrimoniale dans le Var
       qui ont eu un événement BODACC récent"

AI: J'analyse 8M dirigeants INPI...
    [Streaming progress: "Filtrage age... patrimoine SCI... croisement BODACC..."]

    Trouvé 23 dirigeants matchant.

    [PersonCard 1] Jean Dupont (62a) · 4 mandats · 3 SCI · BODACC: cession 03/26
    [PersonCard 2] ...

    💡 Affiner par :
    [Score >=70] [Avec contentieux] [Cotée]
```

### Streaming UX

- **Réponse texte** : word-by-word (SSE Anthropic style)
- **Cards** : apparaissent une par une avec stagger 100ms (Framer Motion)
- **AI orbe** : pulse subtle pendant streaming (gradient)
- **"Thinking..."** : barre de progression gradient si > 2s

### Suggestions intelligentes

Sous le chat input :
- **Au démarrage** : "Top cibles tech IDF" / "DD Acme" / "Comparer X et Y"
- **Après une réponse** : suggestions contextuelles ("Affiner par dept" / "Voir compliance")
- **Sur sélection** : si user a sauvé 5 cibles → "Compare ces 5 cibles" / "Export CSV"

---

# ⚡ Interactions clés (KEYBOARD-FIRST)

```
⌘K        → Command palette (search global, switch conversation)
⌘N        → Nouvelle conversation
⌘Enter    → Submit prompt
⌘L        → Focus chat input
⌘B        → Toggle sidebar
/         → Mode raccourcis : "/siren XXXX", "/score>70", "/compare A B"
?         → Help
Esc       → Ferme Sheet / blur input
↑↓        → Navigate conversation history
Enter     → Open focused card
Cmd+Enter → Open card en Sheet
```

---

# 📝 Mode "/" commands (puissant)

Dans le chat input, taper `/` ouvre un menu de commands rapides :

```
/siren 838291045           → Recherche directe
/compare 838291045 432198765 → Comparaison
/save                      → Sauver dernière liste
/export csv                → Export CSV résultats
/dd 838291045              → Due diligence rapide
/graph 838291045           → Ouvre graphe réseau
/clear                     → Clear conversation
/settings                  → Settings
```

Comme dans Linear / Notion.

---

# 🚀 Comportement intelligent

### L'IA comprend les requêtes en langage naturel

L'IA route automatiquement vers les bons gold tables :

| User dit... | L'IA query... |
|---|---|
| "cibles M&A" | gold.cibles_ma_top |
| "dirigeants" | gold.dirigeants_master |
| "événements" | gold.signaux_ma_feed |
| "sanctions" | gold.compliance_red_flags |
| "réseau" | gold.network_mandats |
| "patrimoine immo" | gold.parcelles_cibles |
| "marchés publics" | gold.marches_publics_unifies |
| "presse" | silver.press_mentions_matched |
| "réformes" | gold.veille_reglementaire |

### Sources visibles (trust)

Chaque card / réponse cite ses sources :
- `siren 838291045` → cliquable vers source INPI RNE
- `BODACC 03/26` → link OpenData
- `Score 82` → tooltip explique : "+10 pro_ma, +20 holding, +15 financier..."

L'utilisateur peut **toujours auditer** d'où vient l'info. Pas de blackbox.

---

# 📱 Responsive

- **Desktop ≥1024px** : layout 3 zones (sidebar + chat + footer)
- **Tablet 768-1023px** : sidebar drawer overlay, chat full-width
- **Mobile <768px** : single column, bottom nav (Chat / Fiches sauvées / Profile)

PWA installable. Notifications push pour alertes compliance HIGH.

---

# 🚀 Stack & Livrables

```yaml
framework: Next.js 15 App Router + React 19 Server Components
ui: Tailwind v4 + shadcn/ui + Framer Motion 11
chat: Vercel AI SDK pour streaming + Anthropic Claude (côté backend)
state: TanStack Query + Zustand (conversations local)
fonts: Inter + JetBrains Mono + Geist Mono
graphs: Recharts (inline charts) + ForceGraph2D (graphe page)
```

## Livrables claude.ai/design

1. **Repo Next.js 15** complet `pnpm install && pnpm dev`
2. **Design tokens** Tailwind v4 inline `@theme`
3. **5-7 composants UI** + Storybook stories
4. **4 écrans** : Chat principal / Fiche Sheet / Graphe / Settings modal
5. **Mock conversations** réalistes avec stream factice (setTimeout)
6. **README** : design system + screenshots
7. **Mock data** : top 50 cibles + 100 dirigeants + 50 événements

## Mock conversations à générer

```typescript
const mockConversations: Conversation[] = [
  {
    id: "conv_1",
    title: "Cibles chimie IDF",
    last_at: "2026-04-29T08:14:00Z",
    messages: [
      { role: "user", content: "Top cibles M&A chimie spécialisée IDF >20M€" },
      { role: "ai", content: "47 cibles trouvées...",
        cards: [acmeMock, betaMock, gammaMock] }
    ]
  },
  {
    id: "conv_2",
    title: "DD Acme Industries",
    last_at: "2026-04-29T07:30:00Z",
    messages: [
      { role: "user", content: "/dd 838291045" },
      { role: "ai", content: "Due diligence Acme Industries SAS...",
        cards: [acmeFullMock], compliance: { red_flags: [], ok: true } }
    ]
  },
  // ... 8-10 autres
];
```

---

# 🎯 Critères de succès

L'utilisateur doit pouvoir :

✅ **Trouver une cible en < 30 secondes** via une question naturelle
✅ **Comparer 2-5 cibles en 1 message** avec table + viz inline
✅ **Faire une DD compliance en 1 prompt** + export PDF en 1 clic
✅ **Sauver et retrouver ses recherches** via sidebar conversations
✅ **Tout faire au clavier** (zéro souris si voulu)
✅ **Mode mobile** : poser la même question depuis téléphone
✅ **Auditer chaque info** : sources cliquables, scores explicables

---

# 🚫 Tone à éviter

- ❌ Dashboard SaaS classique avec 12 widgets KPIs (boring 2020)
- ❌ Sidebar nav avec 15 items (cognitive overload)
- ❌ Tableaux Excel-like (Mergermarket 2008)
- ❌ Header géant type startup landing
- ❌ Onboarding modal de 8 étapes
- ❌ Tooltips partout (clutter)
- ❌ Couleurs primaires saturées Salesforce
- ❌ Feature creep (Saved searches + watchlists + alerts + reports + ...)

# ✅ Tone à viser

- ✅ **ChatGPT premium pour le M&A français** = simplicité absolue
- ✅ Une seule question = une seule réponse claire
- ✅ Cards inline = preview rapide, click = deep-dive
- ✅ Sidebar = juste l'historique conversations (pas plus)
- ✅ Vitesse > complétude (Linear feel)
- ✅ AI explique, source, audite
- ✅ Keyboard-first toujours

---

# 📐 Mock screen final attendu (description)

> Imagine **Perplexity AI**, mais :
> - Au lieu de retourner des résultats web, l'IA retourne des **fiches entreprises FR** dénormalisées
> - Au lieu de citer des URLs Wikipedia, l'IA cite des **siren INPI + BODACC + AMF + DILA**
> - Au lieu d'être généraliste, c'est un **expert M&A boutique français**
> - Le tout dans une UI **sombre, glassmorphique, futuriste** mais **dense comme Bloomberg**
> - Avec une **vitesse de Linear** et la **sobriété d'Anthropic**

C'est ça DEMOEMA Front v2.

---

> Brief v2 — 29/04/2026. Repensé pour AI-first chat-driven UX.
> Iter à donner à claude.ai/design pour mockup initial.

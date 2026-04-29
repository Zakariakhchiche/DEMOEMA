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

---

# 🚀 INNOVATIONS 2026 (intégrées au brief — issus veille UX/UI SaaS)

Suite à veille SaaS UX/UI 2026 (sources : SaaSUI Blog, Orbix Studio, RankTracker, B2B mention G2, Averi, Linear gold standard, etc.), ajout de **3 patterns innovants sous-exploités** par les SaaS M&A actuels (Mergermarket, Dealogic, PitchBook) que DEMOEMA peut claim comme différenciateurs.

## Innovation #1 — **Adaptive UI** (interface auto-personnalisée)

> *"Adaptive UI is where the interface builds itself based on your data, history, patterns and inputs at the time, creating what should be the best possible experience."* — UX Tigers 2026

### Concept
Après 2 semaines d'usage, l'interface DEMOEMA s'adapte à **Anne Dupont** :
- Son top 3 actions devient des **shortcuts épinglés** dans le chat input
- Les cartes affichent en priorité les **champs qu'elle consulte le plus** (DD compliance ? Score patrimoine ? Réseau ?)
- Le chat suggère des prompts basés sur son **historique** ("Comme tu as fait DD Acme la semaine dernière, voici DD Beta — secteur similaire")
- La sidebar Conversations groupe par **patterns réels** (DD / Sourcing / Comparaison) pas juste par date

### Implémentation UI

```tsx
// Chat input avec shortcuts personnalisés (top 3 actions Anne)
<ChatInput>
  <PinnedShortcuts>
    <Chip icon="🛡️">DD compliance ⌘D</Chip>
    <Chip icon="🔍">Sourcing IDF chimie ⌘S</Chip>
    <Chip icon="📊">Compare cibles ⌘K</Chip>
  </PinnedShortcuts>
  <Input placeholder="Pose ta question..." />
</ChatInput>
```

```tsx
// TargetCard adaptative — ordre des champs selon usage user
<TargetCard target={target} userPreferences={anne}>
  {/* Anne consulte 90% du temps : score, red flags, top dirigeant */}
  <ScoreBadge value={target.pro_ma_score} />
  {target.compliance_red_flags > 0 && <RedFlagsBadge />}
  <TopDirigeant person={target.top_dirigeant} />
  {/* Champs secondaires : compact, expand on click */}
  <ExpandableSection>
    <FinanceBlock />
    <NetworkBlock />
  </ExpandableSection>
</TargetCard>
```

### Backend
- Stocker `user_preferences` (JSONB) avec :
  - `top_actions` array (DD, sourcing, compare, etc.)
  - `top_fields_viewed` (score, red_flags, ca, dirigeants, etc.)
  - `last_searches` (10 derniers prompts)
- LLM prompt incluant `user_context` pour personnalisation

---

## Innovation #2 — **Mode "Pitch Ready"** (PDF présentable en 1 clic)

### Pain point M&A boutique
Anne passe **2-4h par cible** à compiler manuellement les infos pour son livrable client. Mergermarket export = CSV brut moche.

### Solution DEMOEMA
Bouton "📄 Pitch Ready" sur chaque card / fiche → PDF design-matched (charte EdRCF) en **5 secondes** :

**Page 1 — Synthesis** :
- Header : logo client + titre "Cible M&A — [Denomination]" + date
- Score halo grand format (signature DEMOEMA)
- KPIs critiques 4 cards : CA, EBITDA, Effectif, Valorisation estimée
- Verdict 1 phrase : *"Cible HIGH potentiel pour mandat sell-side mid-cap chimie"*

**Page 2 — Identité + Finance** :
- Profil entreprise (siren, NAF, dates, siège)
- Mini-graphique évolution CA 5 ans (Recharts)
- Comparaison vs médiane secteur (benchmarks_sectoriels)
- Top 3 dirigeants (avatars + age + pro_ma_score)

**Page 3 — Compliance / Red Flags** :
- 🟢 Section "OK" si rien
- 🔴 Section "Red flags" si présents (sanctions, ICIJ, procédures)
- Auditabilité : sources avec liens BODACC/AMF/DILA

**Page 4 — Réseau** :
- Mini-graphe network_mandats (5 niveaux)
- Top co-mandataires + entreprises liées
- Patrimoine immobilier consolidé (parcelles_cibles)

**Page 5 — Annexes** :
- Liens audit (siren INPI, BODACC, BALO si coté)
- Disclaimer légal RGPD
- Footer EdRCF + date génération

### Customisation client
Anne peut personnaliser le **template** (couleurs charte EdRCF, logo, mention pro) une seule fois → toutes les générations PDF appliquent ce template.

### Stack technique
- React-PDF ou Puppeteer (HTML → PDF)
- Stockage template par workspace (Supabase storage)
- Job async (5s génération + 5s download)

### UI

```tsx
<TargetCard target={acme}>
  <Actions>
    <Button variant="primary" icon={<FileText />}>📊 Voir fiche</Button>
    <Button variant="secondary" icon={<Save />}>💾 Sauver</Button>
    <Button variant="ghost" icon={<Sparkles />}>📄 Pitch Ready</Button>
  </Actions>
</TargetCard>

// Modal Pitch Ready
<Dialog>
  <DialogHeader>Génération Pitch Cible — Acme Industries</DialogHeader>
  <ProgressBar value={progress} /> {/* gradient animated */}
  <Steps>
    <Step done>Identité + finances</Step>
    <Step done>Compliance check</Step>
    <Step done>Réseau dirigeants</Step>
    <Step active>Génération PDF charte EdRCF...</Step>
  </Steps>
  <DialogFooter>
    <DownloadLink href={pdfUrl}>📥 Télécharger PDF (1.2 MB)</DownloadLink>
  </DialogFooter>
</Dialog>
```

---

## Innovation #3 — **Proactive Alerts conversationnelles** (sticky engagement)

### Concept
Au lieu d'attendre qu'Anne demande, **DEMOEMA initie la conversation** chaque matin avec les signaux pertinents pour ses cibles sauvées.

### Exemple message AI proactif (8h00 Paris)

```
✨ DEMOEMA  ·  Bonjour Anne ☕

J'ai analysé ta watchlist "Cibles tech IDF" cette nuit.

🚨 3 alertes prioritaires :

[Card] Acme Industries SAS · Score 82 → 78 (-4)
       ⚠️ Procédure collective ouverte au Tribunal de commerce
       Nanterre le 28/04/26. Source : BODACC.
       [Voir détail]  [Désabonner]

[Card] Beta Pharma Holding · BALO event 24h
       💰 Augmentation de capital 15M€ annoncée 28/04/26.
       Tier-1 par rapport à ton historique sourcing pharma.
       [Voir détail]  [Ajouter au mandat]

[Card] Carbon Capture Tech · Nouveau dirigeant
       👤 Jean Dupont (ex-Engie) nommé président le 26/04/26.
       Parcours pertinent pour ton mandat deeptech.
       [Voir détail]  [Réseau Jean Dupont]

📊 Stats :
- 47 nouveaux signaux 24h sur tes cibles
- 12 cibles ont franchi le seuil score 70+ (tier 1)
- 0 nouveau red flag majeur

💡 Suggestion : on regarde ensemble le mandat sell-side
   Beta Pharma ce matin ?  [Lancer DD complète]
```

### Mécanique

**Cron 06:00 Paris** :
1. Pour chaque user : query saved searches + watchlists
2. Run AI analysis sur les 24h précédentes (silver.signaux_ma_feed depuis last_login)
3. Génère un message proactif personnalisé via LLM (avec context de l'historique)
4. Inject dans la conversation "Today" sidebar (badge unread)

### Notifications

- Badge rouge sur sidebar conversation
- Push notification PWA si configuré
- Email digest si user `notif_email_digest = true`

### Anti-spam
- Cap 1 message proactif / 24h max
- Skip si user n'a pas ouvert l'app depuis 7 jours (re-engagement séparé)
- User peut désactiver par watchlist

### UI

```tsx
<ConversationSidebar>
  <SectionHeader>Today</SectionHeader>
  <ProactiveAlertBadge variant="new">
    <SparkleIcon className="animate-pulse" />
    <Title>3 alertes du matin</Title>
    <Subtitle>Acme · Beta Pharma · Carbon Capture</Subtitle>
    <Time>il y a 14 min</Time>
  </ProactiveAlertBadge>
  {/* ... autres conversations */}
</ConversationSidebar>
```

---

## Innovation #4 — **Density Mode toggle** (compact / comfortable / spacious)

Bouton dans Settings → adapte la densité de toutes les cards.

### Compact (default Anne mode — 80% des users)
- TargetCard hauteur 64px
- 8 cards visibles dans viewport 1080p

### Comfortable
- TargetCard hauteur 96px
- 5 cards visibles

### Spacious
- TargetCard hauteur 128px (présentation client live)
- 3 cards visibles

```tsx
const DensityContext = createContext<"compact" | "comfortable" | "spacious">("compact");

<ToggleGroup value={density} onValueChange={setDensity}>
  <ToggleGroupItem value="compact" aria-label="Compact">⊟</ToggleGroupItem>
  <ToggleGroupItem value="comfortable" aria-label="Comfortable">⊞</ToggleGroupItem>
  <ToggleGroupItem value="spacious" aria-label="Spacious">⊠</ToggleGroupItem>
</ToggleGroup>
```

---

## Innovation #5 — **Quick replies contextuelles auto-générées**

Après chaque réponse AI, des chips de suggestions apparaissent automatiquement basées sur le contexte de la conversation.

### Exemple

```
USER: "Top cibles M&A chimie spé IDF"

AI: [retourne 47 cards]

[Quick replies auto-générées par LLM]
[Affiner par effectif] [Sans procédure collective]
[Ajouter compliance check] [Voir top 10 dirigeants]
[Compare top 3] [Export en watchlist]
```

Click sur un chip → injection automatique dans le prompt suivant.

```tsx
<QuickReplies>
  {generatedSuggestions.map(s => (
    <Chip onClick={() => sendMessage(s.prompt)}>{s.label}</Chip>
  ))}
</QuickReplies>
```

LLM génère ces suggestions en **post-processing** (cheap call, ~50ms) après la réponse principale.

---

## Innovation #6 — **Memory / RAG sur conversations passées**

Le LLM a accès à l'historique des conversations Anne (RAG via embeddings) :

```
USER: "Tu te souviens de la cible chimie qu'on regardait il y a 2 semaines ?"

AI: Oui, tu travaillais sur Acme Industries SAS (siren 838291045).
    Voici les nouveautés depuis :

    [Card avec deltas mis en évidence]
    - Score : 82 → 78 (procédure collective récente)
    - 1 nouveau dirigeant (Jean Dupont, 26/04/26)
    - CA n'a pas encore évolué (déposé annuellement)

    Tu veux qu'on poursuive la DD ou on switch vers une autre cible ?
```

### Stack
- Vector store (pgvector dans Postgres) — embeddings sentences-transformers
- À chaque message, embed + insert dans `user_conversation_embeddings`
- Retrieve top 5 closest avant génération réponse → inject dans prompt

---

## Innovation #7 — **Voice mode** (mobile-first PWA)

Pendant qu'Anne marche entre 2 RDV à La Défense, elle peut **parler** à DEMOEMA depuis son iPhone :

```
🎙️ Anne (audio) : "Donne-moi le scoring de Capgemini"
🔊 AI (voice) : "Capgemini score 79, listée CAC40, CA 22 milliards,
                  pas de red flag majeur. Tu veux la fiche complète ?"
```

Stack :
- Web Speech API (mobile)
- Whisper (transcription serveur fallback)
- Anthropic Claude voice (output) ou ElevenLabs

---

## Innovation #8 — **Compare mode multi-cibles** (drag&drop ou shift+click)

Anne sélectionne 2-5 cards via shift+click → sticky bouton "Compare 3 cibles" apparait en bas → click ouvre vue Compare inline dans le chat avec table + radar chart 9 dimensions.

```tsx
<SelectedCardsBar visible={selectedCount > 0}>
  <span>{selectedCount} cibles sélectionnées</span>
  <Button onClick={openCompare} variant="primary">
    Compare {selectedCount} cibles
  </Button>
</SelectedCardsBar>
```

---

## Innovation #9 — **Watchlists collaboratives** (slack-like)

Anne crée "Cibles tech IDF Q3" → partage via lien (`/w/abc123`) avec son équipe. Les notifications signaux M&A sont synchronisées entre tous les membres.

```tsx
<WatchlistHeader>
  <Title>Cibles tech IDF Q3</Title>
  <Members>👤👤👤 +2</Members>
  <Button onClick={share}>🔗 Partager</Button>
  <NotificationToggle>🔔 Alertes ON</NotificationToggle>
</WatchlistHeader>
```

---

## Innovation #10 — **AI Explainability** (tooltip sur chaque score)

Anne hover sur un `pro_ma_score` → tooltip explique la formule :

```
┌─ Score 82 ────────────────────┐
│ +20 has_holding_patrimoniale   │
│ +15 ca_total = 47M€            │
│ +10 is_pro_ma (12 mandats)     │
│ +10 has_cession_recente        │
│ +5  has_press_buzz             │
│ -3  contentieux récent (1 jug.)│
│ -5  age dirigeant 65+ (Tier 2) │
│ ─────────────────────────────  │
│ = 82 / 100                     │
│ [Voir détail formule complète] │
└────────────────────────────────┘
```

Stack : tooltip Radix UI + breakdown JSONB stocké dans `gold.entreprises_master.score_breakdown`.

---

## 🎯 Résumé des 10 innovations à intégrer

| # | Innovation | Effort | Impact |
|---|---|:---:|:---:|
| 1 | Adaptive UI (shortcuts personnalisés) | M | 🔥🔥 |
| 2 | Pitch Ready PDF en 1 clic | L | 🔥🔥🔥 |
| 3 | Proactive alerts conversationnelles | M | 🔥🔥🔥 |
| 4 | Density mode toggle | S | 🔥 |
| 5 | Quick replies auto-générées | S | 🔥🔥 |
| 6 | Memory / RAG conversations passées | M | 🔥🔥 |
| 7 | Voice mode PWA mobile | L | 🔥 |
| 8 | Compare mode multi-cibles | S | 🔥🔥 |
| 9 | Watchlists collaboratives | M | 🔥🔥 |
| 10 | AI Explainability tooltip scores | S | 🔥 (mais critique pour trust) |

**Priorisation** :
- **MVP v1** : #2 Pitch Ready + #3 Proactive alerts + #5 Quick replies + #10 AI Explainability
- **MVP v2** : #1 Adaptive UI + #6 Memory + #8 Compare mode
- **v3+** : #4 Density + #7 Voice + #9 Watchlists collaboratives

Ces 10 innovations + le design system glassmorphism futuriste = **moat concurrentiel** vs Mergermarket / Dealogic / PitchBook.

---

# 🗄️ DATA EXPLORER MODE — accès direct aux tables (ajout v3)

## Pourquoi
DEMOEMA stocke **512 GB / 115 bronze / 29 silver MV / 13 gold tables**. Une interface chat-first
ne permet pas de **tout** explorer. Pour les power users (advisors expérimentés, analysts,
compliance officers), il faut un **mode Data Explorer** qui complète le chat.

**Anne** utilise le chat 80% du temps. Mais 20% du temps elle veut :
- Voir TOUTES les colonnes d'une cible (chat ne montre que les highlights)
- Faire des queries custom SQL-like sans connaître SQL
- Exporter un dataset complet pour ML / Excel custom
- Comparer 50 cibles (pas 5)

## Layout — Toggle entre Chat et Data Explorer

Cmd+Shift+E (ou icon 📊 dans la sidebar) → switch entre les 2 modes.

```
┌──────────────────────────────────────────────────────────────────┐
│ DEMOEMA  💬 Chat | 📊 Explorer  Workspace ▾  🔔  Avatar          │  56px
├────────────┬─────────────────────────────────────────────────────┤
│            │                                                      │
│ Tables     │  ┌─Table Browser──────────────────────────────────┐ │
│            │  │ gold.entreprises_master · 5,123,456 rows  ⚙️   │ │
│ ▾ Bronze   │  └─────────────────────────────────────────────────┘ │
│   115 tab  │                                                      │
│            │  ┌─Filters bar─────────────────────────────────────┐│
│ ▾ Silver   │  │ score>=70  naf=24.10Z  dept=75  ☓ 47 active    ││
│   29 MV    │  └─────────────────────────────────────────────────┘│
│            │                                                      │
│ ▾ Gold ⭐  │  ┌─Data table virtualisée────────────────────────┐  │
│   ▸ entrep │  │ siren  denomination  naf   ca_dernier  score │  │
│   ▸ dirige │  │ 838.. Acme Industri 24.10  47M€       82●    │  │
│   ▸ cibles │  │ 432.. Beta Pharma   21.20  124M€     91●    │  │
│   ▸ signau │  │ 891.. Carbon Captu  71.12  8.4M€      76●    │  │
│   ▸ red_fl │  │ ... 47 rows                                  │  │
│   ▸ juridi │  └────────────────────────────────────────────────┘ │
│   ▸ networ │                                                      │
│   ▸ contac │  ┌─Aggregations bar───────────────────────────────┐│
│   ...      │  │ Σ 47 cibles · Median CA 32M · Median score 78  ││
│            │  └─────────────────────────────────────────────────┘│
│ Saved views│                                                      │
│ ▸ Top tech │  [Export CSV] [Export Parquet] [Save view] [+ Compare] │
│ ▸ DD ready │                                                      │
└────────────┴─────────────────────────────────────────────────────┘
```

## Composants Data Explorer

### 1. **Table tree sidebar** (gauche, 260px)

```tsx
<TableTreeSidebar>
  <Section label="Bronze (115 tables, 512 GB)" defaultOpen={false}>
    <Group label="INPI">
      <Table name="inpi_dirigeants_*" rows="8.1M" size="13 GB" />
      <Table name="inpi_comptes_*" rows="6.3M" size="14 GB" />
      ...
    </Group>
    <Group label="DILA">...</Group>
    <Group label="OSINT">...</Group>
  </Section>

  <Section label="Silver (29 MV)" defaultOpen={false}>
    {silverTables.map(t => <Table name={t.name} rows={t.rows} />)}
  </Section>

  <Section label="Gold (13 tables) ⭐" defaultOpen={true}>
    <Table name="entreprises_master" rows="5.1M" highlighted />
    <Table name="dirigeants_master" rows="8.1M" highlighted />
    <Table name="cibles_ma_top" rows="123K" highlighted />
    ...
  </Section>

  <Section label="Saved views" defaultOpen={true}>
    <SavedView name="Top tech IDF" filters={...} />
    <SavedView name="DD ready cibles" filters={...} />
  </Section>
</TableTreeSidebar>
```

Click sur une table → ouvre le Table Browser principal.

### 2. **Visual Query Builder** (no SQL knowledge needed)

Au-dessus du tableau, une **filter bar** intuitive (style Notion / Airtable) :

```tsx
<FilterBar>
  <FilterChip column="score_ma" operator=">=" value={70} />
  <FilterChip column="naf" operator="=" value="24.10Z" />
  <FilterChip column="siege_dept" operator="IN" value={["75", "92", "78"]} />
  <FilterChip column="ca_dernier" operator="BETWEEN" value={[10_000_000, 100_000_000]} />
  <Button onClick={addFilter}>+ Add filter</Button>
</FilterBar>
```

Chaque chip est éditable inline (popover avec :
- Column selector (autocomplete)
- Operator (=, !=, >=, <=, BETWEEN, IN, NOT IN, IS NULL, IS NOT NULL, ILIKE)
- Value input (typed selon column type)

### 3. **Data Table virtualisée** (TanStack Table)

```tsx
<DataTable
  data={rows}
  columns={cols}
  virtualization={{ rowHeight: 36, overscan: 10 }}
  pagination={{ pageSize: 100, mode: "keyset" }}
  sorting={{ multi: true }}
  selection={{ mode: "multi", showCheckboxes: true }}
  columnVisibility={{ controllable: true }}
  columnPinning={{ left: ["denomination"], right: ["actions"] }}
  density={density} // compact/comfortable/spacious
  onRowClick={(row) => openSheet(row)}
  onRowContextMenu={(row) => showContextMenu(row)}
/>
```

**Colonnes** : toutes celles de la table sélectionnée. User peut hide/show via column manager.
**Pagination** : keyset cursor (sub-second sur 8M rows).
**Sort** : multi-column (cmd+click pour ajouter).
**Selection** : multi-select avec checkbox → barre actions sticky en bas.

### 4. **Aggregations bar** (footer)

```tsx
<AggregationsBar>
  <Stat label="Total" value="47 cibles" />
  <Stat label="Σ CA" value="2.4 Md€" />
  <Stat label="Median score" value="78" />
  <Stat label="% red flags" value="6%" />
  {/* Custom aggregations possibles */}
  <Button onClick={addAggregation}>+ Add</Button>
</AggregationsBar>
```

User peut ajouter : count distinct, sum, avg, median, p25, p75, percentile custom.

### 5. **Saved Views** (dashboards perso)

User configure une vue → save avec nom + tags → réutilisable :

```tsx
<SavedView>
  <Title>Top tech IDF</Title>
  <Filters>
    score >= 70, naf IN ('62.01Z', '62.02A'), siege_dept = '75'
  </Filters>
  <Sorting>score_ma DESC, ca_dernier DESC</Sorting>
  <Columns>siren, denomination, score, ca, top_dirigeant</Columns>
  <Aggregations>count, sum_ca, median_score</Aggregations>
  <Density>compact</Density>
</SavedView>
```

Saved views sont partageables (lien `/v/abc123`) avec l'équipe EdRCF.

### 6. **Bulk actions sticky bar** (quand selection > 0)

```tsx
{selectedCount > 0 && (
  <StickyBulkActionsBar>
    <span>{selectedCount} selected</span>
    <Button>📊 Compare</Button>
    <Button>💾 Save to watchlist</Button>
    <Button>📄 Pitch Ready (batch PDF)</Button>
    <Button>🔗 Share link</Button>
    <Button>📤 Export CSV</Button>
    <Button>🛡️ DD Compliance batch</Button>
  </StickyBulkActionsBar>
)}
```

### 7. **Export panel** (CSV, Parquet, Excel, JSON)

```tsx
<ExportPanel>
  <Format options={["csv", "xlsx", "parquet", "json"]} default="csv" />
  <Encoding options={["utf-8", "latin-1"]} default="utf-8" />
  <Delimiter options={[",", ";", "tab"]} default=";" /> {/* FR-friendly */}
  <Range options={["all_filtered (47)", "selected (5)", "current_page (100)"]} />
  <Columns selectable />
  <Button onClick={download}>Download</Button>
</ExportPanel>
```

Export Parquet pour les data scientists. Excel pour les compliance officers.

### 8. **SQL mode** (power user, optionnel)

Toggle "SQL" dans la filter bar → ouvre un éditeur SQL avec :
- Autocomplete schémas (bronze.*, silver.*, gold.*)
- Highlighting Postgres syntax
- Run button → résultat affiché dans le DataTable
- Save query (persisté en saved views)

```tsx
<SQLEditor>
  <Monaco
    language="postgresql"
    theme="vs-dark"
    autocomplete={dbSchema}
    onRun={(query) => executeAndDisplay(query)}
  />
</SQLEditor>
```

Sécurité : queries READ-ONLY (interdire INSERT/UPDATE/DELETE/DROP côté backend).

---

## Use cases Data Explorer

### Use case 1 — Compliance officer audit
"Donne-moi toutes les cibles M&A avec **un dirigeant ICIJ Offshore**" :
- Click `gold.persons_master_universal`
- Add filter `has_offshore_match = true`
- Add filter `pro_ma_score >= 50`
- 23 rows displayed
- Bulk action "DD Compliance batch" → 23 PDFs en 1 clic

### Use case 2 — Data scientist M&A
"Export tous les `gold.entreprises_master` IDF tech pour entraîner un modèle de scoring custom" :
- Click `gold.entreprises_master`
- Filter `siege_dept IN ('75','92','78','93','94')` + `naf LIKE '62.%'`
- 12K rows
- Export Parquet → fichier 50 MB
- Branche dans Jupyter / SageMaker

### Use case 3 — Sales prospection direct mail
"Liste 1000 dirigeants Tier 1 avec email validé pour outreach Q3" :
- Click `gold.persons_contacts_master`
- Filter `pro_ma_score >= 60` + `has_email = true` + `emails_validated_count > 0`
- Sort by `pro_ma_score DESC`
- Limit 1000
- Export CSV (prenom, nom, top_email, denomination, score)

### Use case 4 — Boutique advisor benchmark
"Compare 50 cibles sectorielles biotech" :
- Click `gold.cibles_ma_top`
- Filter `naf LIKE '21.%'`
- Sort by `score_ma DESC` Limit 50
- Select all (Ctrl+A)
- Bulk "Compare" → vue side-by-side avec radar 9 dimensions superposés

---

## Modes coexistent — toggle fluide

```
Top header :  💬 Chat  |  📊 Explorer  |  🌐 Graphe
              ─────       ─────────       ──────
              actif       inactif         inactif
```

User peut switch n'importe quand. Les filtres / saved views sont partagés entre modes.

**Pattern** : on chat → AI répond avec cards → si user veut voir plus de détails → click "Voir dans Explorer" → ouvre Data Explorer avec filtres pré-appliqués correspondants.

```tsx
// Dans une réponse AI chat
<Button onClick={() => switchToExplorer({ table: "gold.cibles_ma_top",
                                           filters: aiAppliedFilters })}>
  📊 Voir les 47 résultats dans Data Explorer
</Button>
```

---

## Layout final révisé — 3 modes UI

```
1. CHAT MODE (default, 80% usage)     — outil simple Anne
   ├── Sidebar conversations
   └── Main chat + cards

2. EXPLORER MODE (20% usage)           — power user direct DB access
   ├── Sidebar table tree + saved views
   └── Main : filters + data table + aggregations + bulk actions

3. GRAPHE MODE (5% usage)              — exploration réseau
   ├── ForceGraph2D plein écran
   └── Sidebar focus details
```

## Composants supplémentaires Data Explorer (5 nouveaux)

```tsx
// Components à designer en plus des 5 du mode Chat
<TableTreeSidebar tables={schema} />
<FilterChip column op value editable />
<DataTable virtualized columns rows />
<AggregationsBar stats />
<SQLEditor query onRun />
```

Total composants UI = **5 chat + 5 explorer = 10 components**.

## Critères de succès UX Data Explorer

✅ User peut **trouver une row dans 8M dirigeants en < 3 secondes** (filter + sort)
✅ Export 100K rows → CSV en < 10 secondes
✅ User non-SQL peut faire des queries complexes via le visual builder
✅ Saved views partageables avec équipe EdRCF
✅ Bulk actions sur 100+ rows fluides
✅ Mobile : Data Explorer dégradé (table → cards verticales)

---

## 🎯 Récap final — 3 modes pour 3 use cases

| Mode | User profile | Use case primary |
|---|---|---|
| **💬 Chat** | Anne (associate) | "Trouve-moi des cibles" — questions naturelles |
| **📊 Explorer** | Power user (analyst, compliance) | "Browse 8M dirigeants" — direct DB access |
| **🌐 Graphe** | Tous (exploration) | "Qui connaît qui ?" — réseau visuel |

C'est la **bonne architecture** pour DEMOEMA.

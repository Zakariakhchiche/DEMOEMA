# BUDGET & ÉQUIPE — V2 (salaires Paris tech actualisés)

> ⚠️ **Document V2 — pour les chiffres canoniques, voir [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md)** (source unique de vérité post-audit 2026-04-17).
>
> Décisions verrouillées : [`DECISIONS_VALIDEES.md`](./DECISIONS_VALIDEES.md)
> État réel : [`REPONSES_SELF_CHALLENGE.md`](./REPONSES_SELF_CHALLENGE.md)
>
> ⚠️ **Calendrier** : Y1 2026 démarre **en avril 2026** (pas janvier) — équipe complète prévue pour octobre 2026.
>
> Plan financier révisé avec salaires marché réels, contingence, et hypothèses plus prudentes.

---

## Hypothèses clés (V2 — actualisées)

- Salaires Paris tech 2026 (sources : Codeur, Welcome to the Jungle, Glassdoor) — sensiblement supérieurs au V1
- Charges patronales : ~42% du brut → coefficient **1.42** (chargé) puis **+10% frais administratifs** (mutuelle, ticket resto, télétravail, tickets cadeaux, formation) → **coefficient final ~1.55**
- Bureau : **0€ Y1-Y2** (full remote), 100k€/an Y3, 250k€/an Y4
- Marketing : **5% revenu** Y2, **10% revenu** Y3, **12% revenu** Y4
- Frais légaux/compta : 30k€ Y1, 50k€ Y2, 100k€ Y3, 200k€ Y4
- **Contingence systématique : 15% du budget total** (réserve imprévus)

---

## Grille de salaires Paris tech 2026 (réaliste)

| Niveau | Brut annuel | Chargé (×1.55) | Equity (BSPCE) |
|---|---|---|---|
| **Junior dev (0-2 ans)** | 50-65k€ | 78-100k€ | 0.05-0.10% |
| **Mid dev (3-5 ans)** | 65-85k€ | 100-130k€ | 0.10-0.20% |
| **Senior dev (5-10 ans)** | 85-115k€ | 130-180k€ | 0.20-0.40% |
| **Staff / Lead** | 115-150k€ | 180-230k€ | 0.40-0.80% |
| **Senior Data Eng (rare)** | 100-140k€ | 155-220k€ | 0.30-0.70% |
| **Senior ML Eng (rare)** | 110-150k€ | 170-230k€ | 0.40-0.80% |
| **Head / Director** | 130-180k€ | 200-280k€ | 0.50-1.50% |
| **VP / C-level non-fondateur** | 150-220k€ | 230-340k€ | 1.0-3.0% |
| **Sales (AE B2B)** | 60-90k€ + 50% variable | 130-200k€ OTE | 0.10-0.30% |
| **CRO** | 150-200k€ + 100% variable | 350-500k€ OTE | 1.0-2.0% |
| **Designer Senior** | 70-95k€ | 110-150k€ | 0.10-0.30% |
| **Product Manager** | 75-110k€ | 115-170k€ | 0.20-0.40% |

**Important** : Lead Data Engineer expérimenté (ex-Doctrine, Pappers, Datadog) est **introuvable sous 110k€ brut Paris**. V1 disait 75k€ : c'était irréaliste.

---

## Budget détaillé annuel (V2)

### Année 1 — 2026

| Poste | Montant | Détail |
|---|---|---|
| **Équipe** | 350k€ | Founder (sans salaire ou minimum) + 4 FTE moyens |
| Infra cloud | 7k€ | Scaleway + Vercel + S3 (cf. ARCHITECTURE) |
| LLM + APIs | 5k€ | Claude limité Y1, peu d'usage |
| Outillage SaaS | 12k€ | GitHub, Linear, Notion, Slack, Sentry, Figma |
| Légal + DPO | 30k€ | Cabinet RGPD + corp + DPO externe 5-10k€/mois (urgent) |
| Comptabilité | 8k€ | Expert-comptable |
| Marketing | 15k€ | Site web, branding, content, salon CFNews |
| Voyage / events | 8k€ | Salons M&A (CFNews, France Invest) |
| Recrutement | 15k€ | LinkedIn, agences ponctuelles |
| Validation marché | 5k€ | Outils + cadeaux + pizzas (cf. VALIDATION_MARCHE.md) |
| **Sous-total** | **~455 k€** | |
| **Contingence (10%)** | **~53 k€** | Réserve imprévus |
| **Total Y1 (V3.1 aligné CSV)** | **578 k€** | Source canonique : `FINANCES_UNIFIE.md` + `modele_financier.csv` |

### Année 2 — 2027

| Poste | Montant | Détail |
|---|---|---|
| **Équipe** | 750k€ | 7-9 FTE |
| Infra cloud | 42k€ | Scale Postgres + Dagster |
| LLM + APIs | 60k€ | Copilot v1 lancé |
| Outillage SaaS | 25k€ | + Dagster Cloud, dbt, Datadog (option) |
| Légal + DPO | 50k€ | + audit RGPD complet, prep AI Act |
| Comptabilité | 15k€ | |
| Marketing | 50k€ | First Sales + content + salons |
| Recrutement | 30k€ | Plus de hires |
| Bureau | 0€ | Full remote |
| **Sous-total** | **~1.0M€** | |
| **Contingence (15%)** | **~150k€** | |
| **Total Y2** | **~1.15M€** | |

### Année 3 — 2028

| Poste | Montant | Détail |
|---|---|---|
| **Équipe** | 1.6M€ | 12-18 FTE (avec CRO + 3 AE) |
| Infra cloud | 220k€ | + ClickHouse + Neo4j + Qdrant |
| LLM + APIs | 200k€ | Copilot avancé, NLP massif |
| Outillage SaaS | 80k€ | Stack complète, observabilité |
| Légal + DPO | 100k€ | DPO interne, prep SOC2 |
| Comptabilité | 30k€ | |
| Marketing + Sales | 250k€ | 3 AE + équipe content |
| Recrutement | 80k€ | Croissance forte |
| Bureau | 100k€ | Paris ~30 postes |
| **Sous-total** | **~2.7M€** | |
| **Contingence (15%)** | **~400k€** | |
| **Total Y3** | **~3.1M€** | |

### Année 4 — 2029

| Poste | Montant | Détail |
|---|---|---|
| **Équipe** | 3.5M€ | 22-35 FTE |
| Infra cloud | 700k€ | SaaS multi-tenant + Europe |
| LLM + APIs | 400k€ | Copilot industriel |
| Outillage SaaS | 200k€ | Sales tools, support, analytics |
| Légal + DPO | 200k€ | Compliance internationale |
| Comptabilité | 50k€ | |
| Marketing + Sales | 1M€ | 5-8 AE + SDR |
| Recrutement | 150k€ | |
| Bureau | 250k€ | Paris + bureau secondaire (UK ou DE) |
| **Sous-total** | **~6.4M€** | |
| **Contingence (15%)** | **~960k€** | |
| **Total Y4** | **~7.4M€** | |

### Synthèse cumulative (V2)

| Année | Coûts | Revenus | Cash burn | Levée nécessaire |
|---|---|---|---|---|
| Y1 | 525k€ | 50-100k€ | -425k€ | 700k€ pré-amorçage |
| Y2 | 1.15M€ | 500-800k€ | -350k€ | 2M€ Seed |
| Y3 | 3.1M€ | 2-3M€ | -100k€ à équilibre | 8M€ Series A |
| Y4 | 7.4M€ | 8-15M€ | +0.6 à +7.6M€ | 0 ou Series B 20-40M€ |
| **Cumul** | **~12.2M€** | **~13-20M€** | **+0.8 à +6.8M€** | **~10.7M€ levés** |

---

## Organigramme cible par année (V2 réaliste)

### Y1 (4-5 FTE) — Bootstrap & MVP

```
Founder / CEO (équity uniquement)
├── Co-founder/CTO ou Lead Eng (1 FTE chargé)
├── Senior Backend (1)
├── Senior Frontend (1)
├── ML Engineer / Data Eng (1)
└── Designer freelance (0.3-0.5 FTE)
```

**Recrutements clés Q1-Q2 2026** :
1. **Lead Data Engineer** (110-130k€ chargé 170-200k€ — réalité marché)
2. **Senior Backend Python** (90-110k€ chargé 140-170k€)
3. **Senior Frontend Next.js** (85-105k€ chargé 130-160k€)
4. **ML Engineer NLP FR** (100-130k€ chargé 155-200k€)

### Y2 (7-9 FTE) — PMF chase

```
CEO
├── CTO
│   ├── Lead Data Engineer (1)
│   ├── Backend × 2
│   ├── Frontend × 2
│   ├── ML Engineer × 1
│   └── DevOps part-time (0.5)
├── Product Manager (1)
└── Lead Sales (1)
```

### Y3 (12-18 FTE) — Scale

```
CEO
├── CTO
│   ├── Data Platform Lead → 2 data eng
│   ├── ML Lead → 1 ML eng + 1 NLP
│   ├── Backend Lead → 2 backend
│   ├── Frontend Lead → 2 frontend
│   ├── DevOps/SRE (1)
│   └── Designer (1)
├── CPO
│   ├── PM × 1-2
│   └── Customer Success × 1
├── Head of Sales (CRO)
│   ├── AE × 2-3
│   └── SDR × 1
└── DPO interne (1)
```

### Y4 (22-35 FTE) — Plateforme européenne

```
CEO
├── CTO
│   ├── Data Platform → 3-4 data eng
│   ├── ML/AI → 3-4 ML + 1-2 NLP
│   ├── Backend → 3-4 backend
│   ├── Frontend → 3-4 frontend + 2 design
│   ├── DevOps/SRE → 2 SRE + 1 secu
│   └── Mobile (1, partial)
├── CPO
│   ├── PM × 3 (verticaux)
│   ├── Customer Success × 3
│   └── Support × 2
├── CRO
│   ├── Head of Sales → 4-5 AE
│   ├── Head of Marketing → 2-3 marketers
│   ├── SDR × 3
│   └── Partnerships (1)
├── DPO + Legal Counsel
└── COO/CFO
    ├── Finance × 1
    └── HR/People × 1
```

---

## Profils clés à recruter (priorisé)

### Recrutements Y1 (priorité absolue)

| # | Profil | Salaire chargé | Quand | Profils types |
|---|---|---|---|---|
| 1 | **Lead Data Engineer** | 170-200k€ | Q1 2026 | Ex-Doctrine, Pappers, Datadog, BlaBlaCar |
| 2 | **Senior Backend Python** | 140-170k€ | Q2 2026 | Aircall, Doctolib, Algolia, Lifen |
| 3 | **Senior Frontend Next.js** | 130-160k€ | Q2 2026 | Front + UI/UX sensitivity |
| 4 | **ML Engineer NLP FR** | 155-200k€ | Q3 2026 | Hugging Face, Lighton, Doctrine |

### Recrutements Y2

| # | Profil | Salaire chargé | Quand |
|---|---|---|---|
| 5 | **Product Manager M&A** | 130-170k€ | Q1 2027 (idéal : ex-banquier d'affaires reconverti) |
| 6 | **Lead Sales (First Sales)** | 200k€ OTE | Q1 2027 (ex-Pappers, BvD, BvD, Pitchbook) |
| 7 | **Backend** (mid-senior) | 100-140k€ | Q2 2027 |
| 8 | **Data Engineer #2** | 130-170k€ | Q3 2027 |

### Recrutements Y3

| # | Profil | Salaire chargé | Quand |
|---|---|---|---|
| 9 | **CRO / Head of Sales** | 350-500k€ OTE | Q1 2028 (réseau M&A européen) |
| 10 | **DPO interne** | 100-140k€ | Q2 2028 (avocat ou ex-CNIL) |
| 11 | **3 AE** | 150-200k€ OTE chaque | Q1-Q3 2028 |
| 12 | **Graph Data Engineer** | 130-170k€ | Q3 2028 (Neo4j senior) |

---

## Politique BSPCE (Bons de Souscription)

**Pool total** : 12-15% du capital réservé aux salariés
**Vesting** : 4 ans avec cliff 1 an, monthly vesting after
**Allocation indicative** :

| Niveau | % typique | Equity Y1 hire | Equity Y3 hire |
|---|---|---|---|
| Junior dev | 0.05-0.10% | 0.10% | 0.05% |
| Mid dev | 0.10-0.20% | 0.20% | 0.10% |
| Senior dev | 0.20-0.40% | 0.40% | 0.20% |
| Staff/Lead | 0.40-0.80% | 0.80% | 0.40% |
| Head/Director | 0.50-1.50% | 1.50% | 0.75% |
| C-level non-fondateur | 1.0-3.0% | 3.0% | 1.5% |

**Principe** : les premiers hires (Y1) ont le plus d'equity car risque maximal. L'equity diminue proportionnellement au risque réduit dans le temps.

---

## Politique non-dilutive (à cumuler systématiquement)

| Aide | Montant | Quand viser |
|---|---|---|
| **Bourse French Tech (BPI)** | 30k€ | Q1 2026 (création) |
| **Aide à l'innovation BPI** | 100-300k€ | Q2 2026 |
| **JEI (Jeune Entreprise Innovante)** | -30% charges sociales R&D | Dès embauche premiers ingénieurs |
| **CIR (Crédit Impôt Recherche)** | 30% des dépenses R&D | À partir de Y2 (besoin d'un an d'historique) |
| **CII (Crédit Impôt Innovation)** | 20% des dépenses innovation | Idem |
| **France 2030** | 500k-5M€ | Y2-Y3 si projet stratégique souverain |
| **Concours i-Lab / i-Nov** | 200-600k€ | Q2 2026 candidature |
| **Revenue-Based Financing** (Karmen, Silvr) | 100k-1M€ | Y3 si ARR récurrent prouvé |

> **Cible Y2-Y4** : 30-40% du budget R&D financé par CIR + JEI + BPI = **~1-2M€ économisés sur 4 ans**.

---

## Calendrier de levées (V2)

| Phase | Quand | Montant | Source | Dilution |
|---|---|---|---|---|
| **Pré-amorçage** | Q1 2026 | 200-700k€ | BPI Bourse FT + Business Angels | 5-10% |
| **Seed** | Q4 2026 - Q1 2027 | 1.5-2.5M€ | VC seed FR (Frst, Kima, Elaia, Newfund) | 15-20% |
| **Series A** | Q4 2027 - Q1 2028 | 6-10M€ | VC tech FR/UE (Partech, Eurazeo, Index) | 18-25% |
| **Series B** | 2029-2030 | 20-40M€ | VC growth ou stratégique | 15-20% (ou skip si exit) |

**Cap table cible avant Series A** :
- Fondateurs : 60-65%
- Pré-amorçage : 7-10%
- Seed : 18-22%
- BSPCE pool : 12-15%

---

## KPIs financiers à suivre

| Métrique | Y1 | Y2 | Y3 | Y4 |
|---|---|---|---|---|
| ARR | 50-100k€ | 500-800k€ | 2-3M€ | 8-15M€ |
| MRR | 5-8k€ | 40-65k€ | 165-250k€ | 670k-1.25M€ |
| Burn rate mensuel | -35k€ | -30k€ | -10k€ | +50k à +650k€ |
| Runway (post-levée) | 18-24 mois | 18-24 mois | 24-36 mois | rentable |
| LTV/CAC | n/a | 3× | 4× | 5× |
| Gross margin | 70% | 75% | 80% | 82% |
| Net retention | n/a | 110% | 120% | 130% |
| Headcount | 4-5 | 7-9 | 12-18 | 22-35 |

---

## Différences clés vs V1

| Aspect | V1 | V2 (révisé) |
|---|---|---|
| Salaire Lead Data Eng Y1 | 75k€ chargé | **170-200k€ chargé** (réalité Paris) |
| Coût équipe Y1 | 450k€ | 350k€ (équipe légèrement réduite + Founder sans salaire) |
| Total Y1 | 530k€ | 525k€ (similaire) |
| Total Y4 | 7M€ | **7.4M€** |
| Équipe Y4 | 30-50 | **22-35** (plus contrôlé) |
| ARR Y4 | 20M€ | **8-15M€** (plus prudent) |
| Contingence | Non explicite | **+15% systématique** |
| BSPCE pool | 10-15% | 12-15% (plus généreux pour attirer talent) |

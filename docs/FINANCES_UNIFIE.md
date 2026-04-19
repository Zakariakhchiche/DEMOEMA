# FINANCES UNIFIÉ — Source unique de vérité

> **Tous les autres documents renvoient ici** pour les chiffres financiers, équipe, ARR, levées, cap table.
>
> Validé le 2026-04-17 après audit `SELF_CHALLENGE`.
>
> Toute modification ici doit être propagée dans `BUDGET_EQUIPE.md`, `ROADMAP_4ANS.md`, `MODELE_FINANCIER.md`, `PRICING.md`, `DECISIONS_VALIDEES.md`.

---

## 1. Distinction Revenue total vs ARR (corrige A5)

⚠️ **Erreur courante corrigée** : "ARR" ne désigne **que le revenu récurrent annualisé** (Annual Recurring Revenue).

| Métrique | Définition | Inclut |
|---|---|---|
| **Revenue total** | Total revenu de la période | Tout (récurrent + one-shot + reports) |
| **MRR récurrent** | Revenu mensuel récurrent | Starter + Pro + Enterprise (PAS les reports one-shot) |
| **ARR** | MRR récurrent × 12 | = annualisation du seul récurrent |

### Application correcte (V1 → corrigé)

| | Y1 2026 | Y2 2027 | Y3 2028 | Y4 2029 |
|---|---|---|---|---|
| Revenue total annuel | 44 k€ | 412 k€ | 1 680 k€ | **5 000-8 000 k€** |
| MRR fin de période | 6.7 k€ | 48.7 k€ | 199 k€ | **700-1 200 k€** |
| **ARR fin de période** | **80 k€** | **584 k€** | **2 389 k€** | **8 000-15 000 k€** |

> **Note** : "ARR Y1 = 50-100k€" écrit dans la doc V1 était **faux**. La majorité du revenu Y1 = pay-per-report (one-shot, pas de récurrence). ARR réel Y1 ≈ 80k€.

---

## 2. Tableau financier consolidé (P&L 4 ans)

| Ligne | Y1 2026 | Y2 2027 | Y3 2028 | Y4 2029 |
|---|---|---|---|---|
| **Revenue Reports (one-shot)** | 32 k€ | 110 k€ | 111 k€ | 80 k€ |
| **Revenue Starter récurrent** | 8 k€ | 91 k€ | 206 k€ | 350 k€ |
| **Revenue Pro récurrent** | 7 k€ | 193 k€ | 775 k€ | 2 200 k€ |
| **Revenue Enterprise récurrent** | 0 | 15 k€ | 576 k€ | 4 500 k€ |
| **Revenue total** | **44 k€** | **412 k€** | **1 680 k€** | **~7 000 k€** |
| **ARR fin période** | **80 k€** | **584 k€** | **2 389 k€** | **~10 000 k€** |
| | | | | |
| Salaires (chargés) | 364 k€ | 996 k€ | 2 178 k€ | 4 200 k€ |
| Infra cloud (V4 = **VPS IONOS** au lieu de Scaleway managed) | **8 k€** ⬇ | **40 k€** ⬇ | 120 k€ | 400 k€ |
| LLM + APIs | 5 k€ | 51 k€ | 219 k€ | 500 k€ |
| **Partenariats data Y2+** (CFNews ou licence ADPI/CFC) | 0 | **20 k€** | 30 k€ | 50 k€ |
| Outils SaaS | 14 k€ | 24 k€ | 43 k€ | 150 k€ |
| Légal + DPO | 91 k€ | 86 k€ | 78 k€ | 150 k€ |
| Comptabilité | 8 k€ | 8 k€ | 12 k€ | 50 k€ |
| Marketing & Sales | 15 k€ | 40 k€ | 102 k€ | 500 k€ |
| Voyage & events | 8 k€ | 22 k€ | 50 k€ | 100 k€ |
| Recrutement | 17 k€ | 28 k€ | 56 k€ | 150 k€ |
| Bureau | 0 | 0 | 28 k€ | 200 k€ |
| Autres | 11 k€ | 12 k€ | 21 k€ | 50 k€ |
| Contingence (10%) | 53 k€ | 132 k€ | 297 k€ | 665 k€ |
| **Coûts totaux** | **594 k€** ⬇ | **1 439 k€** ⬇ | **3 204 k€** ⬇ | **~7 100 k€** ⬇ |
| _Économie cumulée vs V3.3 (Scaleway managed)_ | -6 k€ | -24 k€ | -58 k€ | -200 k€ — **~290 k€ économisés sur 4 ans grâce à VPS IONOS Option A** |
| | | | | |
| **Résultat opérationnel** | -556 k€ | -1 051 k€ | -1 582 k€ | ≈ équilibre |
| | | | | |
| Cash injection | **+600 k€** | +2 000 k€ | +8 000 k€ | 0 (ou Series B) |
| **Cash position fin période** | 44 k€ | 993 k€ | 7 411 k€ | ~7 000 k€ |

---

## 3. Décisions verrouillées (corrige A4)

### DPO

- **Coût** : **5 000 €/mois** (60k€/an)
- **Type** : DPO externe régulier (cabinet spécialisé RGPD + AI Act)
- **Démarrage** : Q2 2026 (fin avril)
- **Évolution** : DPO interne en Y3 (130k€ chargé/an)

### Pré-amorçage

- **Cible** : **600 k€** (au milieu de 200-700k€)
- **Sources** : BPI Bourse French Tech (30k€) + 4-6 Business Angels (90-150k€ chacun)
- **Closing visé** : **fin juin 2026** (décalé de Q1 → Q2 vu l'état réel)
- **Valorisation pre-money cible** : 3-4M€ → dilution 13-17%

### Levées suivantes

| Phase | Quand (révisé) | Montant | Dilution cible |
|---|---|---|---|
| Pré-amorçage | Juin 2026 | **600 k€** | 13-17% |
| Seed | Q1 2027 | **2 000 k€** | 18-22% |
| Series A | Q1 2028 | **8 000 k€** | 18-25% |
| Series B (optionnel) | 2030+ | 20-40 M€ | 15-20% (skip si exit) |

### ARR Y4

- **Fourchette** : **8 000 - 15 000 k€** (réaliste vs benchmark Pappers 15M€ après 6 ans, Doctrine 25M€ après 8 ans)
- **Hypothèse milieu** : ~10M€ ARR
- Distribution : 8% Free, 10% Starter, 35% Pro, 47% Enterprise

### Europe

- **Y3 (2028)** : **UK + Allemagne uniquement** (2 pays via Companies House + Bundesanzeiger)
- **Y4 (2029)** : ajout BENELUX + Italie + Espagne (5-6 pays)
- Ne pas viser "8 pays en 1 trimestre" (irréaliste)

---

## 4. Équipe (corrige A4 #19)

### Headcount par fin de période

| | Y1 2026 | Y2 2027 | Y3 2028 | Y4 2029 |
|---|---|---|---|---|
| Founder | 1 | 1 | 1 | 1 |
| CTO/Lead Eng | inclus founder | 1 | 1 | 1 |
| Data Engineers | 1 | 2 | 3 | 4 |
| Backend | 1 | 2 | 3 | 4 |
| Frontend | 1 | 2 | 3 | 4 |
| ML/AI | 0 (Y1) | 1 | 2 | 3 |
| DevOps/SRE | 0 | 0.5 | 1 | 2 |
| Designer | 0.5 freelance | 1 | 1 | 2 |
| Product | 0 | 1 | 2 | 3 |
| Sales | 0 | 1 | 3 | 6 |
| Marketing | 0 | 0 | 1 | 3 |
| Customer Success | 0 | 0 | 1 | 3 |
| DPO | 0 (externe) | 0 (externe) | 1 (interne) | 1 |
| Finance/HR | 0 | 0 | 0.5 | 2 |
| **Total FTE** | **4-5** | **9** | **18** | **35** |

> Y1 = 5 FTE max (4 plein temps + 1 designer freelance). Resynchronise avec ROADMAP & BUDGET.

### Recrutements clés Q2-Q4 2026 (révisé du fait que rien n'est fait)

| # | Profil | Salaire chargé | Quand |
|---|---|---|---|
| 1 | Lead Data Engineer | 200 k€ | Juillet 2026 (post-closing pré-amorçage) |
| 2 | Senior Backend | 170 k€ | Septembre 2026 |
| 3 | Senior Frontend | 160 k€ | Octobre 2026 |
| 4 | Designer freelance | 5 k€/mois | Mai 2026 (pendant validation marché) |

> ML Engineer décalé en **Y2 (Q1 2027)** vu le retard Q1 et les budgets serrés.

---

## 5. Cap table corrigée (V3.1 — dilution réaliste post-audit Q142)

### Hypothèses de valorisation (réalistes 2026 marché FR)

| Tour | Pre-money | Post-money | Montant | **Dilution** |
|---|---|---|---|---|
| Pré-amorçage (juin 2026, démo + 2 LOI) | 3 M€ | **3.6 M€** | 600 k€ | **16.7%** |
| Seed (mai 2027, ARR ~150-200k€) | 8 M€ | **10 M€** | 2 000 k€ | **20%** |
| Series A (mai 2028, ARR ~600-800k€) | 28 M€ | **36 M€** | 8 000 k€ | **22.2%** |

> ⚠️ **Correction post-audit** : le pré-amorçage à **8% dilution @ 7M€ post-money** était irréaliste pour ce stade (demo + 2 LOI sans MVP). Valorisation corrigée à **3 M€ pre-money** = standard pour pré-amorçage à ce stade.

### Cap table après chaque tour (avant pool)

| Étape | Fondateurs | Pré-amorçage | Seed | Series A |
|---|---|---|---|---|
| Création | 100% | — | — | — |
| Post pré-amorçage | **83.3%** | 16.7% | — | — |
| Post Seed | **66.6%** | 13.4% | 20.0% | — |
| Post Series A | **51.8%** | 10.4% | 15.6% | 22.2% |

### Cap table finale après pool BSPCE 12%

> Le pool BSPCE de 12% est typiquement créé **avant Series A** (dilution shareholders existants), parfois **après**. Convention ici : créé après Series A par dilution proportionnelle.

| Catégorie | % final |
|---|---|
| **Fondateurs** | **45.6%** |
| Pré-amorçage (BPI + BA) | 9.2% |
| Seed (VC seed FR) | 13.7% |
| Series A (VC tech) | 19.5% |
| Pool BSPCE (employés) | 12.0% |
| **Total** | **100.0%** ✓ |

### Évolution de la dilution fondateurs

| Étape | Date cible | % fondateurs |
|---|---|---|
| Création société | Q2 2026 | 100% |
| Post pré-amorçage | Juin 2026 | **83.3%** |
| Post Seed | Mai 2027 | **66.6%** |
| Post Series A | Mai 2028 | **51.8%** |
| Post pool BSPCE 12% | Q3-Q4 2028 | **45.6%** |
| Post Series B 25M€ optionnel @ 100M€ post | 2030+ | ~34% (si applicable) |

**Cible exit** : à 8-15M€ ARR Y4 et multiple 4-5× (FR), valo ≈ 32-75M€. Founder à 45.6% (sans Series B) = **15-34M€ brut au pre-clean** (avant préférences liquidation, taxation).

---

## 6. Pricing — fourchettes au lieu de valeurs fixes (à confirmer après benchmark)

⚠️ **À benchmarker en priorité** auprès des 2 boutiques M&A (combien payent-elles Pappers ?). Le pricing ci-dessous est une **première approximation** à confirmer.

| Plan | Fourchette indicative | Cible |
|---|---|---|
| Free | 0 € | 5-10 fiches/mois |
| Starter | **49-79 €/mois user** | Indiv, petits cabinets |
| Pro | **199-299 €/mois user** | Boutiques M&A |
| Enterprise | **15-30 k€/an** (custom) | Banques, fonds, corp |
| Pay-per-report | 490-2 990 € (à augmenter ?) | One-shot |

> Ces fourchettes seront figées après les **20-30 interviews structurées** prévues en Q2 2026.

---

## 7. Coûts détaillés annuels — checks de cohérence

### Y1 (4-5 FTE max, démarrage progressif)

- **Salaires 364 k€** = ((Lead Data 200k × 6mo) + (Backend 170k × 4mo) + (Frontend 160k × 3mo) + (Designer 5k × 6mo)) ≈ 100+57+40+30 + corrections = ~360-380 k€ ✓
- DPO 60k€ + corporate 10k€ + autres légal = ~91 k€
- **Total ~600 k€** ✓

### Y4 (35 FTE)

- 35 FTE × ~120 k€ chargé moyen = 4 200 k€ ✓
- Bureau 200 k€ (Paris + bureau secondaire UK ou DE)
- Marketing & Sales 500 k€ (≈10% revenue)
- **Total ~7 300 k€** ✓

---

## 8. Indicateurs SaaS clés

| Métrique | Y1 | Y2 | Y3 | Y4 |
|---|---|---|---|---|
| ARR | 80 k€ | 584 k€ | 2 389 k€ | 8 000-15 000 k€ |
| Revenue total | 44 k€ | 412 k€ | 1 680 k€ | ~7 000 k€ |
| MRR fin | 6.7 k€ | 48.7 k€ | 199 k€ | ~750 k€ |
| Nb clients récurrents | ~75 | ~310 | ~700 | ~2 000 |
| ARPU mensuel récurrent | ~90 € | ~155 € | ~285 € | ~350 € |
| Net Revenue Retention | n/a | 105% | 110% | **115%** (corrigé du 130% irréaliste) |
| Gross Margin | 65% | 70% | 75% | **75%** (corrigé du 82% trop optimiste) |
| LTV/CAC | n/a | 2.5× | 3× | 4× |
| Headcount | 4-5 | 9 | 18 | 35 |
| Revenue per employee | 11 k€ | 46 k€ | 93 k€ | 200 k€ |

---

## 9. Sources de financement non-dilutif (à cumuler)

| Aide | Montant | Quand |
|---|---|---|
| Bourse French Tech (BPI) | 30 k€ | Q2 2026 (création) |
| Aide à l'innovation BPI | 100-300 k€ | Q3 2026 |
| JEI (réduction charges) | -30% sur charges R&D | Dès embauche ingénieurs |
| CIR (Crédit Impôt Recherche) | 30% des dépenses R&D | À partir de Y2 |
| CII (Crédit Impôt Innovation) | 20% des dépenses innovation | Idem |
| France 2030 / i-Lab | 200-600 k€ | Y2-Y3 |
| Revenue-Based Financing | 100k-1M€ | Y3 si ARR récurrent prouvé |

**Cible Y2-Y4** : 30-40% du budget R&D financé non-dilutif = **~1-2 M€ économisés** sur 4 ans.

---

## 10. Tableau récap final

| | Y1 2026 | Y2 2027 | Y3 2028 | Y4 2029 |
|---|---|---|---|---|
| **Revenue total** | 44 k€ | 412 k€ | 1 680 k€ | ~7 000 k€ |
| **ARR fin** | 80 k€ | 584 k€ | 2 389 k€ | 8-15 000 k€ |
| **Coûts totaux** | 600 k€ | 1 463 k€ | 3 262 k€ | ~7 300 k€ |
| **Burn / Résultat** | -556 k€ | -1 051 k€ | -1 582 k€ | équilibre |
| **Levée** | 600 k€ | 2 000 k€ | 8 000 k€ | 0 |
| **Cash fin période** | 44 k€ | 993 k€ | 7 411 k€ | ~7 000 k€ |
| **Headcount** | 4-5 | 9 | 18 | 35 |

---

## Historique des modifications

| Date | Modification | Source |
|---|---|---|
| 2026-04-17 | Création initiale, source unique de vérité | Audit `SELF_CHALLENGE.md` |

> **Toute évolution future** doit être documentée ici en premier, puis propagée dans les autres docs.

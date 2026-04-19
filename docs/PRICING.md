# STRATÉGIE PRICING

> ⚠️ **Document V2 — pricing à valider après les 30 interviews clients prévues Q2 2026.**
>
> Source de vérité chiffres : [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md)
> État réel : [`REPONSES_SELF_CHALLENGE.md`](./REPONSES_SELF_CHALLENGE.md)
>
> ⚠️ **Erreur arithmétique corrigée** : "2000 clients × 10k€ Enterprise = 20M€ ARR Y4" était **mathématiquement impossible** (TAM PE/M&A FR ≈ 1000 acteurs total). Le mix Y4 cible est désormais **8-15M€ ARR** avec ~2000 clients **toutes catégories confondues** (mix Free/Starter/Pro/Enterprise) et non 2000 Enterprise.
>
> ⚠️ **Net retention 130% Y4** ramené à **115%** (top quartile B2B mid-market réaliste).
> ⚠️ **Gross margin 82% Y4** ramené à **75%** (inclut coût LLM scale + support Enterprise + certifications).
>
> Benchmarks concurrents, modèle tarifaire proposé, mécaniques de monétisation.

---

## Benchmarks marché (2026)

### Bas de marché (consultation entreprise)

| Concurrent | Plan | Prix | Inclus |
|---|---|---|---|
| Pappers | Gratuit | 0€ | 5 fiches/mois |
| Pappers | Pro | 39€/mois user | Fiches illimitées, exports |
| Pappers | Premium | 99€/mois user | API, alertes |
| Société.com | Standard | 9€/mois | Recherche basique |
| Société.com | Pro | 39€/mois | Alertes, exports |
| Infogreffe Pro | Pay-per-use | 3-9€/document | Actes officiels |

### Mid-market (M&A, conseil)

| Concurrent | Prix | Cible |
|---|---|---|
| Diane (BvD/Moody's) | 15-50k€/an/user | Audit, banques, conseil |
| Capital IQ | 20-40k€/an/user | Banques, fonds |
| Pitchbook | 25-80k€/an/user | PE, VC |
| Crunchbase Pro | 99€/mois user | Startups, VC |
| Crunchbase Enterprise | 30-50k€/an | Équipes VC |
| CFNews abonnement | 2-5k€/an/user | Veille deals FR |
| Mergermarket | 10-30k€/an | Banques d'aff. |

### Haut de gamme (intelligence + workflow)

| Concurrent | Prix | Cible |
|---|---|---|
| Affinity | 1-5k€/an/user | PE/VC (CRM) |
| Attio | 30-100€/mois user | Startups, PE moderne |
| Doctrine | 200-500€/mois user | Avocats |
| Harvey AI | 100-300€/mois user | Avocats premium |

---

## Notre proposition tarifaire — 3 SCÉNARIOS

> ⚠️ **Hypothèses à valider après les 30 interviews clients prévues Q2 2026.**
> Le pricing final sera décidé selon les retours sur "combien tu paies aujourd'hui pour Pappers/Diane/autres ?".
> Voici 3 scénarios pour stress-tester la robustesse du modèle économique.

### Principe directeur

> **Démocratiser l'intelligence M&A** : 3-10× moins cher que Diane/Pitchbook, 5-10× plus puissant que Pappers.

### Comparaison des 3 scénarios pricing

| Plan | 🔻 BAS (si Pappers payé 20€/mois) | 🎯 MÉDIAN (default) | 🔺 HAUT (si concurrent légitimé) |
|---|---|---|---|
| Free | 5 fiches/mois | 10 fiches/mois | 10 fiches/mois |
| Starter | **29 €/mois user** | **49 €/mois user** | **79 €/mois user** |
| Pro | **99 €/mois user** | **199 €/mois user** | **299 €/mois user** |
| Enterprise | **8 k€/an** | **15-25 k€/an** | **30-40 k€/an** |
| Rapport "Cible" | 290 € | 490 € | 990 € |
| Rapport "Buyer list" | 1 490 € | 2 990 € | 5 990 € |

### Impact sur ARR Y4 (avec mix 500 Starter + 1000 Pro + 200 Enterprise)

| Scénario | ARR Starter | ARR Pro | ARR Enterprise | **ARR Y4 total** |
|---|---|---|---|---|
| 🔻 BAS | 174 k€ | 1 188 k€ | 1 600 k€ | **~3 M€** |
| 🎯 MÉDIAN | 294 k€ | 2 388 k€ | 4 000 k€ | **~6.7 M€** |
| 🔺 HAUT | 474 k€ | 3 588 k€ | 7 000 k€ | **~11 M€** |

> ⚠️ **Conclusion stress-test** : seul le scénario **HAUT** (ou MÉDIAN avec volumes ×1.5) permet d'atteindre les 8-15M€ ARR Y4 visés dans `FINANCES_UNIFIE.md`. Le scénario BAS rend le modèle non viable → **interviews clients critiques pour valider le pricing MÉDIAN minimum**.

---

### Détail du scénario MÉDIAN (default, à valider)

#### 🔵 Free — Acquisition & viralité
- 0 €/mois
- 10 fiches entreprises/mois
- Recherche basique
- Pas de scoring M&A, pas de copilot, pas d'export
- **Objectif** : SEO + tester avant d'acheter

#### 🟢 Starter — Indépendants, petits cabinets
- **49 €/mois** par user (ou **490 €/an** —2 mois offerts)
- Fiches illimitées
- Scoring M&A basique
- Exports CSV/PDF
- 100 alertes signaux/mois
- **Cible** : conseillers indépendants, advisors solo, petits cabinets

#### 🟠 Pro — Boutiques M&A, équipes <10
- **199 €/mois** par user (ou **1990 €/an**)
- Tout Starter +
- Graphe dirigeants visuel
- Copilot LLM (limité 100 requêtes/mois)
- Alertes illimitées
- API limitée (1000 calls/mois)
- Collaboration équipe (5 users min)
- **Cible** : boutiques M&A, PE seed, family offices

#### 🔴 Enterprise — Banques, gros fonds, corporates
- **À partir de 15-25 k€/an** (selon nb users + features)
- Tout Pro +
- Copilot illimité
- API étendue
- Permissions fines + RBAC + SSO
- Audit log RGPD
- Modules verticaux (santé, industrie, ESS...)
- Account manager dédié + SLA
- **Cible** : équipes M&A banques, fonds PE >100M€ AUM, dpt M&A grands corp.

### 🟣 Pay-per-report (one-shot, cash Y1)

- **490 €** : rapport "Cible" complet (fiche enrichie 360°)
- **1 490 €** : rapport "Cluster sectoriel" (cartographie 50 entreprises secteur)
- **2 990 €** : rapport "Buyer list" (liste qualifiée 100 acquéreurs potentiels)

> ⚠️ **À benchmarker** : marché conseil M&A one-shot = **5-15 k€/livrable**. Notre 2990€ peut être perçu sous-tarifé. Tester en interviews "à partir de quel prix tu décrocherais ?".

---

## Politique de grandfathering pour les hausses Y2

> Décision verrouillée : **les clients existants gardent leur prix d'origine** lorsque les tarifs augmentent (10-15% Y2). Politique standard B2B SaaS.
>
> Évite le churn dû aux augmentations.

---

## Comparaison vs concurrents

| Plan | Notre prix | Concurrent équivalent | Économie |
|---|---|---|---|
| Free | 0€ | Pappers Free (équivalent) | 0€ |
| Starter | 49€/mois | Pappers Pro 39€ | -10€/mois mais bcp + features |
| Pro | 199€/mois | Pas d'équivalent direct | Diane = 1500€/mois → −86% |
| Enterprise | 15k€/an mini | Diane = 30k€, Pitchbook = 40k€ | −50% à −60% |

---

## Modèle économique cible (mix produit)

> **Note V3.1** : les chiffres ARR/clients ci-dessous sont la **source unique** de `FINANCES_UNIFIE.md` (Scénario MÉDIAN du pricing). Pour les scénarios BAS et HAUT, voir tableau "Impact sur ARR Y4" plus haut.

### Y1 fiscal 2026-27 (Avril 2026 → Mars 2027)
- Pay-per-report : 73% du revenu (cash immédiat — 32 k€ / 44 k€)
- Starter : 18% (8 k€)
- Pro : 16% (7 k€)
- Enterprise : 0% (cycle vente trop long Y1)

**Objectif Y1** : 50 clients payants fin Y1, **ARR 80 k€**, Revenue total 44 k€

### Y2 fiscal 2027-28
- Free : viralité (0% revenu mais 80% des leads)
- Starter : 22% (91 k€)
- Pro : 47% (193 k€)
- Enterprise : 4% (15 k€)
- Pay-per-report : 27% (110 k€)

**Objectif Y2** : 200 clients payants, **ARR fin = 584 k€**, Revenue total 412 k€

### Y3 fiscal 2028-29
- Starter : 12% (206 k€)
- Pro : 46% (775 k€)
- Enterprise : 34% (576 k€)
- Reports : 7% (111 k€)

**Objectif Y3** : 500 clients payants, **ARR fin = 2 389 k€**, Revenue total 1 680 k€

### Y4 (2029-30)
- Starter : 8% (~350 k€)
- Pro : 32% (~2 200 k€)
- Enterprise : 56% (~4 500 k€)
- Reports + API/Marketplace : 4%

**Objectif Y4** : ~2 000 clients payants (mix), **ARR 8-15 M€** (selon scénario pricing : MÉDIAN ~10 M€)

---

## Mécaniques tarifaires complémentaires

### Promotions / discounts
- **−20% engagement annuel** vs mensuel
- **−30% cabinets <5 personnes** sur Pro (12 mois)
- **−50% startups <2 ans** sur Starter (kit French Tech)
- **Free trial 14 jours** sur Pro et Enterprise

### Add-ons (à la carte)
- **Module ESG approfondi** : +50€/user/mois
- **Module sectoriel santé** (BDPM, ANSM) : +100€/user/mois
- **Module Europe** (UK, DE, BE...) : +50%/user/mois
- **API étendue** (10k calls/mois) : +200€/mois
- **Audit log avancé + SOC2 reports** : +1k€/mois

### Marketplace (Y4)
- Datasets premium tiers : 70% revenue share au partenaire, 30% à nous
- API publique : 0.10€/call simple, 1€/call enrichi LLM
- Webhooks signaux temps réel : 500€/mois pour 1000 alertes

---

## Stratégie de pricing dynamique

### Ce qu'on ne fait PAS
- ❌ Pricing à la fiche (Infogreffe-style — friction trop forte)
- ❌ Surcharge cachée (LinkedIn-style)
- ❌ Lock-in contractuel ≥ 3 ans
- ❌ Discount excessifs sur Enterprise (dévalorise le produit)

### Ce qu'on fait
- ✅ Transparence totale sur le pricing (page publique)
- ✅ Engagement annuel récompensé mais pas obligatoire
- ✅ Self-service jusqu'à Pro (pas besoin de parler à un commercial)
- ✅ Enterprise = devis personnalisé en visio 30 min

---

## Évolution tarifaire prévue

| Année | Évolution prix | Justification |
|---|---|---|
| Y1 2026 | Lancement (prix proposés ci-dessus) | |
| Y2 2027 | +10-15% sur Pro et Enterprise | Plus de features, AUC scoring meilleur |
| Y3 2028 | Refonte avec modules verticaux (+ tier vertical) | Diversification |
| Y4 2029 | Stabilisation, +5%/an inflation | Maturité |

---

## Indicateurs financiers cibles (V3.1 — alignés FINANCES_UNIFIE)

| Métrique | Y1 fiscal | Y2 fiscal | Y3 fiscal | Y4 |
|---|---|---|---|---|
| ARR fin de période | **80 k€** | **584 k€** | **2 389 k€** | **8-15 M€** |
| Revenue total annuel | 44 k€ | 412 k€ | 1 680 k€ | ~7 000 k€ |
| MRR fin | 6.7 k€ | 48.7 k€ | 199 k€ | ~750 k€ |
| ARPU mensuel mix | ~90 € | ~150 € | ~285 € | ~350 € |
| Nb clients payants | 50 | ~180 | ~500 | ~2 000 |
| LTV/CAC cible | n/a (early) | 2.5× | 3× | 4× |
| Gross margin | 65% | 70% | 75% | **75%** (corrigé du 82% irréaliste) |
| Net retention | n/a | 105% | 110% | **115%** (corrigé du 130% irréaliste) |

---

## Question ouverte : Freemium vs Free Trial vs Pay-only ?

| Option | Avantage | Inconvénient |
|---|---|---|
| **Freemium** (proposé) | SEO, viralité, base de leads massive | Coût infra à supporter |
| **Free trial 14j** | Conversion plus élevée | Moins de viralité, moins de SEO |
| **Pay-only** | Marge brute max | Acquisition lente, pas de marque |

> Recommandation : **Freemium léger Y1-Y2** (SEO + acquisition), basculer en **Free trial 14j sur Pro/Enterprise Y3+**.

# ROADMAP 4 ANS — V2 (réaliste, avec validation marché et buffers)

> ⚠️ **Document V2 — voir bannière ci-dessous pour les corrections post-audit.**
>
> **Source unique de vérité chiffrée** : [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md)
> **Décisions verrouillées** : [`DECISIONS_VALIDEES.md`](./DECISIONS_VALIDEES.md)
> **État réel au 17/04/2026** : [`REPONSES_SELF_CHALLENGE.md`](./REPONSES_SELF_CHALLENGE.md) (rien n'est fait → calendrier décale +3 mois)
> **Plan opérationnel détaillé Q2-Q4 2026** : [`PLAN_DEMARRAGE_Q2-Q4_2026.md`](./PLAN_DEMARRAGE_Q2-Q4_2026.md)
>
> ⚠️ **Calendrier** : toute référence "Q1 2026" dans ce document doit être lue comme **"Q2 2026 (avril-juin)"** — le projet démarre réellement en avril 2026.
>
> ⚠️ **Chiffres ARR** : les fourchettes "50-100k€ Y1" / "500-800k€ Y2" sont **remplacées** par les valeurs canoniques de `FINANCES_UNIFIE.md` (80k€ Y1, 584k€ Y2, 2389k€ Y3, 8-15M€ Y4).
>
> Roadmap révisée selon principes : **start small**, validation marché obligatoire, buffer 20-30% par trimestre, focus mid-market FR avant l'Europe.

---

## Vision condensée

| Année | Thème | Périmètre | ARR cible (FINANCES_UNIFIE) | Équipe |
|---|---|---|---|---|
| **2026** | Validation + MVP focus | 30 sources, 5M FR (light) | **80 k€** | 4-5 |
| **2027** | PMF mid-market FR | 60 sources, scoring ML, copilot v1 | **584 k€** | 9 |
| **2028** | Scaling FR + tests UE | 100 sources, copilot avancé | 2-3M€ | 12-18 |
| **2029** | SaaS mid-market UE | 130+ sources, multi-tenant, modules | 8-15M€ | 22-35 |

**Différences vs V1** :
- ARR Y4 révisé à 8-15M€ (vs 15-25M€) — plus prudent
- Équipe Y4 22-35 (vs 30-50) — plus contrôlé
- Q1 2026 = **validation marché obligatoire avant tout code majeur**
- Pas d'Europe en Y2 (était le cas en V1) — focus FR
- 30 sources Y1 (vs 50) — priorité qualité

---

## ANNÉE 1 — 2026 — "Validation + MVP focus"

### Q1 2026 — VALIDATION (pas de code produit majeur)

**Objectif** : valider que ce qu'on veut construire répond à une vraie demande payante.

**Livrables**
- [ ] **30 interviews clients** (cf. `VALIDATION_MARCHE.md`)
- [ ] Validation de **20 sources critiques** (cf. `VALIDATION_API.md`)
- [ ] **Mockups Figma** des 3 use cases prioritaires
- [ ] **5 LOI (Letters of Intent)** signées par clients potentiels
- [ ] **Décisions Go/No-Go** sur priorités Y1 documentées
- [ ] Pré-amorçage levé (BPI Bourse French Tech + business angels = 200-500k€)
- [ ] Constitution société, statuts, KBIS

**Équipe** : Founder + 1 product/dev + 1 designer freelance
**Budget Q1** : 100k€
**KPIs Q1** :
- 30 interviews réalisées
- 5 LOI signées
- Pré-amorçage > 200k€ closed

**Si Go** : passage Q2 développement
**Si No-Go partiel** : pivot scope ou persona, refaire Q1 sur 4 semaines

---

### Q2 2026 — Fondations data + MVP V1

**Livrables**
- [ ] Infra Postgres + S3 Scaleway + Dagster
- [ ] Ingestion **15 sources priorité 1** (INSEE, INPI RNE, BODACC, recherche-entreprises, OpenSanctions, Judilibre, etc.)
- [ ] Modèle d'entités v1 (entreprises, dirigeants, mandats — table Postgres simple)
- [ ] **API REST v1** : recherche entreprise, fiche, dirigeants
- [ ] **Front MVP** : recherche + fiche entreprise + export PDF
- [ ] Auth Supabase + plans Free/Starter
- [ ] **Premier rapport "Cible"** payant (490€) → cash flow

**Équipe** : +1 backend, +1 frontend (5 FTE total)
**Budget cumulé S1** : 250k€
**KPIs Q2** :
- 5M entreprises requêtables (lookup basique)
- 10 premiers rapports "Cible" vendus
- 20 utilisateurs Starter (49€/mois)

---

### Q3 2026 — Enrichissement + killer feature #1 (Alertes pré-cession)

**Livrables**
- [ ] **+10 sources** (couches financière, marchés publics, sanctions étendues)
- [ ] Comptes annuels INPI (parsing PDF) sur ETI prioritaires
- [ ] **Scoring M&A v0** : 30-50 features les plus impactantes (subset des 103)
- [ ] **Cartographie dirigeants** : graphe simple (table Postgres + viz force-graph) — pas Neo4j encore
- [ ] ⭐ **Alertes signaux pré-cession** (killer feature #1) : détection rule-based sur BODACC + INPI RNE
  - Changement de mandataires sociaux
  - Nomination CFO externe avec dirigeant 55+ sans successeur
  - Nouvelles délégations de pouvoir AG
  - Dirigeant rejoint fonds PE
  - **Effort** : 3-4 semaines dev, sources déjà ingérées
- [ ] **Export Excel templates M&A** (Teaser, Buyer list, Longlist) : 2-3 sem dev
- [ ] **Clause responsabilité IA** dans CGU (conformité AI Act art. 14)
- [ ] **Export CSV compatible Affinity** (format standard)
- [ ] Plan Pro 199€/mois lancé

**Équipe** : +1 ML eng (5-6 FTE total)
**KPIs Q3** :
- 50 clients payants
- MRR 5k€
- 80% satisfaction NPS > 30
- **Alertes pré-cession** : >20 signaux/semaine remontés au moins sur les 10 plus gros secteurs

---

### Q4 2026 — Compliance + killer feature #2 (Who advises whom)

**Livrables**
- [ ] **+5 sources** (web/digital : Certificate Transparency, GitHub, GDELT)
- [ ] **Module compliance/KYC** (sanctions, gels avoirs, RBE)
- [ ] **Détection auto procédures collectives** (alerte temps réel BODACC)
- [ ] ⭐ **Who advises whom v1** (killer feature #2) : base historique M&A advisors 2020-2026
  - NLP extraction deals depuis CFNews RSS + Les Échos + La Tribune + communiqués AMF
  - Pour chaque deal : cible, acquéreur, advisors vendeur/acheteur, valorisation si publiée
  - Objectif V1 : 3 000-5 000 deals FR indexés (pas 12 000 — réaliste)
  - **Effort** : 4-6 semaines (CamemBERT fine-tuné sur 500 communiqués labellisés)
- [ ] **API Affinity** bidirectionnelle (intégration CRM M&A)
- [ ] **Audit RGPD** + LIA documentée
- [ ] **DPIA** validé par DPO + cabinet (12k€)
- [ ] Préparation **levée Seed** (deck, data room)

**Équipe** : 4 FTE (founder + Lead Data + Backend + Frontend)
**Budget cumulé Y1** : ~600k€ (FINANCES_UNIFIE)
**KPIs Y1** :
- 5M entreprises × 30 attributs moyens
- 50 clients payants, MRR 6-8k€, ARR 80k€ (FINANCES_UNIFIE)
- **Who advises whom** : 3 000+ deals indexés
- **Alertes pré-cession** : actives sur 10 secteurs
- DPO + audit RGPD + DPIA validés

---

## ANNÉE 2 — 2027 — "PMF (Product-Market Fit) mid-market FR"

### Q1 2027 — Levée Seed + recrutement

**Livrables**
- [ ] **Seed levé** (1.5-2.5M€)
- [ ] Recrutement : Lead Sales (1), Senior Backend (1), Senior Data Eng (1)
- [ ] Refactoring technique (paye la dette Q4 2026)
- [ ] **Continuous discovery** : 5 interviews/mois en routine

### Q2 2027 — Couche R&D + scoring ML v2

**Livrables**
- [ ] **+10 sources** : couche R&D/innovation (HAL, OpenAlex, EPO OPS)
- [ ] **Scoring M&A v2** : LightGBM sur 100+ features
- [ ] Backtests sur historique BODACC 2018-2026
- [ ] **Cible** : AUC > 0.80 sur prédiction cession 12 mois

### Q3 2027 — Copilot LLM v1 (limité)

**Livrables**
- [ ] **Copilot Claude** intégré (RAG sur datalake Postgres + pgvector)
- [ ] 3 cas d'usage : "résume cette entreprise", "trouve cibles similaires à X", "qui sont les acquéreurs probables ?"
- [ ] Conformité **AI Act** : mention "généré par IA", logs prompts, watermarking
- [ ] Limite 100 requêtes/mois sur Pro, illimité Enterprise

### Q4 2027 — Premiers clients Enterprise

**Livrables**
- [ ] **Premier contrat Enterprise** (15-30k€/an) — banque d'aff. ou fonds PE
- [ ] **Modules verticaux v1** (santé, ESS) — selon demandes clients
- [ ] **CRM intégrations** : Affinity, HubSpot
- [ ] Préparation Series A (deck, métriques, references)

**Équipe Y2** : 8-9 FTE
**Budget Y2** : ~1.1M€
**KPIs Y2** :
- 200 clients payants, ARR 500-800k€
- AUC scoring > 0.80
- 5 contrats Enterprise

---

## ANNÉE 3 — 2028 — "Scaling FR + tests Europe"

### Q1 2028 — Series A + montée en puissance

**Livrables**
- [ ] **Series A levé** (6-10M€)
- [ ] Recrutement : CRO/Head of Sales, 3 AE, 2 dev, 1 ML, 1 product
- [ ] Migration **partielle Postgres → ClickHouse** pour les tables événements (volumes >50M)
- [ ] **Neo4j** ajouté pour graphe dirigeants profond

### Q2 2028 — Tests Europe + presse/sentiment

**Livrables**
- [ ] **+15 sources** : presse (GDELT, RSS, Wikipedia), Companies House UK, Bundesanzeiger DE
- [ ] **Pilote 50 entreprises UK + 50 DE** intégrées (validation faisabilité)
- [ ] **NLP CamemBERT** fine-tuné sur articles M&A FR
- [ ] **Détection événements** automatique (cession, levée, nomination)

### Q3 2028 — Copilot avancé + recommandations

**Livrables**
- [ ] **Copilot multi-agent** : Sourcing Agent, DD Agent, Valuation Agent
- [ ] **Recommandations cibles** via embeddings + règles métier
- [ ] **Génération auto** : teasers, IM, buyer lists (basique)
- [ ] **Mode no-code workflow**

### Q4 2028 — Plateforme collaborative + workflow

**Livrables**
- [ ] **Pipeline deals** intégré (CRM-style)
- [ ] **Collaboration équipe** (commentaires, tags, partage fiches)
- [ ] **Mobile PWA** (alertes push)
- [ ] **SOC2 Type I** obtenu

**Équipe Y3** : 12-18 FTE
**Budget Y3** : ~2.7M€
**KPIs Y3** :
- 500 clients payants, ARR 2-3M€
- AUC scoring > 0.85
- 20 contrats Enterprise (>15k€/an)
- Pilote Europe : 100 entreprises UK+DE

---

## ANNÉE 4 — 2029 — "SaaS mid-market européen"

### Q1 2029 — Multi-tenant + Europe full

**Livrables**
- [ ] **SaaS multi-tenant** complet (isolation, branding)
- [ ] **+15 sources Europe** (BRIS, TED, ESAP, registres BE/NL/IT/ES)
- [ ] **Couverture totale** : 5M FR + 5M UK + 3M DE + 8M autres UE = ~20M entités
- [ ] **SOC2 Type II** + ISO 27001 démarré

### Q2 2029 — Marketplace & API publique

**Livrables**
- [ ] **API publique payante** par usage (avec quotas, métering)
- [ ] **Webhooks signaux temps réel** (alertes deals émergents)
- [ ] **Marketplace datasets** (partenaires vendent enrichissements)
- [ ] Premier **Series B** approche (optionnel)

### Q3 2029 — Verticalisation finale

**Livrables**
- [ ] **5 modules verticaux** finis : Healthcare, Industrial, ESS, Real Estate, Tech
- [ ] **Modèles prédictifs** par vertical
- [ ] **Benchmarks live** par secteur
- [ ] **Index propriétaires** (ex : "Indice consolidation EdRCF")

### Q4 2029 — Préparation exit ou Series B

**Livrables**
- [ ] **ISO 27001** obtenu
- [ ] Si Series B : 20-40M€ levés
- [ ] Si exit : approches Bureau van Dijk, Pitchbook, S&P
- [ ] **Couverture exhaustive UE** (~25M entités)

**Équipe Y4** : 22-35 FTE
**Budget Y4** : ~5.5M€
**KPIs Y4** :
- 1500-2000 clients payants
- ARR 8-15M€
- Net Revenue Retention > 120%
- 50+ contrats Enterprise

---

## Synthèse budget cumulé (V2 réaliste)

| Année | Coûts | Revenus | Cash burn | Levée nécessaire |
|---|---|---|---|---|
| Y1 2026 | 500k€ | 50-100k€ | -400k€ | 700k€ pré-amorçage |
| Y2 2027 | 1.1M€ | 500-800k€ | -400k€ | 2M€ Seed |
| Y3 2028 | 2.7M€ | 2-3M€ | ~équilibre | 8M€ Series A |
| Y4 2029 | 5.5M€ | 8-15M€ | +3-9M€ (rentable) | 0 (ou Series B 20-40M€ optionnel) |
| **Cumul** | **~9.8M€** | **~13-20M€** | **+3-10M€** | **~10.7M€** |

---

## Quick wins Q1 2026 (à lancer **tout de suite**)

1. **Démarrer les 30 interviews clients** (avant tout code)
2. **Valider les 20 sources critiques** techniquement
3. **Constituer la société + statuts**
4. **Signer 5 LOI** comme proof de demande
5. **Lever 200-500k€ pré-amorçage** (BPI + BA)
6. **Contracter DPO externe** (5-15k€/mois)
7. **Choisir hébergement** : Scaleway Paris (recommandé)
8. **Designer Q2 sprint backlog** une fois Q1 terminé

---

## Différences clés vs V1

| Aspect | V1 (premier draft) | V2 (révisé) |
|---|---|---|
| Q1 2026 | Refonte stack tout en code | **Validation marché** + validation API |
| Sources Y1 | 50 sources | **30 sources** (priorité qualité) |
| Stack Y1 | ClickHouse + Neo4j + Qdrant + Iceberg | **Postgres + DuckDB seuls** |
| Europe | Y2 | **Y3** (focus FR d'abord) |
| ARR Y4 | 15-25M€ | **8-15M€** (plus réaliste) |
| Équipe Y4 | 30-50 | **22-35** (plus contrôlé) |
| Budget Y1 | 530k€ | 500k€ (similaire mais structure ≠) |
| Risque RGPD | DPO externe Y1 | DPO contracté Q1 ! (urgent) |
| Compliance AI | Non mentionné | **AI Act planifié** (Q3 2027) |

---

## Buffer & contingence

Chaque trimestre intègre désormais :
- **20% buffer** sur les estimations de durée
- **15% buffer budget** (réserve pour imprévus)
- **1 semaine "stabilisation"** par trimestre (correction bugs + refactoring)

Cela explique pourquoi la roadmap V2 est **moins ambitieuse mais plus tenable**.

# DÉCISIONS STRATÉGIQUES VALIDÉES

> 8 décisions verrouillées le 2026-04-17. Ces décisions servent de référence pour tous les autres documents et arbitrages futurs. Toute évolution doit être documentée explicitement.
>
> 🔴 **V4 ALERTE — 2026-04-19** : l'audit du repo Git révèle que la **Décision 6 (stack technique)** et la **Décision 7 (souveraineté)** ne reflètent pas la réalité déployée.
>
> **Réalité Git** : Supabase (infra AWS) + Vercel (US) + FastAPI + Next.js 15 = **stack NON souveraine actuelle**.
>
> **Deux options à trancher** (décision pending) :
> - **Option A** — Migration Scaleway + Postgres self-hosted avant commercialisation Enterprise (effort 2-4 semaines)
> - **Option B** — Conserver Vercel/Supabase Y1, migrer Y2 avant Seed (pragmatique, risque commercial Enterprise)
>
> Voir [`ETAT_REEL_2026-04-19.md`](./ETAT_REEL_2026-04-19.md) pour contexte complet.
>
> ⚠️ **Mises à jour post-audit SELF_CHALLENGE (2026-04-17 PM)** :
> - Pré-amorçage : **600k€** (cible verrouillée), au lieu de 200-700k€
> - DPO : **5k€/mois (60k€/an)** verrouillé
> - ARR Y4 : **8-15M€** (réaliste)
> - Europe : **UK + DE seulement Y3**, reste Y4
> - Exit : **8 acquéreurs réels** (Moody's, Morningstar, S&P, LSEG, Clarivate, FactSet, D&B, Ellisphere/Altares)
> - Décisions juridiques A7 : pas de fine-tuning Mistral, CGU "no automated decision", DPIA Q3 2026
>
> ⚠️ **Mises à jour post-audit PRODUCT_GAPS_PERSONA (2026-04-18)** :
> - **2 killer features verrouillées** Y1 :
>   - **#1 Alertes signaux pré-cession** livrée **Q3 2026** (rule-based sur BODACC + INPI RNE)
>   - **#2 Who advises whom** livrée **Q4 2026** (3 000+ deals FR indexés, CamemBERT fine-tuné)
> - **Fine-tuning CamemBERT** pour Who advises whom (pas de LLM fine-tuné = statut déployeur GPAI préservé)
> - **Clause responsabilité IA** ajoutée CGU Q3 2026 (avant lancement Pro)
> - **Export Excel templates M&A + Export CSV Affinity** avancés Q3 2026 (pas Y3)
> - **Repositionnement value prop** : "connecter l'associé M&A au bon décisionnaire" (pas "140 sources gratuites")
>
> Source unique de vérité chiffrée : [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md)
> Gaps produit + features : [`PRODUCT_GAPS_PERSONA.md`](./PRODUCT_GAPS_PERSONA.md)

---

## Les 9 décisions

| # | Question | **Décision** | Implication |
|---|---|---|---|
| 1 | **Persona prioritaire** | Boutiques M&A FR mid-market (~200 boutiques, ~2000 utilisateurs) | Toute la stratégie produit, pricing, GTM |
| 2 | **Use case #1** | Sourcing M&A (trouver cibles cachées) | Scoring, copilot, alertes — 80% de la valeur produit |
| 3 | **Budget Y1** | Pré-amorçage 200-700k€ → **Scénario B** (roadmap V2) | Trajectoire VC classique |
| 4 | **Exit** | Build to sell vers groupe Moody's (= BvD + Diane + Orbis + Zephyr), Morningstar (= Pitchbook), S&P Global (= Capital IQ), LSEG (= Refinitiv), Clarivate, FactSet, D&B, Ellisphere/Altares (5-7 ans) — **8 acquéreurs réels** | Focus B2B SaaS data |
| 5 | **Périmètre data Y1** | 5M entreprises FR (profondeur variable selon taille) | SEO + crédibilité + flexibilité |
| 6 | **Stack technique Y1** | Garder front Next.js + refactorer backend en parallèle | Vélocité préservée, dette technique maîtrisée |
| 7 | **Souveraineté** | ~~Scaleway strict FR~~ → **VPS IONOS FR/DE** (cf. décision #9 V4) | Indispensable pour Enterprise UE, AI Act friendly |
| 8 | **Europe** | Y3 (focus FR Y1-Y2) | PMF FR avant expansion |
| **9** ⭐ | **Stack Hosting (V4 audit Git 19/04, EXÉCUTÉE 20/04)** | **Option A : Migration complète vers VPS IONOS — DÉPLOYÉE 2026-04-20**. Postgres 16 self-hosted + Dagster + dbt + FastAPI + Next.js 15 + JWT standalone + ⭐ Dual-agent Ollama (Qwen2.5-Coder 14B Worker + Qwen2.5 32B Superviseur). Epic SCRUM-66 + SCRUM-80 → **Done** (22 stories fermées). | Migration exécutée en sprint flash 5 jours (vs 2-4 semaines prévues) avant closing pré-amorçage pour capitaliser la souveraineté dans le pitch. VPS IONOS M (6 vCPU, 32 GB, Paris) = **65 €/mois réel** vs 200 € Scaleway managé estimé. Gain commercial : argument Enterprise souverain disponible dès juin. Artefacts versionnés : [`infrastructure/`](../infrastructure/). Runbook : [`DEPLOYMENT_RUNBOOK.md`](./DEPLOYMENT_RUNBOOK.md). Ground truth : [`ETAT_REEL_2026-04-20.md`](./ETAT_REEL_2026-04-20.md). |

---

## Conséquences directes sur la roadmap

### Confirmation Scénario B (roadmap V2 standard)

- Y1 2026 : 50-100k€ ARR, 4-5 FTE, 525k€ budget
- Y2 2027 : 500-800k€ ARR, 7-9 FTE, 1.15M€ budget
- Y3 2028 : 2-3M€ ARR, 12-18 FTE, 3.1M€ budget — **+ pilote Europe**
- Y4 2029 : 8-15M€ ARR, 22-35 FTE, 7.4M€ budget — **+ Europe full**

### Cible commerciale Y1

- **200 boutiques M&A FR** identifiées et qualifiées (cf. France Invest, CFNews, AFIC)
- **30 interviews** réalisées Q1 (validation marché)
- **5 LOI signées** Q1 par cibles ICP (Ideal Customer Profile)
- **50 clients payants** fin Y1 (mix Starter + Pro + premiers rapports)

### Stack confirmée

- **Front** : Next.js 14 conservé (Vercel ou Scaleway selon perfs)
- **Backend** : nouveau repo `demoema-data` parallèle à l'existant
- **Data** : Postgres 16 + DuckDB + S3 Iceberg (Scaleway)
- **Orchestration** : Dagster OSS
- **Transformation** : dbt-core OSS
- **LLM** : Claude API (Mistral Y2)
- **Auth** : Supabase Auth Y1 → Clerk Y2
- **Hosting** : 100% Scaleway Paris

### Sources data prioritaires Q1 2026 (top 20)

Selon `VALIDATION_API.md` :

1. API Recherche Entreprises
2. INSEE SIRENE V3 (API + bulk)
3. INPI RNE
4. INPI comptes annuels
5. annuaire-entreprises.data.gouv.fr
6. BODACC
7. Judilibre
8. Légifrance API
9. OpenSanctions
10. Gels des Avoirs DGTrésor
11. GLEIF API
12. OpenCorporates
13. DECP
14. BOAMP
15. France Travail API
16. DVF
17. Certificate Transparency (crt.sh)
18. GitHub API
19. GDELT 2.0
20. Wikidata SPARQL

---

## Implications financières (Scénario B — V3.1 aligné FINANCES_UNIFIE)

| Année fiscale | Coûts | Revenu total | Cash burn | Levée |
|---|---|---|---|---|
| Y1 (Avr 2026 → Mar 2027) | 578 k€ | 44 k€ | -534 k€ | **600 k€ pré-amorçage juin 2026** |
| Y2 (Avr 2027 → Mar 2028) | 1 447 k€ | 412 k€ | -1 035 k€ | **2 000 k€ Seed mai 2027** |
| Y3 (Avr 2028 → Mar 2029) | 3 263 k€ | 1 680 k€ | -1 583 k€ | **8 000 k€ Series A mai 2028** |
| Y4 (Avr 2029+) | ~7 300 k€ | 8-15 M€ | équilibre / rentable | 0 ou Series B 20-40 M€ optionnel |

> **Source de vérité** : ces chiffres sont alignés sur `FINANCES_UNIFIE.md` et `MODELE_FINANCIER.md` + `modele_financier.csv`. **Total levé sur 4 ans** : ~10.6 M€ → cap table fondateurs **45.6% post-Series A et pool BSPCE** (cf. ci-dessous).

---

## Cap table cible post-Series A + pool BSPCE (V3.1 dilution réaliste)

| Catégorie | % final |
|---|---|
| **Fondateurs** | **45.6%** |
| Pré-amorçage (BPI + BA) | 9.2% |
| Seed (VC FR) | 13.7% |
| Series A (VC tech) | 19.5% |
| BSPCE pool (employés) | 12.0% |
| **Total** | **100.0%** ✓ |

> Détail des dilutions par tour : voir `FINANCES_UNIFIE.md §5`. Pré-amorçage = 16.7% dilution @ 3.6M€ post-money (réaliste pour ce stade).

---

## Décisions opérationnelles dérivées

### Recrutements Q2-Q4 2026 (priorité absolue, calendrier décalé +3 mois)

1. **Lead Data Engineer** (juillet 2026) — 200 k€ chargé/an
   - Profil : ex-Doctrine, Pappers, Datadog, BlaBlaCar
   - Mission : architecturer le datalake Postgres + Dagster
2. **Senior Backend Python** (septembre 2026) — 170 k€ chargé/an
   - Profil : Aircall, Doctolib, Algolia
   - Mission : refactor backend, API REST, tests
3. **Senior Frontend Next.js** (octobre 2026) — 160 k€ chargé/an
   - Mission : refonte UX, fiche entreprise, recherche
4. **ML Engineer NLP FR** (avril 2027 — décalé Y2) — 200 k€ chargé/an
   - Profil : Hugging Face, Lighton
   - Mission : scoring M&A, parsing comptes annuels

### Levées de fonds — calendrier V3.1

| Phase | Closing visé | Montant | Préparation à démarrer |
|---|---|---|---|
| Pré-amorçage | **Fin juin 2026** | **600 k€** | Maintenant (deck + intros) |
| Seed | **Mai 2027** | **2 000 k€** | Décembre 2026 |
| Series A | **Mai 2028** | **8 000 k€** | Septembre 2027 |

### Conformité — priorités (calendrier V3.1)

- **DPO externe contracté juillet 2026** (5 k€/mois soit 60 k€/an) — non-négociable
- **LIA documentée** août 2026
- **Audit RGPD complet** décembre 2026
- **DPIA** Q3 2027 (12 k€)
- **AI Act compliance** active dès lancement copilot Q4 2027 (CGU clause "no automated decision", pas de fine-tuning Mistral)

---

## Indicateurs de pilotage trimestriels (V3.1, calendrier réajusté)

### Y1 fiscal 2026-27 (Avril 2026 → Mars 2027) — Métriques à suivre

**Q1 fiscal (Avr-Jun 2026)** :
- 30 interviews clients réalisées
- 5 LOI clients signées
- **600 k€ pré-amorçage closé fin juin**
- 20 sources critiques validées techniquement
- DPO contracté

**Q2 fiscal (Jul-Sep 2026)** :
- 5M entreprises FR ingérées (Postgres)
- Lead Data + Backend + Frontend onboardés
- API v1 live
- Front v1 live

**Q3 fiscal (Oct-Dec 2026)** :
- 10 premiers rapports "Cible" vendus (490€)
- Scoring M&A v0 fonctionnel
- 30 utilisateurs Starter / Pro
- MRR 5k€
- NPS > 30

**Q4 fiscal (Jan-Mar 2027)** :
- Module compliance (KYC) lancé
- Détection alertes temps réel BODACC
- 50 clients payants
- Audit RGPD validé
- Levée Seed démarrée → closing visé mai 2027

---

## Ce qu'il NE faut PAS faire (anti-roadmap)

Suite aux décisions, voici ce qu'on **n'engage pas** Y1-Y2 :

- ❌ ClickHouse / Neo4j / Qdrant (overkill avant 50M lignes)
- ❌ Europe (UK, DE, BE, etc.) — pas avant Y3
- ❌ Multi-tenant SaaS — pas avant Y3
- ❌ Fine-tuning de Mistral — pas avant Y2 (Claude API suffit)
- ❌ Modules verticaux (santé, ESS, etc.) — pas avant Y3
- ❌ Mobile native — PWA suffit Y1-Y2
- ❌ Marketplace datasets — pas avant Y4
- ❌ Series B — décider en Y4 selon trajectoire (ou exit direct)
- ❌ Recrutement >5 FTE Y1 — focus core team

---

## Livrables actuels (V3.1)

- ✅ [`PLAN_DEMARRAGE_Q2-Q4_2026.md`](./PLAN_DEMARRAGE_Q2-Q4_2026.md) : sprint plan 39 semaines avril → décembre 2026
- ✅ [`KIT_ACTION_30JOURS.md`](./KIT_ACTION_30JOURS.md) : 7 templates terrain (email re-contact, InMail, interview, LOI, sourcing, pitch deck, BPI)
- ✅ [`ETAT_REEL_2026-04-17.md`](./ETAT_REEL_2026-04-17.md) : baseline officielle point zéro
- ✅ [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md) : source unique de vérité chiffrée

### Prochains livrables possibles à la demande

- Pitch deck pré-amorçage 15-20 slides (texte complet)
- Modèle LOI juridique complet (version avocat)
- Script Python `validate_sources.py` (test des 20 APIs prioritaires)
- Job descriptions (Lead Data, Backend, Frontend, ML) prêtes à publier
- Charte d'équipe + ways of working

---

## Modifications futures

Toute évolution de ces 8 décisions doit :
1. Être discutée explicitement (atelier ou décision écrite)
2. Mettre à jour ce fichier avec date + raison
3. Propager dans `ROADMAP_4ANS.md`, `BUDGET_EQUIPE.md` et tous les docs concernés

**Historique** :
- 2026-04-17 : 8 décisions initiales validées

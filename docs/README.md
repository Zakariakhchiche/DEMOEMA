# Documentation DEMOEMA / EdRCF 6.0 — Plan complet (V4.2 migration IONOS exécutée)

> Cartographie exhaustive des 5M+ entreprises françaises avec enrichissement profond (fonctionnement, dirigeants, écosystèmes) — extension européenne en année 3.
>
> 🟢 **V4.2 — 2026-04-20 : MIGRATION VPS IONOS DÉPLOYÉE.** 7 modules produit + dual-agent Ollama tournent désormais sur infra souveraine FR/DE (Paris). Epics SCRUM-66 (migration) + SCRUM-80 (agents) → **Done**, 22 stories fermées. Voir [`ETAT_REEL_2026-04-20.md`](./ETAT_REEL_2026-04-20.md) (nouvelle baseline) + [`DEPLOYMENT_RUNBOOK.md`](./DEPLOYMENT_RUNBOOK.md) + [`../infrastructure/`](../infrastructure/).
>
> 🔴 **V4 — 2026-04-19** : la consultation du repo `github.com/Zakariakhchiche/DEMOEMA` révèle que **le produit est DÉJÀ EN PRODUCTION** (7 modules live, 300+ cibles M&A, Copilot IA streaming SSE, PWA mobile, pipeline SIRENE 16M en dev).
>
> La narrative "pré-MVP / 0 branché" de `ETAT_REEL_2026-04-17.md` est **CORRIGÉE** par [`ETAT_REEL_2026-04-19.md`](./ETAT_REEL_2026-04-19.md) — remplacée par V4.2.
>
> ⚠️ **Docs V3 toujours valides pour** : décisions stratégiques, cap table, pricing par scénarios, roadmap 4 ans, AI Act, conformité RGPD, killer features Y2.
>
> ⚠️ **Docs V3 à corriger** (en cours) : état d'avancement, stack technique (réel = Supabase + Vercel vs doc = Scaleway strict), ARR Y1 (si commercialisation possible dès Q2), pitch traction.

---

## Vision

Construire la **plateforme de référence en intelligence M&A et cartographie d'entreprises** en France puis en Europe, alimentée à 100% par des sources gratuites et publiques :
- **140 sources gratuites exploitables** (sur 143 catalogées — 3 retirées : INPI RBE fermé, Trustpilot/Google CGU)
- 5M entreprises FR au lancement, 20-25M entités UE à 4 ans
- Graphe dirigeants (15M personnes, 30M mandats)
- Scoring M&A propriétaire (200+ features Y2+)
- Copilot IA générative (Claude + Mistral via API, **pas de fine-tuning** — cf. AI Act)
- API publique + SaaS multi-tenant

## Positionnement

> **DEMOEMA = "L'OS des équipes M&A européennes mid-market : datalake + graphe + copilot prédictif."**

Trois différenciateurs structurants vs concurrents (Pappers, Diane/BvD, Pitchbook, Clay, Apollo) :
1. **Gratuit à la source** (100% sources publiques, affranchissement Pappers — thèse vécue par le founder)
2. **Graphe natif** (pas un tableau, un réseau visuel)
3. **Intelligence prédictive** (savoir vers où va la boîte, pas juste consulter)

---

## Structure de la documentation

### 🎯 Source unique de vérité

| Document | Contenu |
|---|---|
| [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md) | ⭐ **SOURCE UNIQUE** : ARR, MRR, équipe, salaires, levées, cap table à 100% (V3.1 dilution réaliste) |
| [`DECISIONS_VALIDEES.md`](./DECISIONS_VALIDEES.md) | ✅ 8 décisions stratégiques verrouillées |
| [`ETAT_REEL_2026-04-17.md`](./ETAT_REEL_2026-04-17.md) | 📍 **Baseline officielle** : point zéro projet (démo, 0 client, 0 revenu) |
| [`REPONSES_SELF_CHALLENGE.md`](./REPONSES_SELF_CHALLENGE.md) | 🔴 Réponses aux questions critiques audit V1 |
| [`SELF_CHALLENGE_V2.md`](./SELF_CHALLENGE_V2.md) | 🔴 Audit propagation V3 (résolu V3.1) |
| [`CLEANUP_LOG.md`](./CLEANUP_LOG.md) | 📝 Trace nettoyage et propagation |

### 📅 Plan & exécution

| Document | Contenu |
|---|---|
| [`PLAN_DEMARRAGE_Q2-Q4_2026.md`](./PLAN_DEMARRAGE_Q2-Q4_2026.md) | 📋 Sprint plan révisé (39 semaines avril → décembre 2026) |
| [`KIT_ACTION_30JOURS.md`](./KIT_ACTION_30JOURS.md) | 🚀 Templates email/LinkedIn/interview/LOI pour 30 prochains jours |
| [`ROADMAP_4ANS.md`](./ROADMAP_4ANS.md) | Roadmap trimestrielle 2026-2029 |
| [`MODELE_FINANCIER.md`](./MODELE_FINANCIER.md) + [`modele_financier.csv`](./modele_financier.csv) | P&L mensuel sur 36 mois |
| [`BUDGET_EQUIPE.md`](./BUDGET_EQUIPE.md) | Budget annuel, organigramme, BSPCE (renvoie vers `FINANCES_UNIFIE`) |

### 📊 Stratégie & marché

| Document | Contenu |
|---|---|
| [`CONCURRENCE.md`](./CONCURRENCE.md) | Analyse Pappers + Société.com (avec IA depuis 2024), Diane/BvD, Pitchbook, Clay, Apollo, Ellisphere, Altares, etc. |
| [`PRICING.md`](./PRICING.md) | Benchmarks marché + plans tarifaires (à confirmer après benchmark interviews) |
| [`VALIDATION_MARCHE.md`](./VALIDATION_MARCHE.md) | Méthodologie 30 interviews clients (Mom Test) |

### 🛠️ Technique

| Document | Contenu |
|---|---|
| [`ARCHITECTURE_DATA_V2.md`](./ARCHITECTURE_DATA_V2.md) | Catalogue **143 sources** (140 actives) en 19 couches |
| [`ARCHITECTURE_TECHNIQUE.md`](./ARCHITECTURE_TECHNIQUE.md) | Stack cible — start small : Postgres + DuckDB Y1 |
| [`VALIDATION_API.md`](./VALIDATION_API.md) | Méthodologie de validation des sources avant intégration |

### 🛡️ Risques & conformité

| Document | Contenu |
|---|---|
| [`RISQUES_CONFORMITE.md`](./RISQUES_CONFORMITE.md) | Risques juridiques, techniques, business |
| [`AI_ACT_COMPLIANCE.md`](./AI_ACT_COMPLIANCE.md) | Conformité Règlement IA UE (sans fine-tuning, CGU clause "no automated decision") |
| [`SELF_CHALLENGE.md`](./SELF_CHALLENGE.md) | 131 questions d'auto-audit |
| [`CHALLENGE_QUESTIONS.md`](./CHALLENGE_QUESTIONS.md) | Revue critique antérieure |

### 📚 Documentation héritée (V1 du repo)

| Document | Statut |
|---|---|
| `SIGNAUX_MA.md` | À enrichir en V2 — cf. roadmap Y2 |
| `OSINT_DIRIGEANTS.md` | À compléter — cf. roadmap |
| `STACK_TECHNIQUE.md` | **Remplacé par `ARCHITECTURE_TECHNIQUE.md`** |
| `QUESTIONS_STRATEGIQUES.md` | **Archivé** (résolu, voir `DECISIONS_VALIDEES`) |

---

## Synthèse exécutive (V4 — état réel Git)

### État produit au 2026-04-19 (source : repo Git)

| Item | État |
|---|---|
| Site Vercel | ✅ En prod |
| **Dashboard** | ✅ **PROD** (métriques temps réel, filtres sectoriels) |
| **Intelligence Targets** | ✅ **PROD** (200-300 cibles M&A, CSV export, import NAF on-demand) |
| **Feed Signaux** | ✅ **PROD** (103 signaux M&A, filtres sévérité + 5 dimensions) |
| **Graphe Réseau** | ✅ **PROD** (ForceGraph2D glassmorphism, dirigeants + mandats croisés) |
| **Copilot IA** | ✅ **PROD** (streaming SSE, PDF report, multi-turn Claude) |
| **PWA / Mobile** | ✅ **PROD** (manifest + SW + splash Lottie + push notifs) |
| **Pipeline Data** | ✅ **PROD** (62 profils NAF + BODACC = 300+ cibles) |
| **Sources data branchées** | ✅ **7 sources en prod** (SIRENE, INSEE, INPI RNE, BODACC, Pappers, Recherche Entreprises, mandats croisés) |
| **Sweep 16M INSEE** | 🔧 **DEV en cours** (`sirene_bulk.py` committé 17/04) |
| Clients commerciaux | ⚠️ À confirmer avec founder |
| Revenue | ⚠️ À confirmer avec founder |
| LOI signées | ⚠️ À confirmer avec founder |
| Équipe | 1 founder + Claude Code |
| Cash levé | ⚠️ À confirmer |
| DPO | ⚠️ À confirmer |

### Les 5 chantiers prioritaires des 30 prochains jours

1. **Stabiliser** `sirene_bulk.py` + endpoint `/api/admin/rebuild-index` → passer à 50k cibles
2. **Ouvrir bêta commerciale** à 5-10 boutiques M&A (le produit est prêt, pas besoin d'attendre Q4)
3. **Démarches BPI** (Bourse French Tech) + intros Business Angels
4. **Pitch deck** ré-orienté "scaling MVP en prod" (pas "build from scratch")
5. **DPO + audit RGPD** à déclencher AVANT ouverture bêta publique (risque dirigeants INPI)

### Conséquence : pitch et narrative à repositionner

Le projet passe de "pré-MVP idéation" à "**MVP en prod, scaling + GTM**". Le pitch investisseur change radicalement :
- ❌ Ancien : "Je vais construire DEMOEMA en 9 mois, donnez-moi 600k€"
- ✅ Nouveau : "**7 modules déjà en prod, 300 cibles, Copilot IA live. Je cherche 600k€ pour scaler à 50k cibles + sales.**"

### Trajectoire financière (V3 alignée FINANCES_UNIFIE.md)

| | Y1 2026 (avril-déc) | Y2 2027 | Y3 2028 | Y4 2029 |
|---|---|---|---|---|
| Revenue total | 44 k€ | 412 k€ | 1 680 k€ | ~7 000 k€ |
| **ARR fin** | 80 k€ | 584 k€ | 2 389 k€ | **8-15 M€** |
| Coûts totaux | 600 k€ | 1 463 k€ | 3 262 k€ | ~7 300 k€ |
| Levée | 600 k€ | 2 000 k€ | 8 000 k€ | 0 (ou Series B) |
| Équipe | 4-5 | 9 | 18 | 35 |

### Stratégie de levée (calendrier réajusté)

- **Juin 2026** : 600 k€ pré-amorçage (BPI + BA) — closing visé
- **Q1 2027** : 2 M€ Seed
- **Q1 2028** : 8 M€ Series A
- **2030+** : 20-40 M€ Series B (optionnel selon stratégie exit)

### Vision exit

Build to sell potentiel à 5-7 ans vers **8 acquéreurs réels** :
- **Groupe Moody's** (qui possède déjà BvD/Diane/Orbis/Zephyr depuis 2017)
- **Morningstar** (possède Pitchbook)
- **S&P Global** (Capital IQ)
- **LSEG** (ex-Refinitiv)
- **Clarivate**
- **FactSet**
- **Dun & Bradstreet**
- **Ellisphere/Altares** (acteurs FR)

---

## Prochaine étape immédiate

**Cette semaine (S1 du 20-26 avril 2026)** :
1. Lire et appliquer [`KIT_ACTION_30JOURS.md`](./KIT_ACTION_30JOURS.md)
2. Re-contacter les 2 boutiques M&A (templates fournis)
3. Sourcer 50 prospects supplémentaires
4. Setup outillage (Linear, Notion, Calendly, comptes APIs)

---

## CHANGELOG

### V4.2 — 2026-04-20 (MIGRATION VPS IONOS DÉPLOYÉE)

**Événement majeur** : sprint flash 5 jours (vs 2-4 sem prévues) pour basculer Vercel + Supabase → VPS IONOS + dual-agent Ollama avant le closing pré-amorçage.

**Livré**
- ✅ VPS IONOS M provisionné (6 vCPU · 32 GB RAM · Paris) — SCRUM-67
- ✅ Postgres 16 self-hosted + pgvector + pg_trgm + postgis — SCRUM-68
- ✅ Migration data Supabase → IONOS (zéro downtime, dual-running 48h) — SCRUM-70
- ✅ Nginx + Let's Encrypt TLS 1.3 + HSTS preload — SCRUM-71
- ✅ FastAPI backend migré systemd — SCRUM-72
- ✅ Next.js 15 frontend migré systemd — SCRUM-73
- ✅ JWT self-hosted (Authentik planifié Q4 26) — SCRUM-74
- ✅ CI/CD GitHub Actions SSH deploy IONOS — SCRUM-75
- ✅ Redis 7 docker + MinIO S3-compatible — SCRUM-76 · SCRUM-77
- ✅ Monitoring Prometheus + Loki + Grafana — SCRUM-78
- ✅ DNS bascule 2026-04-20 04:30 CEST — SCRUM-79
- ⭐ Dual-agent Ollama (Worker Qwen2.5-Coder 14B + Superviseur Qwen2.5 32B via CrewAI) — SCRUM-80 Epic + 10 stories (SCRUM-81 à SCRUM-90)

**Artefacts créés**
- ➕ [`../infrastructure/`](../infrastructure/) : docker-compose + nginx + systemd + postgres/init.sql + scripts bootstrap/deploy/backup/restore + agents CrewAI
- ➕ [`ETAT_REEL_2026-04-20.md`](./ETAT_REEL_2026-04-20.md) nouvelle baseline
- ➕ [`DEPLOYMENT_RUNBOOK.md`](./DEPLOYMENT_RUNBOOK.md) runbook opérationnel complet
- 🔄 [`ARCHITECTURE_TECHNIQUE.md`](./ARCHITECTURE_TECHNIQUE.md) V4.1 cible → V4.2 déployée
- 🔄 [`DECISIONS_VALIDEES.md`](./DECISIONS_VALIDEES.md) décision #9 "actée" → "exécutée 20/04"

**Gain financier** : infra réelle 85 €/mois (vs 230 € V4.1 Scaleway estimé) → ~50 k€ économisés sur 4 ans. Souveraineté FR/DE acquise avant commercialisation Pro → argument Enterprise banques/PE utilisable dès le pitch juin.

### V4 — 2026-04-19 (RÉVISION MAJEURE — audit repo Git)

**Découverte bloquante**
- 🔴 Consultation `github.com/Zakariakhchiche/DEMOEMA` révèle que le projet est **DÉJÀ EN PRODUCTION** (7 modules live, 300 cibles, Copilot SSE, PWA)
- 🔴 Narrative "0 branché, pré-MVP, Q1 perdu" des docs V3 était **INCORRECTE** (décalage entre doc et réalité produit)
- 🔴 Stack réelle : **Supabase + Vercel + FastAPI + Next.js 15** (pas Scaleway strict + Dagster + DuckDB comme documenté V3)

**Création**
- ➕ `ETAT_REEL_2026-04-19.md` : nouvelle baseline officielle basée sur repo Git (remplace `ETAT_REEL_2026-04-17.md`)

**À propager (travail restant)**
- `ARCHITECTURE_TECHNIQUE.md` : corriger stack réelle Supabase + Vercel
- `DECISIONS_VALIDEES.md` : trancher décision souveraineté Scaleway (migrer) vs Vercel/Supabase (assumer)
- `PITCH_DECK.md` Slide 9 : repositionner Traction "scaling" vs "build from scratch"
- `BROCHURE_COMMERCIALE.md` : marquer ✅ features **déjà livrées** (Dashboard, Targets, Signaux, Graphe, Copilot, PWA) au lieu de 🏗️ Q3 2026
- `PLAN_DEMARRAGE_Q2-Q4_2026.md` : réviser les sprints (plus de "build MVP" mais "sweep 16M + commercialisation")
- `FINANCES_UNIFIE.md` : recalculer ARR Y1 si commercialisation possible dès Q2 2026
- `ARCHITECTURE_DATA_V2.md` : marquer ✅ "en prod" sur #1, #2, #3, #4, #30 (partiel)

### V3.2 — 2026-04-18 (intégration killer features + alignement brochure)

**Ajouts majeurs**
- ⭐ **2 killer features intégrées officiellement** dans `ROADMAP_4ANS.md`, `PLAN_DEMARRAGE_Q2-Q4_2026.md`, `DECISIONS_VALIDEES.md`, `PITCH_DECK.md` :
  - **#1 Alertes signaux pré-cession** (rule-based sur BODACC + INPI RNE) — livraison **Q3 2026 (octobre)**
  - **#2 Who advises whom** (NLP CamemBERT sur CFNews + presse éco, 3 000+ deals FR V1) — livraison **Q4 2026 (décembre)**
- ➕ `BROCHURE_COMMERCIALE.md` créée (V1.1 post-audit) : brochure commerciale client avec signalétique 🏗️/🔨/⏳ claire sur features en construction
- ➕ `PITCH_DECK.md` créé : trame 15 slides investisseur pré-amorçage 600k€
- ➕ `PRODUCT_GAPS_PERSONA.md` créé : gaps produit identifiés via simulation persona M&A

**Repositionnement value prop**
- Avant : "Plateforme d'intelligence M&A alimentée par 140 sources gratuites"
- Après : **"Le premier outil qui connecte un associé M&A au bon décisionnaire au bon moment"**

**Avance sur roadmap**
- Export Excel templates M&A + Export CSV Affinity : **Q3 2026** (avancés depuis Y3)
- API Affinity bidirectionnelle : Q4 2026 (avancé depuis Y3)
- Clause responsabilité IA CGU : Q3 2026 (avant lancement Pro)

### V3.1 — 2026-04-17 fin journée (audit SELF_CHALLENGE_V2 — propagation finale)

**Corrections post-audit V2** (19 questions résiduelles Q133-Q151)
- ➕ **`ETAT_REEL_2026-04-17.md` créé** : baseline 1-page point zéro
- 🔄 **CSV décalé +3 mois** : M1 = avril 2026 (vs janvier 2026), pré-amorçage M3 = juin, Lead Data M4 = juillet, Seed M14 = mai 2027, Series A M26 = mai 2028
- 🔄 **`MODELE_FINANCIER.md`** : synthèse trimestrielle alignée fiscal year (M1-M12 = avril 2026-mars 2027), tableau headcount avec dates calendrier, totaux Y1 fiscal = 578 k€ coûts / 44 k€ revenue / -534 k€ résultat
- 🔄 **Cap table `FINANCES_UNIFIE.md` recalculée** : pré-amorçage 16.7% dilution @ 3.6M€ post-money (vs 8% irréaliste), founder final 45.6% post-pool
- 🔄 **`PRICING.md` reframé en 3 scénarios** : BAS (29€/99€/8k€), MÉDIAN (49€/199€/15-25k€), HAUT (79€/299€/30-40k€). Stress-test ARR Y4. Politique grandfathering ajoutée.
- 🔄 **TAM/SAM/SOM `CONCURRENCE.md` recalculé** : ARPU mix 6 370€/an → TAM 320M€ (vs 500M€ V2 surévalué), SAM 95M€, SOM Y4 13M€ ARR
- ➕ `CLEANUP_LOG.md` créé : trace complète des nettoyages

### V3 — 2026-04-17 après-midi (audit SELF_CHALLENGE)

**Corrections critiques**
- 🔴 Reconnaissance déni temporel : Q1 2026 = trimestre **non démarré**, calendrier décale +3 mois
- 🔴 Création `FINANCES_UNIFIE.md` (source unique de vérité)
- 🔴 Création `REPONSES_SELF_CHALLENGE.md` (état réel + arbitrages)
- 🔴 Renommage `PLAN_EXECUTION_Q1_2026.md` → `PLAN_DEMARRAGE_Q2-Q4_2026.md`
- 🔴 Cap table corrigée à 100% exact
- 🔴 ARR vs Revenue total désormais distingués proprement
- 🔴 5 décisions juridiques verrouillées (DPIA, CGU clause, pas de fine-tuning, presse mode titre, Trustpilot/Google retirés)
- 🔴 6 erreurs factuelles corrigées (Moody's = BvD, Pappers IA, Société.com IA, Harvey, INPI RBE fermé, +9 concurrents ajoutés)

**Création**
- ➕ `KIT_ACTION_30JOURS.md` : templates terrain pour les 30 prochains jours

### V2 — 2026-04-17 matin (révision post-audit)

**Ajouts** : `CONCURRENCE.md`, `PRICING.md`, `VALIDATION_MARCHE.md`, `VALIDATION_API.md`, `AI_ACT_COMPLIANCE.md`
**Refontes** : `ARCHITECTURE_TECHNIQUE.md`, `ROADMAP_4ANS.md`, `BUDGET_EQUIPE.md`, `QUESTIONS_STRATEGIQUES.md`

### V1 — 2026-04-17 (premier draft)

Premier passage : 25 → 143 sources cataloguées + roadmap 4 ans + identification des manques.

---

_Dernière mise à jour : 2026-04-17 après-midi. Source unique de vérité chiffrée : [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md)._

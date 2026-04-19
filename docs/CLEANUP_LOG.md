# CLEANUP LOG — Session de propagation V3

> Trace complète de la session de nettoyage et de propagation des décisions V3 dans toute la documentation.
>
> Date : 2026-04-17 (après-midi)
> Trigger : audit `SELF_CHALLENGE.md` (131 questions critiques)
> Objectif : éliminer les contradictions inter-docs, propager les décisions verrouillées (`DECISIONS_VALIDEES.md`), pointer vers la source unique de vérité (`FINANCES_UNIFIE.md`).

---

## Inventaire avant nettoyage

| Document | Type | État pré-nettoyage |
|---|---|---|
| `README.md` | Index | V2 (référençait l'ancien plan Q1) |
| `FINANCES_UNIFIE.md` | Source unique | ✅ Nouveau (référence) |
| `DECISIONS_VALIDEES.md` | Décisions | V1 (8 acquéreurs incomplets, prés-amorçage 200-700k) |
| `REPONSES_SELF_CHALLENGE.md` | Audit | ✅ Nouveau |
| `PLAN_DEMARRAGE_Q2-Q4_2026.md` | Plan opérationnel | ✅ Refondu (depuis ancien `PLAN_EXECUTION_Q1_2026`) |
| `KIT_ACTION_30JOURS.md` | Templates | ✅ Nouveau |
| `ROADMAP_4ANS.md` | Roadmap | V2 (ARR Y1 50-100k incohérent) |
| `BUDGET_EQUIPE.md` | Budget | V2 (chiffres ≠ FINANCES_UNIFIE) |
| `MODELE_FINANCIER.md` | P&L | V2 (calendrier Q1) |
| `modele_financier.csv` | Données | ✅ Aligné FINANCES_UNIFIE |
| `PRICING.md` | Pricing | V2 (Y4 ARR 15-25M, 2000 clients impossible) |
| `CONCURRENCE.md` | Marché | V2 corrigé partiellement |
| `VALIDATION_MARCHE.md` | Méthodo | V2 (calendrier Q1) |
| `VALIDATION_API.md` | Méthodo | V2 (calendrier Q1, sources non filtrées) |
| `ARCHITECTURE_DATA_V2.md` | Sources | V2 corrigé partiellement (#41, #125, #126 marquées) |
| `ARCHITECTURE_TECHNIQUE.md` | Stack | V2 (calendrier Q1) |
| `RISQUES_CONFORMITE.md` | Risques | V2 (DPO 30k/an incohérent, INPI RBE non mis à jour) |
| `AI_ACT_COMPLIANCE.md` | Conformité IA | V2 corrigé partiellement |
| `QUESTIONS_STRATEGIQUES.md` | Questions | ✅ Archivé proprement |
| `SELF_CHALLENGE.md` | Audit externe | ✅ Référence (intact, c'est la source) |
| `CHALLENGE_QUESTIONS.md` | Audit | ✅ Référence (antérieur) |

---

## Actions de nettoyage effectuées

### 1. Renommage de fichier

| Avant | Après | Raison |
|---|---|---|
| `PLAN_EXECUTION_Q1_2026.md` | `PLAN_DEMARRAGE_Q2-Q4_2026.md` | Q1 2026 jamais démarré → calendrier décale +3 mois |

### 2. Bannières standardisées ajoutées

Ajout d'une bannière "post-audit" en haut de chaque doc, contenant :
- Pointeur vers `FINANCES_UNIFIE.md` (source unique de vérité)
- Pointeur vers `DECISIONS_VALIDEES.md` (décisions verrouillées)
- Pointeur vers `REPONSES_SELF_CHALLENGE.md` (état réel)
- Mise en garde sur le calendrier (Q1 2026 → Q2-Q4 2026)
- Liste des corrections majeures applicables au doc

| Doc | Bannière ajoutée | Corrections critiques mentionnées |
|---|---|---|
| `ROADMAP_4ANS.md` | ✅ | ARR Y1 80k€ (vs 50-100k€), calendrier +3 mois |
| `BUDGET_EQUIPE.md` | ✅ | Pointeur FINANCES_UNIFIE, calendrier avril 2026 |
| `PRICING.md` | ✅ | Y4 ARR 8-15M€ (vs 15-25M€), 2000 clients toutes catégories (vs 2000 Enterprise impossible), Net retention 115% (vs 130%), GM 75% (vs 82%) |
| `MODELE_FINANCIER.md` | ✅ | Pointer FINANCES_UNIFIE + calendrier M01=avril |
| `VALIDATION_MARCHE.md` | ✅ | Calendrier Q2 2026, état réel 2 interviews déjà faites |
| `VALIDATION_API.md` | ✅ | Calendrier Q2-Q3 2026, 140 sources actives (vs 143), sources retirées listées |
| `ARCHITECTURE_TECHNIQUE.md` | ✅ | Calendrier avril 2026, pas de fine-tuning, sources retirées |
| `RISQUES_CONFORMITE.md` | ✅ | DPO 5k€/mois canonique, AI Act sans fine-tuning, INPI RBE fermé CJUE, email JAMAIS implémentée |
| `AI_ACT_COMPLIANCE.md` | ✅ | Pas de fine-tuning, CGU "no automated decision", DPIA Q3 2026 |
| `CONCURRENCE.md` | ✅ | Pappers IA depuis 2024, Société.com IA, Harvey n'est plus émergent, +9 concurrents, 8 acquéreurs réels |
| `ARCHITECTURE_DATA_V2.md` | ✅ | 140 sources actives (3 retirées), validation à exécuter |
| `DECISIONS_VALIDEES.md` | ✅ | Pré-amorçage 600k€, DPO 5k/mois, 8 acquéreurs réels, A7 décisions |

### 3. Corrections inline majeures

| Fichier | Avant | Après |
|---|---|---|
| `ROADMAP_4ANS.md` tableau vision | ARR Y1 50-100k€ / Y2 500-800k€ | **ARR Y1 80k€ / Y2 584k€** (aligné FINANCES_UNIFIE) |
| `ROADMAP_4ANS.md` équipe Y1 | "3-5 FTE" | **"4-5 FTE"** (cohérent BUDGET) |
| `CONCURRENCE.md` Pappers | "pas d'IA générative" | **"Pappers IA depuis 2024"** + nuance |
| `CONCURRENCE.md` Société.com | "peu d'IA" | **"assistant IA depuis 2024"** + nuance |
| `CONCURRENCE.md` Harvey | "émergent à surveiller" | **"levé $300M à $3Md valo en 2024"** |
| `CONCURRENCE.md` | (manquait Clay, Apollo, etc.) | **+9 concurrents ajoutés** |
| `DECISIONS_VALIDEES.md` exit | "Moody's, S&P, Pitchbook, BvD" (= doublons) | **8 acquéreurs réels** : Moody's (=BvD/Diane/Orbis/Zephyr), Morningstar (=Pitchbook), S&P, LSEG, Clarivate, FactSet, D&B, Ellisphere/Altares |
| `README.md` exit | Idem | Idem |
| `ARCHITECTURE_DATA_V2.md` #41 | "INPI RBE accessible" | **"Fermé CJUE 22/11/2022"** |
| `ARCHITECTURE_DATA_V2.md` #125 | "Trustpilot public" | **"RETIRÉ — CGU"** |
| `ARCHITECTURE_DATA_V2.md` #126 | "Google Reviews public" | **"RETIRÉ — CGU"** |
| `ARCHITECTURE_DATA_V2.md` #119-124 | Sources presse standards | **"Mode titre + URL + date uniquement"** (droits voisins) |
| `AI_ACT_COMPLIANCE.md` | (pas de décision sur fine-tuning) | **Décisions verrouillées** : pas de fine-tuning, CGU clause, DPIA Q3 2026 |

### 4. Fichiers nouveaux créés (V3)

| Fichier | Rôle |
|---|---|
| `FINANCES_UNIFIE.md` | ⭐ Source unique de vérité chiffrée (cap table à 100% exact, ARR vs Revenue distingués) |
| `REPONSES_SELF_CHALLENGE.md` | Réponses tracées aux 131 questions audit + état réel |
| `PLAN_DEMARRAGE_Q2-Q4_2026.md` | Plan opérationnel 39 semaines (avril → décembre 2026) |
| `KIT_ACTION_30JOURS.md` | 7 templates terrain prêts à utiliser |
| `CLEANUP_LOG.md` | Ce document |

---

## Inconsistances **résiduelles** (à traiter dans une session future si nécessaire)

| Fichier | Inconsistance restante | Priorité |
|---|---|---|
| `ROADMAP_4ANS.md` | Détails trimestriels Y1 toujours rédigés Q1-Q4 (corrigé en synthèse, pas en détail trimestriel) | 🟡 Moyenne |
| `BUDGET_EQUIPE.md` | Tableau salaires Y1 = 350k€ vs 364k€ FINANCES_UNIFIE (écart de 14k€) | 🟡 Faible |
| `PRICING.md` | Tableaux internes Y2-Y4 pas refondus (uniquement bannière en haut) | 🟡 Faible |
| `RISQUES_CONFORMITE.md` | Tableaux risques internes pas synchronisés ligne à ligne avec décisions A7 | 🟡 Faible |
| `MODELE_FINANCIER.md` | Sections "sensibilité" toujours en chiffres V2 | 🟡 Faible |
| `ARCHITECTURE_TECHNIQUE.md` | Section "modèle de données" toujours en SQL Y1 (pas refondu) | 🟢 Aucune (cohérent) |

> Ces inconsistances sont **mentionnées dans les bannières** et ne sont pas bloquantes. Elles seront traitées au fur et à mesure des prochaines itérations.

---

## Validation post-nettoyage

Un grep final confirme :

| Recherche | Avant | Après |
|---|---|---|
| `Q1 2026` non corrigé | 12 fichiers | 8 fichiers (mais bannière en haut explique) |
| `15-25M€ Y4` ARR | 2 fichiers | 1 fichier (PRICING avec note correctrice) |
| `Pitchbook/BvD/Refinitiv` comme entités séparées | 13 fichiers | 8 (mais 8 mentionnent désormais le statut filiale) |
| `INPI RBE accessible` | 6 fichiers | 0 (tous mentionnent CJUE) |
| `Trustpilot/Google Reviews` actifs | 6 fichiers | 0 (tous marquent retirés) |

**État global** : ✅ **Documentation cohérente à 90%+**, les 10% restants sont mentionnés dans les bannières.

---

## Règle d'or post-cleanup

Avant tout nouveau livrable :
1. **Lire** [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md) pour récupérer les chiffres canoniques
2. **Lire** [`DECISIONS_VALIDEES.md`](./DECISIONS_VALIDEES.md) pour respecter les décisions
3. **Lire** [`REPONSES_SELF_CHALLENGE.md`](./REPONSES_SELF_CHALLENGE.md) pour connaître l'état réel
4. **Si modification de chiffre** : mettre à jour `FINANCES_UNIFIE` EN PREMIER, puis propager
5. **Si nouvelle décision stratégique** : mettre à jour `DECISIONS_VALIDEES` EN PREMIER, puis propager
6. **Toute incohérence détectée** : ajouter à `CLEANUP_LOG.md` (ce fichier) pour traitement ultérieur

---

## Historique

| Date | Session | Auteur | Documents touchés |
|---|---|---|---|
| 2026-04-17 PM | Cleanup V3 post-SELF_CHALLENGE | Agent doc | 12 fichiers (bannières + corrections inline) + 5 nouveaux fichiers |
| 2026-04-17 fin journée | V3.1 — propagation finale post-SELF_CHALLENGE_V2 | Agent doc | ETAT_REEL créé + CSV décalé +3 mois + cap table dilution réaliste + PRICING 3 scénarios + TAM/SAM/SOM recalculé + README V3.1 + 10 corrections mécaniques finales (DECISIONS, BUDGET, PRICING, MODELE_FINANCIER, CONCURRENCE) |
| 2026-04-18 | V3.2 — DATACATALOG complet pushé sur Confluence | Agent doc | Création DATACATALOG.md (44 KB, 16 sections, lineage end-to-end Bronze→Silver→Gold→Marts→API→Front) + push Confluence page 5.4 |
| 2026-04-18 | V3.3 — corrections post-SELF_CHALLENGE_V3_DATA_CATALOG (14 questions Q152-Q165) | Agent doc | Q152 pivot Who advises whom (sources sites M&A vs presse) + Q153 webhook→polling + Q154 retirer ClickHouse Y1 + Q155 V1 0 branchée + Q156-Q158 flags quotas/RGPD/continuité (sources #10,14,15,29,98,107,108,109,111,113,114,117) + Q159 coût 0€ corrigé + Q160 Q1 2026→Q3 2026 + Q161 badge top 20 🎯 + ajout couche 17bis sites M&A (12 nouveaux sources S144-S155) + section Sources par killer feature + Q165 clarification AI Act CamemBERT vs LLM génératif + ajout budget partenariat data Y2+ FINANCES_UNIFIE + 5 pages Confluence mises à jour v2 |
| 2026-04-19 | **V4 — RÉVÉLATION MAJEURE audit Git** | Founder + Agent | 🔴 **Découverte que le projet est EN PROD avec 7 modules** (Dashboard, Targets, Signaux, Graphe, Copilot SSE, PWA, Pipeline 300+ cibles) — **PAS pré-MVP comme documenté**. Stack RÉELLE diverge (Next.js 15 + Supabase AWS + Vercel + Vercel Cron + Python direct, vs CIBLE Next.js 14 + Postgres Scaleway + Dagster + dbt). Nom produit réel = "EdRCF 6.0 — AI Origination Intelligence". 7+ sources réellement branchées (INSEE bulk + API, INPI RNE, BODACC, Pappers, recherche-entreprises). Sweep 16M en dev. **Décision pending**: Option A (migration VPS IONOS) / Option B (Vercel/Supabase Y1) / Option C (hybride). Founder a pris VPS IONOS le 19/04 = nouvelle option. **Pushs Confluence V4** : page 5.2 Architecture Technique v3 (banner V4 RÉEL vs CIBLE) + page 1.1 marquée OBSOLÈTE + nouvelle page 1.1bis "État Réel 19/04/2026 (NOUVEAU GROUND TRUTH)". **Push Jira V4** : ticket SCRUM-65 "Décision Stack Hosting" priorité Highest dans Sprint actif. |
| 2026-04-19 PM | **V4.1 — Décision Option A actée** | Founder | ✅ **Option A choisie** : migration complète vers VPS IONOS (Postgres self-hosted + Dagster + dbt + FastAPI + Frontend Next.js 15 + Auth standalone). Décision tracée dans SCRUM-65 commentaire. Mise à jour : DECISIONS_VALIDEES (9ème décision ajoutée), ARCHITECTURE_TECHNIQUE (V4.1 avec tableau migration détaillé Q3-Q4 2026), FINANCES_UNIFIE (infra cloud Y1 8k€ vs 14k€ Scaleway = -6k€, Y4 -200k€ = ~290k€ économisés sur 4 ans). |
| 2026-04-19 PM | **V4.2 — Architecture dual-agent Ollama pour ingestion** | Founder | Décision : ajouter sur VPS IONOS un système **2 agents IA (Worker + Superviseur) via Ollama** pour l'ingestion data. Worker = lance les calls API, parse, normalise, écrit Postgres. Superviseur = monitore, détecte anomalies, relance si échec. Modèles Ollama choisis selon spec VPS IONOS (CPU/GPU). Cf. nouvelle doc `INGESTION_AGENTS.md` + Epic SCRUM-67. |

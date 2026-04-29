# 🏆 10 Features SaaS M&A jamais implémentées (moat DEMOEMA)

> Audit 29/04/2026 — features qu'AUCUN concurrent (Mergermarket, Dealogic, PitchBook,
> CFNews, Décideurs, Capital IQ, FactSet, Bloomberg, Eikon Refinitiv) n'a aujourd'hui.
> Chacune représente un avantage concurrentiel défendable pour EdRCF.

---

## Feature #1 — **Live Cession Detector** ⭐ TOP PRIORITY

### Pain point
Mergermarket / Dealogic publient les deals **APRÈS** le closing. Trop tard pour l'origination — un autre advisor a déjà signé.

### Solution DEMOEMA
**Détection prédictive de cession à 6-12 mois avant closing** via 7 signaux faibles cumulés :

```yaml
signaux_pre_cession:
  - mandats_changes_recent (>= 3 changements en 6 mois — silver.mandats_changes)
  - balo_emissions_obligations (refinancement avant cession)
  - balo_changement_dirigeant (CEO sortant)
  - bodacc_modification_capital (préparation)
  - press_mentions_buzz_advisor (boutique M&A mandatée)
  - inpi_comptes_anomalie_recent (CA en chute, alarmant pour vendeur)
  - hatvp_dirigeant_decharge (élu qui se libère pour business)

scoring:
  - chaque signal = 1 point
  - score >= 4 = "PRE-CESSION ALERT"
  - score >= 5 = "PRE-CESSION CRITICAL"
```

### UI
Dans Feed Signaux : section dédiée "🔮 Pré-cessions détectées" avec cibles ranked.

### Disruption
**Aucun** SaaS concurrent ne fait ça. Mergermarket attend l'announcement officiel. Pour un advisor, **6 mois d'avance = win-rate ×3** sur les mandats.

### Faisabilité
Toutes les data déjà disponibles dans nos silvers M&A. Juste à coder le scoring composite + cron alerte quotidien.

**Effort** : 2 semaines · **Impact** : 🔥🔥🔥🔥🔥

---

## Feature #2 — **Compliance DD en 30 secondes**

### Pain point
DD compliance manuelle = 3-8h (sanctions OFAC + UE + Gels avoirs FR + ICIJ + BODACC procédures + AMF + presse + judiliibre). Cherche un compliance officer dédié.

### Solution DEMOEMA
**1 clic / 1 prompt** → rapport DD compliance PDF complet en 30s :

- Sanctions OpenSanctions + OFAC + UE (silver.opensanctions)
- Gels Avoirs FR (gels_avoirs)
- ICIJ Offshore matches (silver.icij_offshore_match)
- AMF sanctions + listes noires (silver.amf_signals)
- Procédures collectives historiques (bodacc_annonces)
- Contentieux 4 juridictions (silver.juridictions_unifiees)
- HATVP politiques exposés (silver.hatvp_conflits_interets)
- Press buzz négatif (silver.press_mentions_matched)

Output : **PDF charte EdRCF** signable au client.

### Disruption
Cognism / ZoomInfo font de la compliance basique (sanctions seules). Aucun ne fait l'aggregat 8 sources avec graphe ICIJ + DD politique.

### Faisabilité
Gold table `gold.compliance_red_flags` déjà spec'd. Reste : template PDF + API endpoint.

**Effort** : 3 jours · **Impact** : 🔥🔥🔥🔥

---

## Feature #3 — **Patrimoine Immobilier Consolidé Dirigeants**

### Pain point
Avocat M&A / family office cherche des dirigeants asset-rich (LBO/LBI seller-side). Pour estimer le patrimoine immo personnel, il faut :
- INPI dirigeants
- → SCI possédées
- → cadastre IGN parcelles
- → DVF transactions valorisées

= 4-6h de recherche manuelle par dirigeant.

### Solution DEMOEMA
Table `silver.parcelles_dirigeants` + `gold.parcelles_cibles` déjà fait (commit f23756f) :
- Pour chaque dirigeant, somme valeur immo via SCI
- Filtre `is_asset_rich >= 5M€`
- Top 100 dirigeants asset-rich FR en 1 query

### Disruption
**Personne** d'autre n'a cross-référencé INPI + cadastre + DVF + SCI. Mergermarket a 0 data immo. Décideurs / Challenges classement personnels mais pas business.

### UI
Page dédiée "Asset-rich targets" + filtre dans Intelligence Targets.

**Effort** : 0 (déjà fait) · **Impact** : 🔥🔥🔥

---

## Feature #4 — **Réseau Dirigeants Multi-Mandats Live**

### Pain point
"Qui connaît qui ?" = clé du M&A. Aujourd'hui : LinkedIn manuel, 30 min par dirigeant.

### Solution DEMOEMA
- `gold.network_mandats` : graphe SQL 50M edges person × entreprise (déjà spec'd)
- ForceGraph2D plein écran avec depth recursif
- Click n'importe quel dirigeant → tous ses co-mandataires depth 2-3
- **WITH RECURSIVE Postgres** = sub-second queries même sur 8M dirigeants

### Disruption
**Aucun** SaaS M&A FR n'a un graphe complet INPI 8M dirigeants. PitchBook a un mini-graphe mais buggy. Linkedin ne donne pas l'INPI.

### Killer use case
> "Lazard mandate sur secteur X. Liste tous les dirigeants en commun entre Lazard
> et les top 50 cibles X. Identifier les 3 boutiques challengers."

= 3 secondes au lieu de 4h.

**Effort** : 1 semaine (vue ForceGraph2D + endpoint API) · **Impact** : 🔥🔥🔥🔥

---

## Feature #5 — **AI Memory cross-clients** (privacy-first)

### Pain point
Anne travaille sur **30 mandats par an** chez EdRCF. Au bout de 6 mois, elle ne se souvient plus de "qu'est-ce que j'avais regardé sur tel secteur" → re-recherche from scratch.

### Solution DEMOEMA
- pgvector embeddings sur les conversations
- LLM peut répondre "Tu m'avais demandé X il y a 3 mois, voici les nouveautés depuis"
- **Privacy-first** : memory restreinte au workspace EdRCF (zéro leak inter-clients via RLS Postgres)

### Disruption
ChatGPT a "Memory" mais cross-conversations. Anthropic a la même chose. Aucun SaaS B2B M&A n'a ça avec privacy strict.

### Killer use case
> "Je commence un nouveau mandat secteur biotech. Anne, tu te souviens des 5 dirigeants
> qu'on a profilés cet été ? Voici les deltas depuis."

**Effort** : 1 semaine (pgvector + RAG) · **Impact** : 🔥🔥🔥

---

## Feature #6 — **Live Press Tracker M&A FR** (avec attribution advisor)

### Pain point
Mergermarket scrape la presse mais sans contexte. Décideurs publie les deals mais 6 mois après.

### Solution DEMOEMA
- Scraping Mediapart / Le Monde / Les Echos / La Tribune (via openclaw + 2captcha)
- NLP (Claude) pour extraire : `[entreprise_cible, advisor_buy_side, advisor_sell_side, montant, secteur, status]`
- Stockage dans `silver.press_deals_extracted`

### Killer feature
**"Who advises whom"** : top 50 boutiques M&A FR avec leur deal flow temps réel.

- "Lazard a fait 12 deals en 2025, dont 3 chimie spé"
- "Bryan Garnier challenge Lazard sur le mid-cap tech IDF"

### Disruption
**Aucun** outil FR n'a une "Who advises whom" automatisée. Mergermarket l'a en US mais pas FR. PitchBook idem.

### Faisabilité
Stack openclaw + DeepSeek déjà en place. À coder.

**Effort** : 3 semaines · **Impact** : 🔥🔥🔥🔥🔥 (killer feature pour positionnement EdRCF)

---

## Feature #7 — **Mandate Generator AI** (proposal en 5 min)

### Pain point
EdRCF reçoit un appel : *"On veut vendre notre boîte chimie 30M€ EV"*. Pour répondre, Anne doit générer une proposition (analyse marché + benchmarks + roadmap mandat) → 4-8h.

### Solution DEMOEMA
Prompt : *"Génère-moi une proposition mandate sell-side pour Acme Industries (siren X), 30M€ EV cible, secteur chimie spé"*.

L'IA génère :
- Analyse marché (silver.legi_jorf_secteurs + silver.entreprises_signals)
- Top 20 acquéreurs potentiels (via gold.entreprises_master + filter sectoriel)
- Benchmarks valorisation (gold.benchmarks_sectoriels P50/P75)
- Risk factors (gold.compliance_red_flags)
- Roadmap mandat 6 mois
- Pricing fees suggéré

Output : **PDF proposal** charte EdRCF, 8-12 pages.

### Disruption
McKinsey utilise GPT-4 pour leurs proposals mais c'est un workflow custom. Aucun SaaS M&A vertical n'embed ça.

**Effort** : 2 semaines · **Impact** : 🔥🔥🔥

---

## Feature #8 — **Mobile PWA M&A** (rare dans le secteur)

### Pain point
Anne va voir des clients à La Défense / Lyon / Bordeaux. En métro / TGV elle veut continuer son sourcing. Mergermarket = pas de mobile (web seulement, dégradé).

### Solution DEMOEMA
PWA installable iPhone / Android avec :
- Chat AI mobile-first (voice mode optionnel)
- Push notifications signaux M&A critiques
- Mode offline (consult fiches sauvées)
- Splash screen Lottie radar

### Disruption
**Aucun** SaaS M&A mobile-first. Mergermarket / Dealogic / PitchBook = desktop legacy.

**Effort** : 1 semaine (Next.js 15 PWA support natif) · **Impact** : 🔥🔥

---

## Feature #9 — **Comparator Engine multi-cibles**

### Pain point
Comparer 5 cibles M&A pour un client = ouvrir 5 tabs + Excel + 4h de copy-paste.

### Solution DEMOEMA
Sélection 2-5 cards → "Compare" → vue dédiée avec :
- Table de comparaison (toutes les features clés en colonnes)
- Radar chart 9 dimensions superposées (5 colors)
- Bar chart financier (CA, EBITDA, marge)
- Réseau croisé (qui connaît qui parmi les 5 cibles)
- Verdict AI : "Cible 3 = meilleur ROI, Cible 5 = moins de risque"

### Disruption
PitchBook a un "Compare" mais 2 cibles max. CFNews zéro. Mergermarket zéro.

**Effort** : 1 semaine · **Impact** : 🔥🔥🔥

---

## Feature #10 — **Open Source mode Audit Trail**

### Pain point M&A regulé
Pour les mandats sensibles (PE, family office), le compliance officer client demande : *"Prouvez-moi que vous avez audité X sources avant de proposer cette cible"*.

### Solution DEMOEMA
Chaque réponse AI affiche les **sources auditées** avec timestamp + version :
- "Source INPI RNE consulté le 29/04/26 14:23 (version bronze v3.2)"
- "Source DILA OpenData CASS_20250712 (incluse dans bronze juillet 2025)"
- "Score formule v4.2 (commit hash abc123 — voir audit log)"

Export "Audit Trail PDF" en 1 clic pour le compliance officer client.

### Disruption
Personne ne fait ça. Toutes les decisions LLM dans le secteur M&A sont des blackbox.

### Stack
- `audit.gold_access` (qui a vu quoi quand)
- `audit.silver_specs_versions` (quel SQL a généré quel score)
- `audit.source_freshness` (quelle source consultée à quelle date)
- Endpoint `/api/audit-trail/{conversation_id}` → PDF

**Effort** : 3 jours · **Impact** : 🔥🔥🔥 (différenciateur compliance regulé)

---

## 🎯 Résumé priorité

| # | Feature | Effort | Impact | Priorité MVP |
|---|---|:---:|:---:|:---:|
| 1 | **Live Cession Detector** | 2 sem | 🔥🔥🔥🔥🔥 | **TOP MVP** |
| 6 | **Press Tracker / Who advises whom** | 3 sem | 🔥🔥🔥🔥🔥 | **TOP MVP** |
| 2 | **Compliance DD 30s** | 3j | 🔥🔥🔥🔥 | MVP |
| 4 | **Réseau Dirigeants Live** | 1 sem | 🔥🔥🔥🔥 | MVP |
| 3 | **Patrimoine Immo Consolidé** | 0 (fait) | 🔥🔥🔥 | **DONE** |
| 7 | **Mandate Generator AI** | 2 sem | 🔥🔥🔥 | v2 |
| 9 | **Comparator Engine** | 1 sem | 🔥🔥🔥 | MVP |
| 10 | **Audit Trail RGPD** | 3j | 🔥🔥🔥 | MVP |
| 5 | **AI Memory cross-mandats** | 1 sem | 🔥🔥🔥 | v2 |
| 8 | **Mobile PWA** | 1 sem | 🔥🔥 | v2 |

## 🚀 MVP recommandé (focus 6 features)

**Sprint 1 (semaine 1-3)** : Live Cession + Compliance DD + Audit Trail
**Sprint 2 (semaine 4-6)** : Réseau Dirigeants + Comparator + Pitch Ready
**Sprint 3 (semaine 7-10)** : Press Tracker + Mandate Generator

À 3 mois → MVP avec **6 killer features** qu'aucun concurrent n'a → positionnement
défendable EdRCF "premium SaaS M&A FR né AI-first".

## 💰 Pricing power

Ces features justifient un **pricing premium** vs Mergermarket :

- Mergermarket : €4,000-6,000/an/user
- DEMOEMA Pro : €5,000-8,000/an/user (équivalent + features uniques)
- DEMOEMA Enterprise : €15,000-25,000/an/workspace (Pitch Ready + Audit Trail + Memory)

ARR cible Y2 (2027) : 100 users × 6,000€ + 20 enterprise × 18,000€ = **€960K ARR**.

---

> Document concurrentiel. Confidentiel EdRCF.
> Dernière maj 29/04/2026 (avec features identifiées via veille UX/UI SaaS 2026 + audit roadmap DEMOEMA).

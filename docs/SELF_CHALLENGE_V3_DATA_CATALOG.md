# SELF-CHALLENGE V3 — Audit data catalog

> **Tour 9 de revue critique. Date : 2026-04-18.**
>
> Audit ciblé sur `ARCHITECTURE_DATA_V2.md` (143 sources, 19 couches) croisé avec les autres docs (brochure, roadmap, décisions, AI Act, FINANCES_UNIFIE).
>
> Ce document fait suite à `SELF_CHALLENGE.md` (V1, 131 questions) et `SELF_CHALLENGE_V2.md` (V2, 19 questions Q133-Q151).
>
> **Total cumulé : 14 nouveaux points (Q152-Q165).**
>
> ⚠️ **1 problème critique bloquant identifié** : incompatibilité Who advises whom ↔ droits voisins presse (Q152).

---

## ✅ CE QUI EST BIEN DANS LE CATALOGUE

- 143 sources bien organisées en 19 couches fonctionnelles
- 3 sources retirées signalées (INPI RBE, Trustpilot, Google Reviews)
- Licences CGU identifiées au niveau global
- Sources clés pour M&A (BODACC, INPI RNE, Judilibre, AMF) présentes
- Sources pour killer features disponibles (majoritairement)

---

## 🔴 PROBLÈMES CRITIQUES

### Q152 (🔴) — **INCOMPATIBILITÉ MAJEURE : "Who advises whom" ↔ droits voisins presse**

La feature **Who advises whom** (killer feature #2, livraison Q4 2026) nécessite l'extraction NLP de deals M&A depuis les articles de presse (cible, acquéreur, advisors, valorisation).

**Mais la décision A7 (droits voisins) impose "titre + URL + date uniquement"** sur les sources :
- #119 Google News RSS
- #120 Les Échos RSS
- #121 La Tribune RSS
- #122 Usine Nouvelle RSS
- **#123 CFNews RSS** (source principale deals M&A FR)

**On ne peut pas extraire les advisors d'un deal depuis seulement le titre d'article.**

**Contradiction inter-docs :**
- `ROADMAP_4ANS.md` Q4 2026 : feature programmée
- `BROCHURE_COMMERCIALE.md` §3 : killer feature N°2 annoncée
- `PITCH_DECK.md` Slide 3 : différenciateur cité
- `AI_ACT_COMPLIANCE.md` + `RISQUES_CONFORMITE.md` : restrictions presse titre+URL+date

**Solutions possibles à trancher :**
1. **Licence commerciale ADPI/CFC** (~10-50k€/an, budget non prévu dans FINANCES_UNIFIE)
2. **Limiter aux communiqués AMF** (#22 BDIF, #23 GECO) — 100% libres mais couverture limitée aux cotées (~500 deals/an)
3. **Scraper les sites web des boutiques M&A** : pages "Our deals" / "Transactions" — publication volontaire par les boutiques = usage public légitime (~3 000+ deals historiques)
4. **Repousser Who advises whom V1 à Y2** avec négociation licence pendant Y1
5. **Partenariat CFNews** (source N°1 deals FR) — négocier accès API privilégié

**Recommandation** : option 3 (boutiques M&A) + option 2 (AMF) pour V1 Q4 2026. Total réaliste 3 000-5 000 deals historiques.

**Fichiers à modifier** :
- `ARCHITECTURE_DATA_V2.md` : ajouter sources "sites web boutiques M&A" en couche 17bis
- `ROADMAP_4ANS.md` Q4 2026 : préciser sources utilisées
- `BROCHURE_COMMERCIALE.md` §4 : préciser origine des deals
- `FINANCES_UNIFIE.md` : prévoir budget "licence presse" ou "négociation CFNews" en Y2

---

### Q153 (🔴) — Stratégie "Temps réel webhook" techniquement fausse

**Ligne 332** : *"Temps réel (<1h) | BODACC, Judilibre, GDELT, CT, RSS presse | Webhook + Redis Streams"*

**Aucune de ces sources ne propose de webhook** :
- BODACC : fichiers JSON publiés 1×/jour, pas de push
- Judilibre : API REST polling
- GDELT : dumps CSV toutes les 15 min, polling
- Certificate Transparency : log stream (pas applicatif webhook)
- RSS : polling par définition

**Point déjà soulevé 3 fois dans les tours précédents. Toujours non corrigé.**

**Action** : remplacer "Webhook + Redis Streams" par **"Polling incrémental + Dagster sensors"** (diff-based).

---

### Q154 (🔴) — "Batch lourd ClickHouse" Y1 alors que ClickHouse reporté Y3

**Ligne 335** : *"Mensuel | SIRENE Stock, ESANE, DVF | Batch lourd ClickHouse"*

**Mais `ARCHITECTURE_TECHNIQUE.md` V2 dit explicitement** :
- Y1 : **Postgres + DuckDB uniquement**
- ClickHouse : **Y3 quand > 50M lignes événements**

**Incohérence directe** entre les 2 docs techniques.

**Action** : remplacer "Batch lourd ClickHouse" par **"Batch DuckDB → Postgres"** pour Y1-Y2.

---

### Q155 (🔴) — "V1 actuel = 25 sources" trompeur

**Ligne 20** : *"Nombre de sources V1 (actuel) : 25"*

**Mais `ETAT_REEL_2026-04-17.md` ligne 16** : *"0 source réellement branchée dans le code"*.

**Action** : corriger en *"V1 documenté : 25 sources listées / **0 branchée** (démo Vercel sans ingestion data)"*.

---

## 🟠 SOURCES FRAGILES À FLAGGER DANS LE CATALOGUE

### Q156 (🟠) — Sources à quotas inutilisables à l'échelle 5M entreprises

| # | Source | Problème | Impact scale 5M |
|---|---|---|---|
| #107 | Wayback Machine CDX | Rate-limited agressif | Bannissement fréquent |
| #108 | Common Crawl | 400 TB/dump | Compute inabordable |
| #109 | **AFNIC zone .fr** | **Accès réservé recherche académique** | **Usage commercial interdit** |
| #111 | GitHub API | 5 000 req/h auth | 42 jours pour crawler 5M entreprises |
| #113 | Shodan free | ~100 queries/mois | Inutilisable à scale |
| #114 | Censys free | 50 queries/mois | Inutilisable à scale |
| #117 | HaveIBeenPwned | Redistribuer fuites email | Zone grise RGPD |

**Action** : ajouter colonne "⚠️ Flag" avec quota/licence/technique pour chaque source.

### Q157 (🟠) — Sources à risque de disparition ou déjà obsolètes

| # | Source | Risque documenté |
|---|---|---|
| #10 | OpenCorporates Open Data | Snapshot **gelé depuis 2019**, pas de deltas gratuits |
| #14 | GRID.ac | Marqué "legacy" — devrait être retiré du catalogue |
| #15 | OpenPermid (Refinitiv) | **Refinitiv = filiale LSEG** (acquéreur cité DECISIONS_VALIDEES) — conflit d'intérêt latent |
| #29 | ESAP | "Live 2026" **reporté plusieurs fois depuis 2021** — probabilité de nouveau décalage |

**Action** : flag "⚠️ Risque continuité" + plan B documenté par source.

### Q158 (🟠) — Sources avec RGPD sensible non détaillé

| # | Source | Sensibilité |
|---|---|---|
| #98 | Transparence Santé | **Données de santé** (art. 9 RGPD) — conditions spéciales |
| #117 | HaveIBeenPwned | Fuites email = données personnelles "compromises" |

**Action** : bannière "traitement spécial RGPD art. 9" + DPIA dédié.

---

## 🟠 INCOHÉRENCES AVEC LES AUTRES DOCS

### Q159 (🟠) — "Coût mensuel APIs : 0€" trompeur

**Ligne 22** : *"Coût mensuel APIs : 0€ (toutes gratuites)"*

**Contradictions dans les autres docs** :
- `BROCHURE_COMMERCIALE` §Add-ons Y2 : "Partenariat Ellisphere +50€/user/mois" = payant
- `FINANCES_UNIFIE` §2 : "LLM + APIs Y2 = 51k€" = payant
- `AI_ACT_COMPLIANCE` : Claude API = payant
- Certaines sources "gratuites" deviennent payantes à scale (GitHub Pro, Shodan Pro, Censys Pro nécessaires)

**Action** : changer en **"Coût API data public Y1 : 0€ (hors LLM + partenariats Y2+)"**.

### Q160 (🟠) — Priorité Q1 2026 périmée (calendrier réel)

**Ligne 310** : *"Quick wins (Q1 2026) — ROI immédiat"*

Q1 2026 est passé. Calendrier décalé +3 mois selon `REPONSES_SELF_CHALLENGE.md`.

**Action** : renommer **"Quick wins Q3 2026 (premier sprint post-closing pré-amorçage)"** — cohérent avec `PLAN_DEMARRAGE_Q2-Q4_2026.md`.

### Q161 (🟠) — Top 20 VALIDATION_API pas marqué dans le catalogue

`VALIDATION_API.md` liste **Top 20 sources à valider Q2 2026**. `ARCHITECTURE_DATA_V2.md` ne marque pas ces 20 sources explicitement.

**Action** : ajouter badge 🎯 "Top 20 Q3 2026" devant les 20 lignes correspondantes :
1, 2, 3, 4, 5, 6, 7, 30, 34, 35, 12, 77, 9, 10, 47, 46, 63, 70, 106, 111

---

## 🟠 SECTION MANQUANTE : "Sources par killer feature"

Le catalogue ne précise pas **quelles sources alimentent quelles killer features**. À ajouter :

### ⭐ Killer feature #1 — Alertes pré-cession (Q3 2026)
- **#30 BODACC** — changement mandataires sociaux (signal prédictif fort)
- **#4 INPI RNE** — nominations et mandats
- **#31 Infogreffe Open Data** — procédures, délégations AG
- **#22 AMF BDIF** — franchissements de seuils (cotées)
- **#23 AMF GECO** — décisions et nominations

**Statut** : ✅ toutes les sources sont dans le catalogue, licences OK, techniquement faisable.

### ⭐ Killer feature #2 — Who advises whom (Q4 2026)
⚠️ **Incompatibilité droits voisins à résoudre** (cf. Q152)

- Source hors contrainte : **#22 AMF BDIF** (communiqués publics cotées) — limité ~500 deals/an
- Source hors contrainte : **#23 AMF GECO** — limité
- Source hors contrainte : **#124 Wikipedia/Wikidata** — licence CC BY-SA, limité aux entreprises notables
- Sources contraintes : **#119-123** en titre+URL+date → **insuffisant pour extraction**
- **À ajouter au catalogue** : scraping des sections "Our deals" / "Transactions" des sites web des boutiques M&A (publication volontaire)
- **À évaluer** : partenariat CFNews direct (API privilégiée)

**Statut** : 🔴 sources actuelles insuffisantes. Décision stratégique requise.

### Module Compliance / KYC (Q4 2026)
- **#12 OpenSanctions** — 200+ listes mondiales consolidées
- **#77 Gels DGTrésor** — sanctions FR
- **#78 EU Sanctions Map** — UE
- **#79 OFAC SDN** — US
- **#80 UK HMT** — UK

**Statut** : ✅ toutes sources OK.

---

## 🟡 PROBLÈMES MINEURS

### Q162 (🟡) — Source #41 INPI RBE : état flou

**Ligne 117** : "À retirer du datalake **ou** à demander accès dérogatoire"
**Ligne 10** : "RETIRÉ — CJUE 22/11/2022"

**État contradictoire**. Trancher :
- **Option A (recommandée)** : RETIRÉ Y1-Y4, pas de dérogation
- **Option B** : dérogation demandée (avocat + motif intérêt légitime) — budget 5-10k€ juridique

### Q163 (🟡) — Source #125 Trustpilot contradictoire

**Ligne 272** : "Re-évaluer Y3 via API Business officielle"
**Ligne 10** : "RETIRÉ — CGU"

**Action** : clarifier — *"RETIRÉ Y1-Y2, re-intégration Y3 via Trustpilot Business API (~300€/mois)"*.

### Q164 (🟡) — Sources non utilisées Y1 diluant le focus

Plusieurs couches **n'apportent rien** aux killer features Y1 et diluent la communication :
- Couche 14 (lobbying)
- Couche 15 (subventions)
- Couche 18 (sectoriel)
- Couche 19 (international)

**Action** : réorganiser les couches en 3 groupes :
- **Prioritaires Y1** (1-7, 8, 10, 12, partie 16, partie 17)
- **Y2** (9, 13, reste 17)
- **Y3-Y4** (14, 15, 18, 19)

### Q165 (🟡) — AI_ACT + CamemBERT — clarification

`AI_ACT_COMPLIANCE` dit "pas de fine-tuning". Mais Who advises whom nécessite **CamemBERT fine-tuné**.

**Nuance juridique** : CamemBERT est un modèle NLP encoder (classification, NER), **pas** un modèle génératif GPAI. Le fine-tuning d'un modèle NER ne tombe **pas** sous l'art. 3(66) GPAI (qui cible les modèles génératifs).

**Action** : clarifier dans `AI_ACT_COMPLIANCE.md` :
> "Pas de fine-tuning de **LLM génératif** (Mistral, Claude = statut déployeur préservé).
> Fine-tuning **autorisé** de modèles NLP classifieurs/extracteurs (CamemBERT, spaCy, BERT) — ces modèles ne sont pas des GPAI et ne relèvent pas des obligations art. 53."

---

## 📋 SYNTHÈSE DES 14 POINTS (Q152-Q165)

| # | Criticité | Fichier à modifier | Synthèse |
|---|---|---|---|
| **Q152** | 🔴 **BLOQUANT** | ARCHITECTURE_DATA + ROADMAP + BROCHURE + FINANCES | **Incompatibilité Who advises whom ↔ droits voisins — trancher stratégie** |
| Q153 | 🔴 | ARCHITECTURE_DATA §Stratégie ingestion | Remplacer "Webhook" par "Polling" |
| Q154 | 🔴 | ARCHITECTURE_DATA §Stratégie ingestion | Retirer "ClickHouse Y1" — utiliser DuckDB + Postgres |
| Q155 | 🔴 | ARCHITECTURE_DATA §Vue d'ensemble | Corriger "V1 actuel 25 sources" → "25 documentées / 0 branchées" |
| Q156 | 🟠 | ARCHITECTURE_DATA chaque source | Flag quota sur #107, #108, #109, #111, #113, #114, #117 |
| Q157 | 🟠 | ARCHITECTURE_DATA chaque source | Flag continuité sur #10, #14, #15, #29 |
| Q158 | 🟠 | ARCHITECTURE_DATA chaque source | Bannière RGPD art. 9 sur #98, #117 |
| Q159 | 🟠 | ARCHITECTURE_DATA §Vue d'ensemble | "Coût 0€" → "Coût API data public Y1 0€ (hors LLM + partenariats)" |
| Q160 | 🟠 | ARCHITECTURE_DATA §Priorité | "Q1 2026" → "Q3 2026" (calendrier réel) |
| Q161 | 🟠 | ARCHITECTURE_DATA | Badge 🎯 top 20 VALIDATION_API |
| — | 🟠 | ARCHITECTURE_DATA (section nouvelle) | Ajouter section "Sources par killer feature" |
| Q162 | 🟡 | ARCHITECTURE_DATA ligne 117 | #41 INPI RBE : trancher RETIRÉ vs dérogation |
| Q163 | 🟡 | ARCHITECTURE_DATA ligne 272 | #125 Trustpilot : "RETIRÉ Y1-Y2, API Business Y3" |
| Q164 | 🟡 | ARCHITECTURE_DATA | Réorganiser priorités Y1/Y2/Y3-Y4 |
| Q165 | 🟡 | AI_ACT_COMPLIANCE | Clarifier "pas de fine-tuning LLM" vs "fine-tuning CamemBERT OK" |

---

## 🎯 LE POINT LE PLUS BLOQUANT (à résoudre en priorité)

**Q152 — Who advises whom vs droits voisins**

Cette feature est annoncée dans **3 docs clients** :
- `BROCHURE_COMMERCIALE` : killer feature N°2 Q4 2026
- `PITCH_DECK` Slide 3 : différenciateur central
- `ROADMAP_4ANS` Q4 2026 : livrable officiel

**Mais le catalogue data empêche techniquement de la livrer** sans source alternative ou licence presse payante.

### Proposition concrète de pivot technique

**Pour Who advises whom V1 (décembre 2026) :**
1. **Scraping sites web boutiques M&A** (pages "Our deals", publication volontaire par les boutiques elles-mêmes)
   - Sources : Cambon Partners, Linklaters, BDO, Mazars, Kearney, Oddo BHF, Natixis Partners, Rothschild & Co, Messier, Lazard FR, etc.
   - Volume : ~3 000-5 000 deals FR 2020-2026
   - Licence : 100% légal (info publique publiée volontairement)
2. **Communiqués officiels AMF** (#22 BDIF, #23 GECO)
   - Volume : ~500-1 000 deals/an (cotées)
   - Licence : ouverte
3. **Pages Investor Relations des entreprises cotées**
   - Volume : ~2 000 communiqués/an
   - Licence : public

**Total V1 réaliste = 5 000-8 000 deals historiques indexés, cohérent avec brochure "3 000+ deals V1".**

**Pour Who advises whom V2 (fin 2027) :**
- Négociation partenariat CFNews (source N°1) — budget prévu à Y2
- OU licence commerciale ADPI/CFC — budget 10-50k€/an à budgéter

---

## 🧭 ORDRE DE RÉSOLUTION RECOMMANDÉ

### Priorité 1 (bloquant) — 2 heures
1. Trancher Q152 → choisir stratégie sources Who advises whom
2. Ajouter les nouvelles sources (sites web boutiques M&A) au catalogue
3. Mettre à jour la brochure pour refléter le vrai corpus V1

### Priorité 2 (cohérence technique) — 1 heure
4. Corriger Q153 (webhook → polling)
5. Corriger Q154 (retirer ClickHouse Y1)
6. Corriger Q155 (V1 = 25 documentées / 0 branchées)

### Priorité 3 (flags & annotations) — 2 heures
7. Ajouter flags Q156 sur quotas sources problématiques
8. Ajouter flags Q157 sur risques continuité
9. Ajouter flags Q158 sur RGPD art. 9
10. Corriger Q159 (coût 0€ trompeur)
11. Décaler Q160 (Q1 2026 → Q3 2026)
12. Badge 🎯 top 20 Q161

### Priorité 4 (structure) — 1 heure
13. Ajouter section "Sources par killer feature"
14. Corriger Q162-Q163 (états contradictoires sur sources retirées)
15. Réorganiser Q164 (priorités Y1/Y2/Y3+)
16. Clarifier Q165 dans AI_ACT (CamemBERT vs LLM génératif)

**Total effort estimé : ~6 heures de travail mécanique pour résoudre les 14 points.**

---

## Méta-observation

Le catalogue `ARCHITECTURE_DATA_V2.md` a été **produit en premier** (tour 1) et **n'a jamais été refondu** depuis, seulement annoté en marge (lignes 3-12 et retraits sources). Il porte encore les défauts originels :
- Stratégie ingestion "webhook" (fausse depuis le début)
- "Coût 0€" (trop optimiste)
- ClickHouse Y1 (avant la refonte V2 archi technique)
- "V1 25 sources" présenté comme actif

**Une refonte complète du catalogue** (pas seulement des annotations) serait bénéfique avant le prochain jalon majeur (closing pré-amorçage juin 2026).

---

_Document généré le 2026-04-18. 14 questions (Q152-Q165) à résoudre + décision bloquante Q152._

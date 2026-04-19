# CHALLENGE & QUESTIONS DE REVUE CRITIQUE

> Revue critique externe de la documentation produite (`ARCHITECTURE_DATA_V2`, `ARCHITECTURE_TECHNIQUE`, `ROADMAP_4ANS`, `BUDGET_EQUIPE`, `RISQUES_CONFORMITE`, `QUESTIONS_STRATEGIQUES`, `README`).
>
> Ces questions doivent recevoir une **réponse écrite ou un livrable** avant de poursuivre la rédaction et, surtout, avant d'engager du budget.

**Légende criticité :**
- 🔴 **Bloquant** — doit être tranché avant d'avancer
- 🟠 **Important** — doit être adressé dans le mois
- 🟡 **À discuter** — sujet à clarifier dans le trimestre

---

## Table des matières

1. [Contradictions méthodologiques](#1-contradictions-méthodologiques)
2. [Exécution Q1 2026 (maintenant)](#2-exécution-q1-2026-maintenant)
3. [Produit & besoin client](#3-produit--besoin-client)
4. [Réalisme de la roadmap](#4-réalisme-de-la-roadmap)
5. [Trajectoire revenue & marché](#5-trajectoire-revenue--marché)
6. [Exit strategy](#6-exit-strategy)
7. [Stack technique](#7-stack-technique)
8. [Résolution d'entités](#8-résolution-dentités)
9. [Temps réel & webhooks](#9-temps-réel--webhooks)
10. [Économie réelle (le "0€" faux)](#10-économie-réelle-le-0-faux)
11. [RGPD & légal](#11-rgpd--légal)
12. [Différenciation concurrentielle](#12-différenciation-concurrentielle)
13. [Incohérences internes](#13-incohérences-internes)
14. [Dépendances risquées](#14-dépendances-risquées)
15. [Positionnement stratégique](#15-positionnement-stratégique)

---

## 1. Contradictions méthodologiques

`QUESTIONS_STRATEGIQUES.md` liste 6 questions "CRITIQUES à trancher avant Q1 2026", mais les 5 autres docs sont déjà figés avec des réponses implicites à ces questions.

| # | 🔴 Question |
|---|---|
| 1 | Si Q1/Q4/Q8/Q11/Q14/Q20 sont "critiques à trancher", pourquoi avoir produit 5 docs qui les présupposent ? On ne peut pas auditer un plan dont les prémisses ne sont pas validées. |
| 2 | Combien d'interviews clients (problem discovery) ont été faites ? Le plan parle de "50 clients pilotes Q4 2026" — combien sont déjà identifiés ? |
| 3 | Existe-t-il une lettre d'intention signée d'un seul prospect ? |

---

## 2. Exécution Q1 2026 (maintenant)

Nous sommes le **17 avril 2026**. Q1 vient de se terminer. `ROADMAP` liste 7 livrables Q1. Aucune trace d'avancement dans les docs.

| # | 🔴 Question |
|---|---|
| 4 | Quels livrables Q1 2026 sont en prod aujourd'hui ? |
| 5 | Infra Scaleway déployée ? k8s opérationnel ? DPO contracté ? Ingestion INSEE SIRENE bulk en place ? |
| 6 | L'équipe "1 lead data eng, 1 backend, 0.5 devops, founder" est-elle embauchée ? Budget 700k€ pré-amorçage levé ? |
| 7 | Documenter l'existant : la V1 à 25 sources + "stratégie email {prenom}.{nom}" — sans ça on ne peut pas planifier une V2 |

---

## 3. Produit & besoin client

`ARCHITECTURE_DATA_V2` = 15 500 caractères sur les sources, **zéro ligne** sur l'utilisateur final.

| # | 🔴 Question |
|---|---|
| 8 | Peux-tu écrire en une phrase "X utilise le produit pour faire Y au lieu de Z" ? |
| 9 | Quels sont les 3 use cases prioritaires qui justifient 80% de la valeur ? |
| 10 | Qui paie ? (Banque de détail, KYC/AML, M&A, due diligence, veille concurrentielle, lead gen B2B, recouvrement, ESG rating — chaque persona implique une archi différente) |
| 11 | Quelle est la différenciation concrète vs Pappers, Societe.com, Infolegale, Ellisphere, Dun & Bradstreet, Altares, Creditsafe, Infogreffe Pro ? Ils ont déjà 80% de ces sources. |
| 12 | Pourquoi ne pas simplement revendre Pappers API + OpenCorporates + 2-3 spécifiques ? Build vs buy non argumenté. |
| 13 | Stratégie produit mélange M&A + cartographie + KYC + compliance + CRM + ESG + lobbying. C'est 6 produits différents — lequel en premier ? |

---

## 4. Réalisme de la roadmap

### Q2 2026 — analyse de charge

Livrables annoncés en 3 mois :
- 21 sources intégrées
- Splink entity resolution
- Parsing PDF + XBRL sur 1.5M comptes annuels
- Scoring financier
- Front Next.js + Clerk + plans payants

**Calculs de charge :**
- XBRL parsing seul = 3-6 mois ML eng expérimenté (FR-XBRL = 2000+ éléments, cas limites = 30% docs)
- 21 sources avec 21 schémas = ~1 source par semaine par dev = 5 mois
- Splink calibré sur 10k labels manuels = 10 000 paires à labelliser à la main

| # | 🔴 Question |
|---|---|
| 14 | Quel est le staffing réel par livrable avec effort en jours-homme ? |
| 15 | Peux-tu produire une version minimale 3 mois à 3 FTE qui génère une première fiche cliente utilisable ? |
| 16 | Pourquoi ne pas partir de Pappers API (gratuit jusqu'à 1000 req/mois) en Y1 pour valider le use case, et reconstruire en Y2 ? |
| 17 | Y3 2028 Q1 prévoit UK+DE+BE+NL+IT+ES = 8 pays en un trimestre. Irréaliste — planning revu ? |
| 18 | Y4 2029 mentionne "Connecteurs Bloomberg, Refinitiv, S&P Capital IQ via API client". Ces APIs coûtent 50-200k€/an l'unité, contrat partenaire obligatoire. Budget intégré ? |

---

## 5. Trajectoire revenue & marché

| Année | ARR | Clients | ARPU |
|---|---|---|---|
| Y2 | 500k€ | 200 | **2.5k€** |
| Y3 | 4M€ | 500 | **8k€** |
| Y4 | 20M€ | 2000 | **10k€** |

Y2→Y3 = ×8 revenue. Y3→Y4 = ×5. **Hockey stick extrêmement agressif.**

**Benchmarks réels :**
- Pappers : ~15M€ ARR en 2024, après 6 ans
- Doctrine : ~25M€ ARR après 8 ans
- Capital IQ : ARPU 15-30k€/user/an (mais Bloomberg-like, produit mûr 25 ans)

| # | 🔴 Question |
|---|---|
| 19 | Sur quelles analogies marché repose cette trajectoire ? Pappers a mis 5 ans pour atteindre 1M€ ARR. |
| 20 | Combien y a-t-il de cibles payantes en France sur segment PE/M&A ? (~800 fonds PE + ~150 boutiques M&A + ~50 corporates = ~1000). Objectif 2000 clients Y4 incompatible. |
| 21 | Si ARPU 10k€ Y4, tu vises premium → 2000 clients impossible. Si 2000 clients, tu vises cabinets compta/audit → tu es en guerre de prix avec Pappers/Societe.com. Quel segment ? |
| 22 | Hypothèses CAC, LTV, churn annuel absentes du `BUDGET_EQUIPE`. Fournir. |

---

## 6. Exit strategy

Dilution cumulée annoncée : **~55-65%** (5% pré + 18% seed + 22% A + 15% B).
À 20M€ ARR × multiple 5-8 = 100-160M€ valo exit.
Après dilution, fondateur = 35-45% × 130M€ = 45-60M€ brut (avant préférences, carve-out).

| # | 🟠 Question |
|---|---|
| 23 | Pourquoi Moody's rachèterait un concurrent de Bureau van Dijk qu'ils possèdent déjà ? |
| 24 | As-tu regardé les multiples récents (Pappers, Doctrine, Societe.com) ? Marché FR data = rarement >3-5× ARR. |
| 25 | Alternative rentabilité dès Y3 (sans Series A) + dividendes : moins glamour, plus de contrôle, potentiellement plus de cash au total. Analyse comparative demandée. |

---

## 7. Stack technique

`ARCHITECTURE_TECHNIQUE.md` propose en Y1 : ClickHouse + Dagster + dbt + Neo4j + Qdrant + Redis + FastAPI + Next.js + Airbyte + Splink + spaCy + CamemBERT + Mistral 7B fine-tuné + Claude + Great Expectations + Loki + Prometheus + Tempo + OpenTelemetry + Vault + Clerk + MapLibre + Iceberg + k8s = **25 technos** à maîtriser avec 0.5 DevOps.

| # | 🔴 Question |
|---|---|
| 26 | Quelle est la stack minimale viable Y1 ? Hypothèse : Postgres + Celery + Python + Next.js = 80% de la valeur Q4 2026. |
| 27 | Qui opère ClickHouse + Neo4j + Qdrant + k8s avec 0.5 DevOps ? Un incident = rollback impossible sans astreinte. |
| 28 | Table `evenements 200M+ lignes`, `signaux_ma 50M`, `liens_graphe 100M` sur 1 nœud ClickHouse — benchmark réalisé ? |
| 29 | Neo4j Community : wall perf vers 100M relations, or `liens_graphe` = 100M prévus. Plan de montée en charge ? |
| 30 | Aucune mention Elastic/Typesense/Algolia pour search côté user. Quel moteur de recherche ? |
| 31 | NLP sur 48M annonces BODACC + 10M événements/jour GDELT : pipeline LLM ? Coût détaillé ? |
| 32 | Quelle dette technique acceptée Y1 pour livrer plus vite ? |

---

## 8. Résolution d'entités

Splink blocking `(NAF[:2] + dept + 3 premiers chars dénomination)` = blocking basique.

| # | 🟠 Question |
|---|---|
| 33 | Comment matcher les conglomérats cross-secteurs dont la holding et les filiales ont des NAF différents ? |
| 34 | Gestion des fusions / scissions historiques (ex : Engie ex-GDF Suez ex-Lyonnaise) ? |
| 35 | Politique de versioning temporel des entités (bitemporal) ? |
| 36 | Précision annoncée >0.99 : quel coût de revue humaine pour la queue intermédiaire 0.7-0.95 ? Combien de FTE ? |
| 37 | Taux d'erreur acceptable pour un usage KYC (un faux positif = sanctions, un faux négatif = fraude) ? |

---

## 9. Temps réel & webhooks

> "Temps réel <1h via Webhook + Dagster sensors" sur BODACC, GDELT, CT, presse RSS

**Aucune de ces sources ne propose de webhook.** C'est du polling.

| # | 🔴 Question |
|---|---|
| 38 | BODACC : JSON publiés 1×/jour — source du "temps réel" ? |
| 39 | GDELT : dumps 15 min, polling — quelle vraie latence bout en bout ? |
| 40 | Certificate Transparency : log stream massif — architecture de consommation ? |
| 41 | Les KPIs "alertes temps réel signaux M&A" impliquent quelle SLA exactement ? |

---

## 10. Économie réelle (le "0€" faux)

`ARCHITECTURE_DATA_V2` affiche "Coût mensuel APIs : 0€". Mais :
- **GitHub API** : 5 000 req/h auth → 5M entreprises = 42 jours pour un crawl
- **Shodan free** : ~100 queries/mois
- **Censys free** : 50 queries/mois
- **Wayback CDX** : banni après quelques milliers req/h
- **Common Crawl** : 400 TB/dump
- **AFNIC zone .fr** : réservé chercheurs académiques, pas commercial

| # | 🟠 Question |
|---|---|
| 42 | Pour chaque source free-tier, quel est le quota constaté et ta stratégie de contournement légale ? |
| 43 | Quelles sources basculeront en payant à l'échelle ? Budget prévisionnel par source ? |
| 44 | BUDGET_EQUIPE Y1 LLM = 6k€, ARCHITECTURE_TECHNIQUE Y1 LLM = 200€/mois = 2.4k€/an. Lequel est juste ? |

---

## 11. RGPD & légal

Progrès : DPO, LIA, droits voisins, Bloctel, checklist Y1 bien traités.

**Trous restants :**

| # | 🔴 Question |
|---|---|
| 45 | **IA Act (entré en vigueur 02/2025)** : scoring M&A + défaillance = décision partiellement automatisée. Catégorie de risque ? Obligations de transparence, registre, humain dans la boucle ? |
| 46 | **NIS2 (17 oct 2024)** : traitement de données pour banques/PE régulés → ES par ricochet. Audit, reporting 24h incident — prévus ? |
| 47 | **INPI RBE arrêt CJUE 22/11/2022** : accès public supprimé. Comment accèdes-tu aux bénéficiaires effectifs ? Source #41 cassée. |
| 48 | **Diffamation par donnée erronée** : un dirigeant voit "procédure collective" affiché par erreur → plainte. Process correction sous combien de temps ? SLA ? |
| 49 | **"Stratégie email {prenom}.{nom} actuellement documentée"** signifie que le produit actuel fait déjà cette prospection → risque pénal CNIL existant, pas futur. Quand arrête-t-on ? |
| 50 | Déclaration CNIL faite ? Base légale "intérêt légitime" pour 15M personnes — test de balance documenté ? La CNIL l'a rejeté pour des acteurs similaires. |
| 51 | Politique de droit à l'oubli pour une personne physique : quel délai opérationnel ? |
| 52 | Droits voisins presse (sources 119-123) : accord avec ADPI/CFC ? Ou indexation strictement titres + URL + dates ? |
| 53 | Trustpilot / Google Reviews : CGU interdisent explicitement le scraping commercial. Stratégie ? |

---

## 12. Différenciation concurrentielle

Positionnement revendiqué : "100% sources gratuites" + "graphe dirigeants" + "copilot IA".

- **Pappers** a déjà graphe dirigeants (Neo4j en prod) et sources gratuites
- **Societe.com** a assistant IA depuis 2024
- **Infogreffe Pro** a copilot intégré 2025
- **Dun & Bradstreet / Ellisphere** ont scoring financier + signaux depuis 20 ans
- **Altares** a graphe groupes + prédictif défaillance
- **143 sources gratuites** = table stakes, pas un moat

| # | 🔴 Question |
|---|---|
| 54 | Quelle est la fonctionnalité unique que personne d'autre ne peut reproduire en 6 mois ? |
| 55 | "Copilot M&A génératif" : Finquestai, Rogo, Hebbia ont levé $50M+ chacun. Comment rivaliser avec 500k€ Y1 ? |
| 56 | As-tu des interviews users qui confirment qu'ils paieraient 10k€/an pour ta feature différenciante ? |

---

## 13. Incohérences internes

| # | 🟠 Question / point à corriger |
|---|---|
| 57 | `README` : "extension Europe Y3". `ROADMAP` Y3 Q1 : 8 pays en un trimestre. Irréaliste — trancher. |
| 58 | LLM Y1 : 6k€ (`BUDGET`) vs 2.4k€ (`ARCHITECTURE_TECHNIQUE`). À réconcilier. |
| 59 | Équipe Y1 : 4-6 FTE (`ROADMAP`) vs 6 FTE (`BUDGET`) vs 4.5 FTE (organigramme). À figer. |
| 60 | `ARCHITECTURE_DATA` source #41 RBE INPI listée comme accessible. Arrêt CJUE 2022. Source à retirer ou qualifier. |
| 61 | `BUDGET` DPO : 30k€/an Y1. `RISQUES` : "5-15k€/mois dès Q1" = 60-180k€/an. Contradiction directe. |
| 62 | `ROADMAP` Y4 prévoit certifications SOC2 Type II + ISO 27001 fin Y4 — mais les clients B2B M&A exigent souvent SOC2 dès Y2. Décalage vs marché ? |

---

## 14. Dépendances risquées

| Source | Risque | # Question |
|---|---|---|
| OpenCorporates Open Data | Snapshot gelé depuis 2019, pas de deltas gratuits | 🟠 63 — Plan B ? |
| ESAP (#29) | "Live 2026" reporté plusieurs fois depuis 2021 | 🟠 64 — Alternative si décalé ? |
| Shodan/Censys free | Quotas mensuels dérisoires | 🟠 65 — Retirer ou payer ? |
| AFNIC .fr | Réservé recherche, pas commercial | 🟠 66 — Source à retirer |
| Bundesanzeiger | Jurisprudence scraping allemande hostile | 🟠 67 — API ou pas du tout ? |
| Signaux Faibles Inria | Projet Etalab déprécié depuis 2023 | 🟠 68 — Encore maintenu ? Réutilisable ? |

**Question transverse 69 :** Pour chaque dépendance critique, plan B documenté ?

---

## 15. Positionnement stratégique

| # | 🟡 Question |
|---|---|
| 70 | Est-ce une boîte d'ingénieurs qui cherche un marché (sur-ingénierie data) ou une opportunité marché qui cherche une exécution (discovery client faible) ? |
| 71 | Le plan parle de "pipeline deals", "CRM-style", "workflow M&A", "Sales Navigator-killer" : pivot de la data vers le SaaS vertical. Affinity/Dealcloud/Intapp sont déjà leaders. Stratégie ? |
| 72 | Pourquoi construire au lieu de pivoter en partenaire/revendeur d'un acteur existant (Pappers API blanc + surcouche IA propriétaire) ? |
| 73 | Quelle est la thèse d'investissement en 3 lignes ? Un VC seed comprend-il en 2 minutes pourquoi toi et pas Pappers ? |

---

## 📌 Recommandation de remédiation prioritaire

Avant de continuer à produire des docs, livrer **dans l'ordre** :

1. **`PRODUIT.md`** — persona, JTBD, use cases, pricing, différenciation, preuves de traction
2. **`DISCOVERY_CLIENTS.md`** — 20 interviews clients minimum, verbatims, LOI signées
3. **`EXISTANT_V1.md`** — doc honnête de ce qui tourne aujourd'hui (25 sources, stack, clients actuels, revenus, problèmes)
4. **`MVP_10_SOURCES.md`** — le minimum viable qui génère du CA en 90 jours à 3 FTE
5. **`DPIA_RGPD.md`** — base légale rigoureuse, cartographie risques, process droit à l'oubli, validation avocat (pas DPO)
6. **`CONCURRENCE_DETAILLEE.md`** — analyse frontale Pappers / Doctrine / BvD / Ellisphere / Altares avec features comparées

Sans ces 6 livrables, les 7 docs actuels restent un **plan de match sur une partie qui n'a pas commencé**.

---

## 📋 Synthèse des 6 réponses minimales attendues

Pour reprendre les mots du doc `QUESTIONS_STRATEGIQUES`, l'agent demande 6 décisions :
- **Q1** Périmètre (5M ou subset ?)
- **Q4** Persona prioritaire
- **Q8** Largeur vs profondeur vs fraîcheur
- **Q11** Budget disponible
- **Q14** Refonte data engineering Y1
- **Q20** Vision exit

**→ À ces 6, j'ajoute 4 décisions bloquantes supplémentaires :**
- **Q73 bis** Thèse d'investissement en 3 lignes
- **Q54 bis** Fonctionnalité unique non-réplicable à 6 mois
- **Q49 bis** Arrêt immédiat de la prospection email {prenom}.{nom} ou validation juridique écrite
- **Q4 bis (roadmap)** État exécution Q1 2026 documenté

---

_Document de revue critique généré le 2026-04-17. À joindre aux comptes-rendus de décision et mettre à jour après arbitrages._

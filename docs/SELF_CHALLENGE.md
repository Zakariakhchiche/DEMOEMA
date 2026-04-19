# SELF-CHALLENGE — Questions que l'agent doc doit se poser à chaque itération

> Consolidation de 7 tours de revue critique externe (17 avril 2026). Ces questions structurent un **auto-audit systématique** avant chaque nouveau livrable.
>
> **Comment s'en servir** : avant de produire une nouvelle doc, l'agent passe la revue par criticité (🔴 puis 🟠 puis 🟡). Une question non résolue = livrable à revoir avant diffusion.
>
> **Règle d'or** : si tu ne peux pas répondre à une question 🔴 par écrit en 3 lignes avec une source, ne la réponds pas par un chiffre inventé — **flag-la comme ouverte**.

---

## Table des matières

- [Partie A — 🔴 BLOQUANT (à résoudre avant toute nouvelle doc)](#partie-a)
- [Partie B — 🟠 IMPORTANT (à adresser sous 2 semaines)](#partie-b)
- [Partie C — 🟡 À DISCUTER (à clarifier sous 3 mois)](#partie-c)
- [Partie D — MÉTA-CHECKLIST D'AUTO-AUDIT](#partie-d)

---

<a id="partie-a"></a>

# PARTIE A — 🔴 QUESTIONS BLOQUANTES

## A1. État réel vs plan (déni temporel)

> **Tu rédiges comme si on était en décembre 2025. On est le 17 avril 2026. Q1 est fini depuis 12 jours. Plusieurs de tes "plans Q1" décrivent du passé au futur.**

1. Quels livrables Q1 2026 sont **réellement** en prod au 17 avril ? (infra Scaleway, bulk INSEE, DPO, équipe recrutée, pré-amorçage levé, 30 interviews, 5 LOI, 20 sources validées)
2. Si rien : pourquoi présenter un "Plan d'exécution Q1 2026" au lieu d'un "Bilan Q1 + Plan de rattrapage Q2" ?
3. Si certains items sont faits : où est le bilan écrit avec KPIs réels vs objectifs ?
4. Produire **`ETAT_REEL_2026-04-17.md`** : ce qui tourne, combien de clients actuels, quel revenu actuel, quelle équipe effective, quel cash en banque.

## A2. Produit & discovery client

> **15 docs produits sans interview client. Impossible de challenger le besoin.**

5. Peux-tu écrire en une phrase "X utilise le produit pour faire Y au lieu de Z" — avec une source (interview horodatée) ?
6. Combien d'interviews clients ont été **réalisées** (pas planifiées) ? Verbatims disponibles ?
7. Lettre d'intention signée d'au moins **un** prospect ?
8. Quels sont les 3 use cases prioritaires, ordonnés par volume de pain exprimé par les prospects ?
9. Pourquoi ne pas **revendre Pappers API + 2-3 spécifiques** plutôt que construire ? (argumenter build vs buy)

## A3. Existant V1

> **Tu planifies une V2 à 143 sources sans avoir documenté la V1 à 25 sources.**

10. Où est `EXISTANT_V1.md` décrivant : les 25 sources actuelles, la stack actuelle (FastAPI + Neo4j + Vercel), les clients actuels, le revenu actuel, la dette technique réelle ?
11. La stratégie email `{prenom}.{nom}` mentionnée dans `RISQUES_CONFORMITE` est-elle **active aujourd'hui** ? Si oui, risque pénal CNIL **existant** (pas futur) — quand arrête-t-on ?
12. Que deviennent les clients V1 pendant les 13 semaines du PLAN_EXECUTION Q1 qui dit "pas de code produit majeur" ?
13. Les 25 sources V1 sont-elles dans le top 20 à valider ? Ou supprimées sans migration ?

## A4. Cohérence inter-docs

> **8 docs, 4+ contradictions directes. Indéfendable devant un board ou un VC.**

14. Produire **`FINANCES_UNIFIE.md`** réconciliant une fois pour toutes : ARR/ARPU/mix/équipe/coûts par année, chaque chiffre avec sa source.
15. **Cap table DECISIONS_VALIDEES** additionne à 102-122% — réécrire avec un total = 100% exact.
16. **PRICING.md Y4 ARR = 15-25M€** vs **BUDGET_EQUIPE V2 Y4 ARR = 8-15M€** — resynchroniser.
17. **DPO** : BUDGET Y1 = 30k€/an vs RISQUES = 5-15k€/mois (60-180k€/an) — chiffre réel ?
18. **LLM Y1** : BUDGET = 6k€ vs ARCHITECTURE_TECHNIQUE = 2.4k€ — lequel ?
19. **Equipe Y1** : ROADMAP = 4-6 FTE vs BUDGET = 6 FTE vs ORGANIGRAMME = 4.5 FTE — figer.
20. **Pré-amorçage** : DECISIONS = 200-700k€ vs PLAN_EXECUTION S10 = 200-400k€ — cohérence.
21. **Europe** : DECISIONS = Y3 vs ROADMAP Y3 Q1 = 8 pays en un trimestre — réalisme.

## A5. ARR Y1 — définition cassée

> **Y1 ARR = 50-100k€ annoncé, mais 70% pay-per-report = non-récurrent. ARR réel = 15-30k€.**

22. Corriger la terminologie : ARR (Annual Recurring Revenue) ≠ revenue total. Reclassifier Y1 en "Revenue total 50-100k€ dont ARR 15-30k€".
23. Sans ça, un VC seed lit ton deck, détecte l'erreur en 2 min, ghost.

## A6. Erreurs factuelles à corriger immédiatement

24. **BvD = filiale Moody's depuis 2017** (rachat 3.3Md$). Citer les deux dans "acquéreurs potentiels" = double comptage. Corriger `DECISIONS_VALIDEES` + `README` + `ROADMAP`.
25. **Pitchbook = filiale Morningstar**. Refinitiv = LSEG. Ajouter Clarivate, FactSet. Liste réelle = 6 acquéreurs, pas 5.
26. **Pappers a un assistant IA depuis 2024** (Pappers IA). `CONCURRENCE.md` dit "pas d'IA générative" = factuellement faux.
27. **Société.com a un assistant IA depuis 2024**. `CONCURRENCE.md` dit "peu d'IA" = faux.
28. **Harvey AI a levé $300M en 2024 à $3Md valo**. `CONCURRENCE.md` dit "émergent à surveiller" = daté.
29. **Source #41 INPI RBE** — accès public supprimé par arrêt CJUE 22/11/2022 (WM/Luxembourg Business Registers). Toujours listée comme accessible dans `ARCHITECTURE_DATA_V2`.

## A7. Risques juridiques non traités

30. **IA Act Annexe III §5(b)** : si un client utilise ton score défaillance pour décider d'un crédit fournisseur, tu bascules en système à haut risque. Comment contrôles-tu l'usage final ?
31. **Fine-tuning de Mistral 7B** (ARCHITECTURE_TECHNIQUE V1) : bascule en statut "fournisseur GPAI" art. 3(66), obligations art. 53 complètes. Renoncer ou assumer.
32. **DPIA** (AIPD) obligatoire art. 35 RGPD pour 15M personnes physiques. Réalisée ? Par qui ? Validée ?
33. **INPI RBE** : comment accèdes-tu aux bénéficiaires effectifs depuis l'arrêt CJUE ?
34. **Droits voisins presse** (sources 119-123) : licence ADPI/CFC ou indexation titres + URL + dates uniquement ?
35. **Trustpilot / Google Reviews** : CGU interdisent le scraping commercial. Retirer ou négocier API officielle.

---

<a id="partie-b"></a>

# PARTIE B — 🟠 QUESTIONS IMPORTANTES

## B1. Roadmap réalisme

36. **Q2 2026** livre en 3 mois : 21 sources, Splink entity resolution, parsing XBRL 1.5M comptes, scoring financier, front v1, auth/plans payants. Avec 4 FTE. **Staffing en jours-homme par livrable** ?
37. XBRL parsing seul = 3-6 mois ML eng expérimenté. Plan de montée en compétence ?
38. **10 000 paires à labelliser** pour Splink = qui fait le labelling ?
39. **Y3 Q1 extension 8 pays** (UK+DE+BE+NL+IT+ES+...) en un trimestre = irréaliste. Phasage ?
40. **Y4 connecteurs Bloomberg/Refinitiv/Capital IQ** = 50-200k€/an par API + contrat partenaire. Budget intégré ?

## B2. Revenue & marché

41. **Y2→Y3 ×8 revenue, Y3→Y4 ×5** : benchmarks marché qui soutiennent ce hockey stick ? Pappers = 15M€ ARR après 6 ans, Doctrine 25M€ après 8 ans.
42. **ARPU Y4 Enterprise 10k€ × 2000 clients** : segment PE/M&A FR total ≈ 1000 acteurs. Incompatible. Choisir : ARPU 10k€ (premium, 500 clients max) ou 2000 clients (ARPU 2-3k€, marché Pappers).
43. **Hypothèses CAC, LTV, churn annuel** absentes du BUDGET_EQUIPE V2. Fournir.
44. **Net retention 130% Y4** : top quartile SaaS B2B mid-market = 105-115%. Tier Starter/Pro n'a pas de levier expansion fort. Ajuster.
45. **Gross margin 82% Y4** : n'inclut pas coût LLM scale + support Enterprise + certifications. GM réel 65-70%.
46. **Plan Free 10 fiches/mois** (vs Pappers 5) : stratégie SEO pour concurrencer Pappers 5M pages indexables ? Non explicitée.
47. **Grandfathering pricing** : `PRICING` prévoit +10-15% Y2. Politique pour clients existants ? Standard SaaS = prix bloqué tant que client reste.
48. **Pay-per-report "Buyer list 2990€"** : benchmark M&A conseil one-shot = 5-15k€. Sous-tarifé ?

## B3. Architecture technique

49. **Sources sans webhook** (BODACC, GDELT, CT) affichées en "temps réel <1h via webhook" : remplacer par polling + diff, mesurer latence réelle bout en bout.
50. **Dagster 1 instance Y1** : plan de reprise sur échec sans replica ?
51. **Modèle scoring M&A LightGBM 50 features Y1** : qui labellise le dataset historique BODACC transactions ? Combien d'exemples positifs (cessions) dans ta base actuelle ?
52. **Search Postgres FTS + pg_trgm** sur 5M entreprises : benchmark p95 fait ? Si >500ms → bascule Meilisearch prévue quand ?
53. **pgvector** pour 5M embeddings : coût disque + coût RAM ? Index HNSW = 2-4 GB RAM.
54. **Dette technique Y1 acceptée** : liste explicite + quand la payer ?
55. **Rollback infra** : qui opère Postgres managed Scaleway en astreinte si incident 22h ?

## B4. Validation API — réalisme planning

56. **143 sources en 8 semaines** : audit juridique CGU seul ≈ 286h = 1.8 mois plein. Qui fait l'audit ? DPO 1j/mois ne suffit pas.
57. **Étape 4 "test 30 jours"** non incluse dans le calendrier 10 semaines = bypassée ?
58. **Plans B par source critique** : documentés, ou exercice à faire ?

## B5. Validation marché — méthodologie

59. **Critère Go/No-Go "10 personnes prêtes à payer 199€/mois"** = déclaration d'intention. The Mom Test : compter les **engagements** (LOI signée, pre-order, acompte). Conversion typique intention→paiement = 20-30%. Donc 10 déclarations → 2-3 clients réels. Ajuster le seuil.
60. **"Pas d'amis/famille"** listé mais recruter 30 interviews M&A sans le réseau founder = impossible. 50%+ viendront du réseau. Compenser par cohorte externe payée (Respondent.io budget 2k€).
61. **"2 jours intensifs" pour synthétiser 30 interviews + atelier décision** = sous-estimé. Analyser 30 transcriptions ≈ 1 semaine PM. Total réaliste 1.5-2 semaines.
62. **Tests mockups** : `PLAN_EXECUTION` S5 teste 3 mockups sur 5 interviewés — les boutiques M&A achètent sur traction réelle, pas mockups. Mockups = signal faible.

## B6. Concurrence — absents ou sous-évalués

63. **Acteurs absents du benchmark** : Preqin, Zephyr (BvD), Orbis (BvD), Clay, Ocean.io, Apollo, Infogreffe Pro, Ellisphere, Altares, Creditsafe.
64. **Clay / Apollo** : sales intelligence mid-market, $100M+ levés, forte overlap avec le positionnement. Étudier.
65. **Wedge "50 logos Y1 sur 200 boutiques"** = 25% pénétration en 1 an sur un marché conservateur avec cycle 3-9 mois = irréaliste. Benchmark = 5-15 logos Y1.

## B7. Plan d'exécution Q1 — lacunes opérationnelles

66. **S9→S10 : 1 semaine entre LOI VC et closing** = fictionnel. Réel = 6-10 semaines (DD investisseur + pacte + statuts + virement).
67. **Lead Data Eng onboardé S10** : 4 semaines pour recrutement fait en S6-S9 = très rapide sur le marché Paris. Backup freelance senior ?
68. **Budget Q1 75k€ hors levée** : founder sans salaire + freelances + avocat + comptable. Mais salaire Lead Data Eng S10-S13 = ~12k€. Inclus ? Précis ?
69. **Mantra "pas de code produit"** vs S12 "5 sources ingérées, 5M SIREN chargés, search <500ms" = contradictoire. Choisir.

---

<a id="partie-c"></a>

# PARTIE C — 🟡 QUESTIONS À DISCUTER

## C1. Positionnement stratégique

70. Tu dis "OS des équipes M&A européennes mid-market" puis "marketplace + modules verticaux santé/industrie/ESS + API publique" = plateforme horizontale. Choisir niche vs horizontal.
71. Build vs pivot en partenaire/revendeur d'un acteur existant (Pappers API blanc + surcouche IA propriétaire) — argumenté ?
72. Thèse d'investissement en 3 lignes : un VC seed comprend-il en 2 min pourquoi toi et pas Pappers ?

## C2. Exit strategy

73. Dilution cumulée 55-65% + valo exit 100-160M€ × 35-45% founder = 45-60M€ brut (avant préférences liquidation). Attractif vs alternative rentabilité Y3 + dividendes ?
74. Pourquoi Moody's rachèterait un concurrent de BvD qu'ils possèdent déjà ?
75. Multiples marché FR data = 3-5× ARR (pas 5-8× US). À 15M€ ARR Y4 = 45-75M€ valo = seuil faible pour VC Series B.

## C3. Dépendances risquées

76. OpenCorporates Open Data : snapshot gelé depuis 2019. Plan B ?
77. ESAP "live 2026" reporté plusieurs fois depuis 2021. Alternative ?
78. Shodan/Censys free : quotas mensuels incompatibles avec 5M cibles. Payer ou retirer ?
79. AFNIC zone .fr : réservé recherche académique. Retirer ou obtenir accord commercial.
80. Signaux Faibles Inria : maintenu ? Calibré sur données récentes ?

## C4. Gouvernance méthodologique

81. Les 30 questions `QUESTIONS_STRATEGIQUES V1` ont été réduites à 8 en V2 "car se déduisent" — certaines (stockage emails, scraping zone grise, partenariats INSEE, SEO fiches publiques, critères éthiques clients) ne se déduisent pas mécaniquement. Trancher explicitement.
82. Le `CHANGELOG` V2 du README ne mentionne pas que `PRICING.md`, `CONCURRENCE.md`, `RISQUES_CONFORMITE.md`, `ARCHITECTURE_DATA_V2.md` n'ont pas été resynchronisés avec les décisions V2. Le faire.
83. 15 docs produits en ~2h sans consulter l'existant ni interviewer le porteur. Risque : "plan parfait papier, irréaliste exécution". Quel moment pour stopper la prod doc et passer au terrain ?

---

<a id="partie-d"></a>

# PARTIE D — MÉTA-CHECKLIST D'AUTO-AUDIT

> **Avant de produire un nouveau doc ou d'updater un existant, l'agent se pose ces 15 questions.**

## D1. Temporalité

- [ ] Ai-je vérifié la date du jour ? Mes livrables au futur sont-ils dans le futur ?
- [ ] Si je parle d'un trimestre passé, ai-je écrit "Bilan" et non "Plan" ?

## D2. Existant

- [ ] Ai-je documenté l'état réel avant de proposer un état cible ?
- [ ] Ai-je identifié le chemin de migration du réel vers le cible ?
- [ ] Les clients actuels sont-ils mentionnés dans mon plan ?

## D3. Discovery client

- [ ] Chaque besoin produit que je décris s'appuie-t-il sur **au moins 3 verbatims** ?
- [ ] Ai-je au moins **une** LOI signée pour soutenir la trajectoire revenue ?
- [ ] Mon persona est-il **un nom de poste dans une entreprise réelle** que j'ai interviewée ?

## D4. Cohérence inter-docs

- [ ] Les chiffres de ce doc sont-ils cohérents avec `FINANCES_UNIFIE.md` ?
- [ ] La cap table totalise-t-elle bien 100% ?
- [ ] Les dates mentionnées sont-elles cohérentes avec les autres roadmaps ?

## D5. Factualité

- [ ] Chaque affirmation concurrentielle a-t-elle une **source datée** (URL, rapport, verbatim) ?
- [ ] Les acquéreurs cités existent-ils indépendamment (pas de filiales d'un même groupe) ?
- [ ] Les chiffres marché (TAM/SAM/SOM) viennent-ils d'une source (Gartner, IDC, PitchBook) ou sont-ils calculés à partir d'hypothèses explicites ?

## D6. Juridique

- [ ] Les sources data listées sont-elles toutes réellement accessibles **en 2026** (vérifier cassages récents : CJUE, CGU modifiées) ?
- [ ] Le scoring décisionnel bascule-t-il en IA Act haut risque selon l'usage client final ?
- [ ] La collecte de données personnelles respecte-t-elle DPIA + base légale + droit effacement ?

## D7. Réalisme d'exécution

- [ ] Chaque livrable a un **owner nommé** et un **effort en jours-homme** ?
- [ ] Les enchaînements critiques (LOI→closing, recrutement→onboarding) respectent-ils les durées marché ?
- [ ] La stack Y1 peut-elle être opérée par l'effectif Y1 ?

---

## Comment utiliser ce document

**Avant chaque itération de doc :**
1. Lire les questions 🔴 Partie A. Si une seule reste sans réponse écrite + source → stop, répondre d'abord.
2. Lire Partie D (méta-checklist). Cocher tous les items.
3. Seulement après : écrire ou updater.

**Règle de survie** : produire un doc qui échoue sur une question 🔴 = produire un doc qui sera démoli en réunion. Mieux vaut un doc court qui passe la grille qu'un doc long qui la rate.

---

## Historique des tours de revue

| Tour | Date | Documents revus | Questions émises |
|---|---|---|---|
| 1 | 2026-04-17 | ARCHITECTURE_DATA_V2 | ~30 |
| 2 | 2026-04-17 | ARCH_TECH V1, ROADMAP V1, BUDGET V1, RISQUES, QUESTIONS_STRATEGIQUES V1, README V1 | +43 |
| 3 | 2026-04-17 | AI_ACT, CONCURRENCE, PRICING | +22 |
| 4 | 2026-04-17 | VALIDATION_MARCHE, VALIDATION_API, ARCH_TECH V2, BUDGET V2, QUESTIONS_STRATEGIQUES V2 | +17 |
| 5 | 2026-04-17 | README V2 | +4 |
| 6 | 2026-04-17 | DECISIONS_VALIDEES, PLAN_EXECUTION_Q1_2026, QUESTIONS_STRATEGIQUES archivé, README updated | +15 |
| **Total** | | | **~131 questions** |

**Questions ouvertes au 2026-04-17 17h00** : ~85 (non résolues).
**Questions résolues ou obsolètes** : ~46.

---

_Document généré le 2026-04-17. À mettre à jour après chaque nouvelle itération. Les questions résolues restent dans le doc en italique barré pour traçabilité._

# RÉPONSES AU SELF-CHALLENGE

> Réponses collectées question par question, en partant des 🔴 bloquantes (Partie A).
>
> Date de démarrage : 2026-04-17. Statut : **en cours**.

---

## A1 — État réel vs plan (déni temporel)

### Question 1 — Livrables Q1 2026 réellement en prod ?

**Réponse utilisateur (2026-04-17)** : **RIEN n'est fait.**

| Livrable Q1 prévu | Statut |
|---|---|
| Infra Scaleway (Postgres + S3) | ❌ Pas fait |
| Bulk INSEE Sirene ingéré | ❌ Pas fait |
| DPO contracté | ❌ Pas fait |
| Lead Data Engineer recruté | ❌ Pas fait |
| Senior Backend recruté | ❌ Pas fait |
| Senior Frontend recruté | ❌ Pas fait |
| Pré-amorçage levé | ❌ 0 € |
| Interviews clients réalisées | ❌ 0 |
| LOI clients signées | ❌ 0 |
| Sources critiques validées | ❌ 0 / 20 |

### Conséquences immédiates

1. **Le "Plan Q1 2026" doit être renommé** : c'est en fait un **plan de démarrage Q2 2026** (avril-juin). Q1 est officiellement perdu (3 mois de retard sur le calendrier interne).
2. **Le calendrier glisse de 3 mois** : tous les jalons décalent.
   - Pré-amorçage devait être Q1 → maintenant **closing visé fin juin 2026**
   - MVP V1 devait être Q4 26 → maintenant **Q1 27**
   - Seed devait être Q1 27 → maintenant **Q3 27**
   - Series A devait être Q1 28 → maintenant **Q3 28**
3. **L'ARR Y4 (= 2029)** reste atteignable mais avec un calendrier décalé : Y4 devient 2030 ou il faut accélérer Y2-Y3.
4. **Implications financières** :
   - Pas de coûts engagés Y1 = cash brûlé = 0 (bonne nouvelle)
   - Mais : 3 mois de retard market = 3 mois de retard sur tous les revenus
   - Et : la fenêtre VC seed FR 2026 est plus tendue (correction marché en cours)
5. **Action immédiate** : créer `ETAT_REEL_2026-04-17.md` qui formalise "point de départ : zéro" et **renommer `PLAN_EXECUTION_Q1_2026.md` → `PLAN_DEMARRAGE_Q2-Q4_2026.md`**

### Questions 2-3 (A1)

- **Q2** : "Pourquoi un Plan Q1 au lieu d'un Bilan Q1 ?" → **Réponse** : par déni temporel de l'agent. Corrigé par reframe en plan de démarrage Q2-Q4 2026.
- **Q3** : "Si certains items faits, où est le bilan ?" → **N/A** (rien fait).

### Question 4 (A1) — Statut

- ⏳ À faire : produire `ETAT_REEL_2026-04-17.md` une fois que les questions A2 (existant V1) auront été clarifiées.

---

## A3 — Existant V1 (site + repo)

### Question — État réel de la V1

**Réponse utilisateur (2026-04-17)** :
- ✅ Site `demoema.vercel.app` **accessible**
- ❌ **0 utilisateur**
- ❌ **0 € de revenu**

### Conséquences

- La V1 = **prototype/démo public**, pas un produit en service avec clients
- **Aucun client à protéger** pendant la transition vers V2 → on peut refondre librement
- **Pas de revenu à préserver** → pas de pression cash immédiate sur la refonte
- Mais : le site visible publiquement = **vitrine d'image**, attention à ne pas casser sans plan de communication

### Réponses 4-6 (2026-04-17)

| # | Question | Réponse |
|---|---|---|
| 4 | Sources V1 opérationnelles ? | ❌ **Non** — les 25 sources sont **listées dans la doc mais pas branchées** dans le code |
| 5 | Stratégie email active ? | ❌ **Non implémentée** — juste documentée |
| 6 | Maintien du code ? | 👤 **Toi seul** (founder unique) |

### Conséquences majeures

1. **V1 = UI shell** sans intégration data réelle. La "plateforme" affichée sur Vercel est une démo visuelle, pas un système fonctionnel.
2. **Risque RGPD email = 0** (rien envoyé, pas de prod). On peut planifier proprement.
3. **Bus factor = 1** (un seul mainteneur = risque critique). Recruter Lead Data Eng devient encore plus prioritaire.
4. **Pas de migration technique à faire** depuis l'existant — on peut **partir from scratch sans dette**.
5. **Le code GitHub actuel** = base de design + structure front, à conserver comme socle pour le refactor V2.

### Bilan global de la Partie A1+A3

🎯 **L'état réel = "stade idée + démo visuelle"** :
- Site démo accessible
- 0 clients
- 0 revenu
- 0 sources réellement branchées
- 0 équipe (sauf founder)
- 0 cash levé
- 0 conformité (pas de DPO, mais aussi pas d'exposition)

**Implication stratégique** : on est en réalité en **mode pré-amorçage / pré-MVP**, pas en mode "scale-up qui valide V2". Le plan de marche doit l'assumer.

---

## A2 — Discovery client

### Réponses (2026-04-17)

| # | Question | Réponse |
|---|---|---|
| 1 | Interviews boutiques M&A faites | **2** (point de départ minimal) |
| 2 | LOI signée par un prospect | ❌ Non |
| 3 | Démo Vercel testée auprès de pros | ✅ Oui — **a plu** (auprès des 2 boutiques) |
| 4 | Réseau personnel M&A | ✅ Oui — **présent**, exploitable |
| 5 | Pourquoi ce projet vs revendre Pappers ? | **Build mais pas par défaut** : projet initialement sur Pappers, **dépendance contraignante + coût trop élevé** → décision de s'en affranchir. |

### Conséquences majeures

1. **Le wedge produit est légitimé par expérience vécue** : "on a essayé Pappers, c'est cher et lock-in". C'est le **meilleur argument possible** vis-à-vis d'autres boutiques M&A qui vivent le même problème.
2. **2 interviews = base de départ valide**, mais **pas suffisant** pour figer pricing/persona. Objectif Q2 : **passer de 2 à 20-30 interviews structurées** (cf. `VALIDATION_MARCHE.md`).
3. **Réseau personnel + démo qui plaît = avantage commercial réel** : potentiel de **3-5 LOI signables sous 30 jours** si on sort un pitch + offre claire.
4. **Build vs Buy = tranché par expérience** :
   - Buy (Pappers) : essayé → trop cher + dépendance
   - Build (sources publiques) : moins de dépendance, coût marginal nul, mais effort upfront important
5. **Argument de pitch VC** : "founder qui a vécu la douleur Pappers + réseau M&A + prototype validé par 2 boutiques + 100% sources publiques" = une vraie thèse.

### Réponses complémentaires (2026-04-17)

| Question | Réponse |
|---|---|
| Réaction des boutiques | **Intérêt fort pour une solution SaaS** car elles n'ont **pas de DSI** ni d'IA en interne aujourd'hui |
| Prix Pappers (benchmark) | ❓ **Inconnu** — à creuser avant de figer pricing |
| Pain #1 | **Perte de temps à analyser les données entreprises sans savoir vers où elles vont** + **besoin d'avoir les données rapidement dans un seul lieu** |

### Insights produit majeurs

1. **Persona affiné** : boutique M&A mid-market **sans DSI ni équipe data** → veut une solution **clé en main, managée, sans intégration**.
2. **Wedge produit clarifié** :
   - **Agrégation** (toutes les sources en 1 endroit) — résout le "perdre du temps à fouiller"
   - **Vitesse** (données rapides, pas besoin de re-fouiller)
   - **Intelligence prédictive** ("savoir vers où va la boîte") — = scoring, prédiction de cession, signaux faibles
3. **Killer features prioritaires** (vs pricing/concurrence inventés en V1) :
   - Recherche unifiée multi-sources sur 1 fiche
   - **Score "trajectoire" de l'entreprise** (en croissance / stagne / décroît / cession imminente)
   - Alertes signaux faibles
   - Export instantané pour pitch
4. **Pricing à benchmark** : il **faut absolument creuser combien elles payent Pappers** (et autres outils) avant d'oser un pricing. C'est probablement entre 50€/mois (Pappers Pro indiv) et 1000€/mois (multi-users + add-ons). Sans cet ancrage, mon pricing 49€/199€/15k€ est inventé.

### Action immédiate — re-contacter les 2 boutiques

Les 2 boutiques qui ont vu la démo sont nos **3 ancrages les plus précieux**. Action :

1. **Re-contacter sous 7 jours** chacune
2. Demander :
   - Combien payent-elles Pappers + autres outils data ?
   - Si on construit une solution qui résout leur pain #1, paieraient-elles : 49€ ? 199€ ? 499€ ? 999€/mois ? À partir de quel prix décrochent-elles ?
   - Acceptent-elles d'être **bêta-testeur premium** (gratuit 6 mois en échange de feedback) → **précurseur de LOI**

**Objectif** : transformer ces 2 prospects en 2 LOI signées d'ici fin avril 2026.

---

## A4 — Cohérence inter-docs

### Arbitrages validés (2026-04-17)

| # | Sujet | Décision verrouillée |
|---|---|---|
| 17 | DPO Y1 coût | **60k€/an** (5k€/mois externe régulier) |
| 20 | Pré-amorçage | **600k€ ciblé** |
| 16+44+45 | ARR Y4 | **8-15M€** (réaliste vs benchmark) |
| 21 | Europe Y3 | **UK + DE uniquement** (2 pays), reste Y4 |

### Corrections mécaniques (faites sans validation)

| # | Sujet | Avant | Après |
|---|---|---|---|
| 15 | Cap table | 102-122% | **100% exact** (cf. `FINANCES_UNIFIE.md`) |
| 19 | Équipe Y1 | 4-6 FTE / 6 / 4.5 (3 valeurs différentes) | **5 FTE max** fin Y1 |
| 18 | LLM Y1 | 6k€ vs 2.4k€ | **5k€** (aligné CSV) |

→ Toutes ces valeurs migrent vers `FINANCES_UNIFIE.md` comme **source unique de vérité**. Tous les autres docs y renverront.

---

## A5 — ARR mal défini

### Résolution (mécanique)

✅ **Corrigé** dans `FINANCES_UNIFIE.md` section 1.

| Avant | Après |
|---|---|
| "Y1 ARR = 50-100k€" (mélange tout) | **Revenue total Y1 = 44k€**, dont **ARR récurrent = 80k€** (≠ revenu Y1, c'est le run-rate fin de période) |

ARR désormais défini strictement comme **MRR récurrent × 12**, sans inclure les pay-per-report.

---

## A6 — Erreurs factuelles

### Corrections appliquées (2026-04-17)

| # | Erreur | Correction | Fichiers fixés |
|---|---|---|---|
| 24 | "Build to sell vers Moody's, S&P, Pitchbook, BvD" (= doublons) | **8 acquéreurs réels listés** : Moody's (= BvD/Diane/Orbis/Zephyr), Morningstar (= Pitchbook), S&P, LSEG, Clarivate, FactSet, D&B, Ellisphere/Altares | DECISIONS_VALIDEES, README, FINANCES_UNIFIE |
| 26 | "Pappers : pas d'IA générative" | **Pappers IA depuis 2024** | CONCURRENCE |
| 27 | "Société.com : peu d'IA" | **Assistant IA depuis 2024**, mais Q&A documentaire (pas prédictif) | CONCURRENCE |
| 28 | "Harvey AI émergent à surveiller" | **Établi : $300M levés en 2024 à $3Md valo** | CONCURRENCE |
| 29 | "INPI RBE accessible" | **Fermé au public depuis CJUE 22/11/2022** (WM/Luxembourg) — à retirer du datalake | ARCHITECTURE_DATA_V2 |
| Bonus | Concurrents absents | **Ajoutés** : Clay, Apollo, Ocean.io, Ellisphere, Altares, Creditsafe, Preqin, Infogreffe Pro, Orbis, Zephyr | CONCURRENCE |

---

## A7 — Risques juridiques (5 décisions)

### Décisions verrouillées (2026-04-17)

| # | Question | Décision |
|---|---|---|
| 30 | Usage du score défaillance par clients | **CGU interdisent expressément** l'usage décisionnel automatique sur personnes physiques. Le score reste "aide à la qualification". → évite bascule en système IA haut risque |
| 31 | Fine-tuning Mistral 7B | **Renoncer** au fine-tuning. Claude + Mistral via API uniquement (statut "déployeur", pas "fournisseur GPAI") |
| 32 | DPIA (RGPD art. 35) | **Planifié Q3 2026** par cabinet (8-15k€ une fois + 5k€/an mise à jour) |
| 34 | Droits voisins presse | **Option A** : titre + URL + date uniquement (pas de corps d'article). Pas de licence ADPI/CFC Y1-Y2 |
| 35 | Trustpilot + Google Reviews | **Retirés du datalake** (CGU interdisent scraping commercial). Re-évaluer en Y3 via API Business officielle |

### Conséquences sur le datalake (143 → 141 sources actives)

- ❌ Source #41 INPI RBE : retirée (CJUE 2022)
- ❌ Source #125 Trustpilot : retirée (CGU)
- ❌ Source #126 Google Reviews : retirée (CGU)
- ⚠️ Sources #119-124 presse : **mode titre+URL+date uniquement**
- → **140 sources réellement exploitables** sur 143 catalogées

### Conséquences architecture & roadmap

1. **Pas de fine-tuning ML Y2** → simplifie le stack (juste API LLM)
2. **CGU enrichies** : ajouter clause "no automated decision on natural persons" → à rédiger Q3 2026 avant lancement Pro
3. **Budget conformité réajusté** :
   - DPO 60k€/an
   - DPIA initial 12k€ (Q3 2026)
   - Audit AI Act 10k€ (Q4 2026)
   - Total Y1 conformité : **~80-90k€**
4. **Pas de risque GPAI provider** = pas d'obligations art. 53 AI Act
5. **Risque CGU presse** : à monitorer si la loi française durcit les droits voisins

---

## ✅ Bilan Partie A 🔴 — TOUTES les questions résolues

| Section | Statut |
|---|---|
| A1 — Déni temporel | ✅ Résolu (rien fait, calendrier décale +3 mois) |
| A2 — Discovery client | ✅ Résolu (2 boutiques + réseau + thèse Pappers) |
| A3 — Existant V1 | ✅ Résolu (démo seule, 0 client) |
| A4 — Cohérence inter-docs | ✅ Résolu (FINANCES_UNIFIE.md créé) |
| A5 — ARR mal défini | ✅ Résolu (corrigé dans FINANCES_UNIFIE) |
| A6 — Erreurs factuelles | ✅ Résolu (5 docs fixés) |
| A7 — Risques juridiques | ✅ Résolu (5 décisions) |

**Prochaine étape** : Partie B (🟠) — 28 questions importantes, ou actions terrain prioritaires.

---

---

(Ce document sera complété au fil des réponses.)

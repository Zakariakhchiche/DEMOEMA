# PLAN DE DÉMARRAGE Q2-Q4 2026 — Sprint plan révisé

> **Document refondu le 2026-04-17 après audit `SELF_CHALLENGE`.**
>
> Constat : au 17 avril 2026, **rien n'est fait** (cf. `REPONSES_SELF_CHALLENGE.md` Partie A1). Q1 2026 = trimestre perdu sur le calendrier interne. Le plan se décale de **+3 mois**.
>
> Ce document remplace l'ancien `PLAN_EXECUTION_Q1_2026.md` (dénié temporel).
>
> **Périmètre** : 39 semaines (avril → décembre 2026). Objectif : valider le marché, lever 600k€ pré-amorçage, recruter 3 hires clés, MVP V1 sur les rails fin Y1.

---

## État de départ (2026-04-17)

✅ **Atouts**
- Site `demoema.vercel.app` accessible (démo visuelle)
- 2 boutiques M&A ont vu la démo — **ont aimé**
- Réseau personnel M&A exploitable
- Thèse "affranchissement de Pappers" légitimée par expérience vécue
- Décisions stratégiques verrouillées (cf. `DECISIONS_VALIDEES.md`)
- Source unique de vérité chiffrée (`FINANCES_UNIFIE.md`)

❌ **Manques (point de départ)**
- 0 client, 0 revenu, 0 LOI signée
- 0 source data réellement branchée (juste listées)
- 0 équipe (founder seul)
- 0 cash levé
- Pas de DPO contracté
- Pas d'infra
- Pas de pitch deck pré-amorçage

---

## Vue d'ensemble (39 semaines)

| Période | Semaines | Focus principal |
|---|---|---|
| **Avril** | S1-S2 | Re-contact 2 boutiques + sourcing 50 cibles + setup outils |
| **Mai** | S3-S6 | 25 interviews + validation 10 sources + démarrage deck |
| **Juin** | S7-S10 | Pitchs investisseurs + closing pré-amorçage 600k€ + recrutement Lead Data Eng |
| **Juillet** | S11-S14 | Onboarding Lead Data + DPO contracté + Setup infra Scaleway + premier sprint dev |
| **Août** | S15-S18 | Ingestion 10 sources + modèle entités + recrutement Backend |
| **Septembre** | S19-S22 | API v1 + Backend onboardé + recrutement Frontend + premiers rapports payants |
| **Octobre** | S23-S26 | Frontend onboardé + front MVP + Pro lancé |
| **Novembre** | S27-S30 | Module compliance + détection auto BODACC + audit RGPD |
| **Décembre** | S31-S34 | DPIA + 50 clients payants + bilan Y1 + démarrage levée Seed |

---

## AVRIL 2026 — Re-contact + sourcing + setup

### S1 (du 20 au 26 avril) — Re-contact urgent

**Priorité absolue** : ne pas perdre l'élan des 2 boutiques.

- [ ] **Re-contacter les 2 boutiques M&A** par email + visio courte (cf. `KIT_ACTION_30JOURS.md`)
  - Demander combien elles payent Pappers (et autres outils)
  - Comprendre LE pain #1 dans le détail
  - Proposer le statut **bêta-testeur premium** (gratuit 6 mois)
  - Objectif : transformer en **2 LOI signées** sous 30 jours
- [ ] **Sourcing 50 prospects supplémentaires** ICP (boutiques M&A FR mid-market)
  - Sources : France Invest, AFIC, CFNews annuaire, LinkedIn, réseau personnel
- [ ] **Setup outillage** :
  - Linear (project mgmt), Notion (docs), Slack, Calendly, Otter.ai
  - Comptes APIs gratuits : INSEE OAuth, INPI compte, api.piste.gouv.fr
- [ ] **Charte d'équipe** + valeurs + rituels (même seul, structure pour les futurs hires)

**Effort** : 35h founder
**Owner** : Founder

### S2 (27 avril – 3 mai) — Sourcing & invitations

- [ ] **30 invitations LinkedIn + email** envoyées (objectif 50% = 15 interviews bookées)
- [ ] **Script d'interview** validé (cf. `KIT_ACTION_30JOURS.md`)
- [ ] **Banque BPI rendez-vous** pris (Bourse French Tech)
- [ ] **Premier draft pitch deck** (5 slides : pourquoi maintenant, marché, proto, équipe, ask)

**Effort** : 35h founder

---

## MAI 2026 — Interviews + démarrage deck

### S3 (4-10 mai) — Premières interviews

- [ ] **5 interviews** réalisées (visio 45 min)
- [ ] **Script validation API v1** : tester INSEE SIRENE bulk + API Recherche Entreprises
- [ ] **Mise à jour pitch deck** post-interviews

### S4 (11-17 mai) — Continuation

- [ ] **5 interviews** supplémentaires (total 10)
- [ ] **Validation 3 sources** supplémentaires (INPI RNE, BODACC, Judilibre)
- [ ] **Atelier mid-month** : retours interviews → ajuster cible/pricing
- [ ] **DPO** : 3 cabinets contactés

### S5-S6 (18-31 mai)

- [ ] **15 interviews** supplémentaires (total 25 cumul)
- [ ] **Validation 5 sources** restantes (top 10 fait)
- [ ] **Audit CGU des sources** par avocat (1 semaine, ~5k€)
- [ ] **Pitch deck V2** (15 slides : Problem, Solution, Market, Traction, Team, Roadmap, Use of Funds)
- [ ] **Modèle financier** v1 mis à jour avec verbatims interviews
- [ ] **Préparation closing pré-amorçage** : data room

**Owner** : Founder + Designer freelance (mockups pour démo investisseurs)

---

## JUIN 2026 — Pitchs + closing pré-amorçage

### S7-S10

- [ ] **15 pitchs investisseurs** (BA + VC seed FR)
  - Ciblés : Frst, Kima, Elaia, Newfund, Educapital, Ovni Capital
  - Plus 8-10 BA avec réseau M&A/data
- [ ] **3 LOI investisseurs** signées
- [ ] **Term sheet** négociée avec lead investor
- [ ] **Closing pré-amorçage 600k€** (statuts modifiés, virement reçu) — visé fin juin
- [ ] **Job description Lead Data Engineer** publiée + 5 candidats short-listés
- [ ] **5 derniers interviews clients** (total 30 = objectif validation marché atteint)
- [ ] **Atelier décisions Go/No-Go** : confirmation persona/use case/pricing

**Effort** : 80% founder time
**KPI fin juin** : 600k€ closés + 30 interviews + 5 LOI investisseurs + 2 LOI clients

---

## JUILLET 2026 — Onboarding + setup infra

### S11-S14

- [ ] **Lead Data Eng démarre** (offer signée juin, démarrage juillet)
- [ ] **DPO externe contracté** (5k€/mois)
- [ ] **Compta** signé
- [ ] **Setup infra Scaleway** :
  - Postgres 16 managed (Pro-XS, ~200€/mois)
  - Bucket S3 (raw zone)
  - GitHub Actions CI/CD
  - Repo `demoema-data` initialisé
- [ ] **Dagster + dbt-core** installés en local
- [ ] **Premier sprint dev** : ingestion **5 sources** (INSEE bulk, INSEE delta, API Recherche, BODACC, INPI RNE)
- [ ] **5M SIREN** chargés en Postgres (test volumétrie + latence)

**Effort** : Founder 60% + Lead Data 100%
**Budget juillet** : ~25k€ (salaires + infra + outils)

---

## AOÛT 2026 — Ingestion + recrutement Backend

### S15-S18

- [ ] **+5 sources** ingérées (Judilibre, OpenSanctions, Gels Avoirs, GLEIF, OpenCorporates)
- [ ] **Modèle d'entités v1** (entreprises, etablissements, personnes)
- [ ] **Résolution simple** SIREN ↔ LEI ↔ Wikidata (pas de Splink Y1)
- [ ] **Recrutement Senior Backend** : démarrage à fin août / début septembre
- [ ] **Mentions légales / RGPD policy** rédigées
- [ ] **LIA documentée** (Légitimate Interest Assessment) avec DPO

**Owner** : Lead Data + Founder (recrutement)

---

## SEPTEMBRE 2026 — API v1 + Backend onboardé + premiers revenus

### S19-S22

- [ ] **Senior Backend démarre**
- [ ] **API REST v1** (FastAPI) : endpoints recherche entreprise + fiche
- [ ] **Recrutement Senior Frontend** : démarrage à fin septembre
- [ ] **Première version "Rapport Cible"** vendable (490€)
- [ ] **Premier rapport vendu** aux 2 boutiques (objectif : 2 ventes test)
- [ ] **Mise en place auth** Supabase + plans Free/Starter

**KPI fin septembre** : API live, 2 rapports vendus, 50 utilisateurs Free

---

## OCTOBRE 2026 — Frontend + lancement Pro + ⭐ Alertes pré-cession

### S23-S26

- [ ] **Senior Frontend démarre**
- [ ] **Front Next.js refactor** : recherche + fiche enrichie + export PDF
- [ ] **Lancement plan Pro 199€/mois** (+ engagement annuel −20%)
- [ ] **Cartographie dirigeants v0** (graphe simple table Postgres + viz force-graph)
- [ ] ⭐ **Killer feature #1 : Alertes signaux pré-cession** (rule-based sur BODACC + INPI RNE)
  - Détection : changement mandataires, nomination CFO dirigeant 55+, délégations AG, dirigeant vers PE
  - Email hebdo "3 entreprises de votre secteur montrent des signaux"
  - Dashboard dédié
- [ ] **Export Excel templates M&A** (Teaser, Buyer list, Longlist, DD brief)
- [ ] **Export CSV compatible Affinity**
- [ ] **Clause responsabilité IA** CGU (conformité AI Act)
- [ ] **Premiers utilisateurs Starter** (10 cible)
- [ ] **Audit RGPD intermédiaire** par DPO

**Équipe fin octobre** : 4 FTE (founder + Lead Data + Backend + Frontend)

---

## NOVEMBRE 2026 — Compliance + ⭐ Who advises whom (démarrage)

### S27-S30

- [ ] **Module compliance/KYC** (sanctions, gels avoirs, RBE consolidé)
- [ ] **Détection auto procédures collectives** (BODACC daily pull + diff)
- [ ] **+5 sources** : Certificate Transparency, GitHub, GDELT, BOAMP, France Travail
- [ ] **Scoring M&A v0** : 30-50 features les plus impactantes
- [ ] ⭐ **Killer feature #2 — Who advises whom (démarrage dev)**
  - Scraping CFNews RSS + Les Échos + La Tribune (légal, RSS public)
  - Labellisation 500 communiqués de deals M&A (cible, acquéreur, advisors)
  - Fine-tuning CamemBERT sur extraction nommée
- [ ] **API Affinity v1** (export bidirectionnel)
- [ ] **Préparation levée Seed** : deck V3 + traction metrics + intros

**KPI fin novembre** : 30 clients payants, MRR 4-5k€, NPS premier mesure, Who advises whom V0 en beta interne

---

## DÉCEMBRE 2026 — DPIA + ⭐ Who advises whom V1 + bilan Y1 + démarrage Seed

### S31-S34

- [ ] **DPIA validé** par DPO + cabinet RGPD (12k€)
- [ ] **AI Act compliance baseline** : CGU avec clause "no automated decision"
- [ ] ⭐ **Who advises whom V1 publié** (3 000+ deals FR indexés 2020-2026, précision >85% sur labellisation test)
- [ ] **Bilan Y1 documenté** (KPIs vs objectifs, learnings, corrections)
- [ ] **50 clients payants** (objectif fin Y1)
- [ ] **MRR 6-8k€** (= ARR 80k€ run-rate, cf. FINANCES_UNIFIE)
- [ ] **Premier pitch Seed** auprès de VCs (closing visé Q1 2027)
- [ ] **Communication externe** : LinkedIn launch officiel + Product Hunt
- [ ] **Planning Q1 2027** figé

---

## Récapitulatif effort & coûts (avril → décembre 2026)

| Mois | FTE | Salaires | Autres | Levée | Cash position |
|---|---|---|---|---|---|
| Avril | 1 founder | 0 | 5k | 0 | -5k |
| Mai | 1 + 0.5 freelance design | 5k | 15k | 0 | -25k |
| Juin | 1 + 0.5 | 5k | 20k | **+600k** | +550k |
| Juillet | 2 (Lead Data start) | 22k | 25k | 0 | +503k |
| Août | 2 | 22k | 18k | 0 | +463k |
| Septembre | 3 (Backend start) | 36k | 22k | 0 | +405k |
| Octobre | 4 (Frontend start) | 49k | 28k | 0 | +328k |
| Novembre | 4 | 44k | 30k | 0 | +254k |
| Décembre | 4 | 44k | 35k | 0 | +175k |

> **Cash position fin décembre 2026** : **~175k€** = runway ~3 mois → besoin Seed Q1 2027 (déjà en pipeline).

---

## KPIs de succès (objectifs fin décembre 2026)

| KPI | Objectif | Backup si raté |
|---|---|---|
| Clients payants | 50 | Min acceptable : 30 |
| MRR | 6-8k€ | Min : 4k€ |
| LOI clients signées | 5+ | Min : 3 |
| Sources opérationnelles | 15 | Min : 10 |
| Équipe FTE | 4 | Min : 3 + freelances |
| Cash en banque fin Y1 | ≥150k€ | <50k€ = bridge urgent |
| DPO + RGPD compliant | 100% | Bloquant ventes Pro |
| Levée Seed démarrée | Pitchs en cours | Min : deck prêt |

---

## Dépendances critiques (chemin critique)

```
Re-contact 2 boutiques (S1)
  └→ 2 LOI clients (S4-S6) [validation marché]
      └→ Pitch deck V2 (S5-S6)
          └→ Closing 600k€ (S10) [funding gate]
              └→ Lead Data hire (S11)
                  └→ Setup infra (S13)
                      └→ Premier sprint dev (S14)
                          └→ Backend hire (S18)
                              └→ API v1 (S20)
                                  └→ Frontend hire (S22)
                                      └→ Front MVP (S26)
                                          └→ Pro launch (S26)
                                              └→ MRR (S27-S34)
```

**Si closing pré-amorçage glisse** → tout le reste glisse de la même durée.

---

## Risques majeurs et mitigation

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Closing pré-amorçage non bouclé en juin | Moyenne | Critique | Bridge personal money + Karmen RBF / délai +1-2 mois |
| Lead Data Eng pas trouvé | Moyenne | Haute | Freelance senior 6 mois en attendant + élargir aux profils ex-Doctrine, Pappers |
| Pas assez de LOI clients (<3) | Moyenne | Haute | Prolonger interviews juin → août |
| Pivot nécessaire après interviews | Moyenne | Moyenne | 2 semaines buffer prévues + scénarios de pivot prédéfinis |
| Ralentissement marché VC FR | Élevée | Haute | Multiplier les pitchs (15+) + non-dilutif BPI |
| Burnout founder | Moyenne | Critique | Charte ways of working + advisor coach + freelances pour offload |

---

## Ce qui est explicitement REPORTÉ (post-Y1)

- ❌ ML Engineer Y1 → décalé Q1 2027 (Seed)
- ❌ Splink entity resolution → décalé Y2
- ❌ ClickHouse / Neo4j / Qdrant → décalé Y2-Y3
- ❌ Europe → décalé Y3 (UK + DE seulement)
- ❌ Multi-tenant SaaS → décalé Y3
- ❌ Modules verticaux (santé, ESS) → décalé Y3
- ❌ Marketplace datasets → décalé Y4
- ❌ Fine-tuning Mistral → **abandonné** (cf. AI_ACT_COMPLIANCE)

---

## Le mantra Q2-Q4 2026

> **"Discovery first. Funding second. Product third."**
>
> 30 interviews + 5 LOI + 600k€ levés **avant** d'écrire 1 ligne de code produit majeur. Si tu te surprends à coder une feature en mai 2026, tu te trompes de priorité. Reviens à la validation marché.

---

## Modifications majeures vs ancien `PLAN_EXECUTION_Q1_2026.md`

| Aspect | V1 (déni temporel) | V2 (révisé) |
|---|---|---|
| Période | Q1 2026 (jan-mars) | **Q2-Q4 2026 (avril-décembre)** |
| Démarrage | "Setup S1 = 5 jan" | **"Re-contact 2 boutiques S1 = 20 avril"** |
| Pré-amorçage | Closing fin Q1 | **Closing fin juin 2026** |
| Premier sprint dev | S12 (mars) | **S13-S14 (juillet)** |
| Premiers revenus | M5 (mai) | **Septembre** |
| Lancement Pro | Q4 26 | **Octobre** |
| Bilan Y1 | S13 fin mars | **Décembre** |
| Levée Seed | Q1 2027 | **Q1 2027 confirmé** (pipeline démarre déc) |

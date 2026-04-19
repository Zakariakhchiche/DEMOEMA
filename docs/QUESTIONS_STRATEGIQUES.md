# QUESTIONS STRATÉGIQUES — V2 (TRANCHÉES ✅)

> ✅ **STATUT : RÉSOLU le 2026-04-17.** Les 8 décisions ont été validées (Scénario B / recommandations par défaut).
>
> Voir [`DECISIONS_VALIDEES.md`](./DECISIONS_VALIDEES.md) pour le détail des décisions verrouillées.
>
> Ce fichier est conservé en archive pour traçabilité.

---

## 1. Persona prioritaire (1 seule réponse)

> **Quelle est la cible primaire pour Y1-Y2 ?**

- [ ] **Boutiques M&A FR mid-market** (~200 boutiques, ~2000 utilisateurs) — recommandé : douleur réelle, cycle court
- [ ] Fonds PE FR mid-market (50-500M€ AUM)
- [ ] Banques d'affaires (M&A teams)
- [ ] Corporates (direction M&A/stratégie)

**Pourquoi c'est critique** : conditionne 100% de la stratégie produit, pricing, GTM, et même le choix des sources data.

---

## 2. Use case prioritaire #1 (1 seule réponse)

> **Quel est LE problème qu'on résout en priorité ?**

- [ ] **Sourcing M&A** (trouver des cibles cachées) — différenciation forte vs Pappers
- [ ] Due diligence accélérée (synthèse 360° d'une cible)
- [ ] Veille concurrentielle (qui bouge dans mon secteur)
- [ ] KYC / Compliance (vérifier sanctions, RBE)

**Pourquoi c'est critique** : dicte le scoring M&A, le copilot, les alertes — bref, 80% de la valeur produit.

---

## 3. Périmètre data Y1 (1 seule réponse)

> **Combien d'entreprises FR couvrir au lancement ?**

- [ ] **5M (toutes FR)** mais profondeur variable selon taille — recommandé pour SEO + crédibilité
- [ ] 150k (>10 salariés) — sweet spot M&A, infra ×30 plus légère
- [ ] 7000 (ETI + grandes) — ultra-focus deals premium
- [ ] Sectoriel pilote (1 vertical : santé OU industrie OU tech)

**Pourquoi c'est critique** : différentiel infra et coûts ×30 entre option A et B.

---

## 4. Budget réel disponible Y1 (1 seule réponse)

> **Quelle enveloppe disponible pour 2026 ?**

- [ ] **Bootstrap (<200k€)** — scope ultra-réduit, 2-3 personnes, validation puis pivot
- [ ] **Pré-amorçage (200-700k€)** — recommandé : roadmap V2 réaliste
- [ ] **Seed direct (1.5M€+)** — roadmap accélérée, mais besoin réseau VC immédiat
- [ ] À déterminer / levée en cours

**Pourquoi c'est critique** : conditionne le choix entre roadmap V2 et roadmap "minimal viable".

---

## 5. Stack technique Y1 (1 seule réponse)

> **On garde ou on refactore l'existant Vercel/FastAPI ?**

- [ ] **Garder le front Next.js, refactorer le backend en parallèle** (recommandé V2)
- [ ] Tout garder, ajouter par-dessus (dette technique grandissante)
- [ ] Refonte totale, démarrer from scratch (plus propre mais ralentit Y1)

**Pourquoi c'est critique** : impacte directement la vélocité Q1-Q2 2026.

---

## 6. Souveraineté data (1 seule réponse)

> **Hébergement et stockage des données ?**

- [ ] **Souveraineté FR stricte (Scaleway)** — recommandé : sales en France/Europe, AI Act friendly
- [ ] Cloud US OK (AWS, GCP) — plus de services managés mais frein commercial UE
- [ ] Hybride : data en FR, compute pouvant être hors FR

**Pourquoi c'est critique** : impact ventes Enterprise (banques, fonds PE = exigent souveraineté), impact RGPD/AI Act.

---

## 7. Quand démarrer l'Europe ? (1 seule réponse)

> **Extension hors FR à quel moment ?**

- [ ] Y3 (recommandé V2) — focus FR Y1-Y2, Europe quand PMF prouvé
- [ ] Y2 (UK + DE en plus dès le PMF FR)
- [ ] Y1 (UK dès le départ — bonus différenciation)
- [ ] FR only sur les 4 ans (cible mid-market FR suffit pour 15M€ ARR)

**Pourquoi c'est critique** : impact infra, équipe (langues, cultures), conformité (RGPD pays par pays).

---

## 8. Vision exit (1 seule réponse)

> **Sortie envisagée à 5-7 ans ?**

- [ ] **Build to sell** vers Moody's, S&P, Pitchbook, Bureau van Dijk (recommandé pour SaaS data B2B)
- [ ] Build to scale (IPO 7-10 ans) — ambition forte, dilution importante
- [ ] Long-term independent (rentabilité dès Y3, croissance modérée)
- [ ] À déterminer / pas de stratégie figée

**Pourquoi c'est critique** : conditionne la cap table, les choix de VC, le rythme de croissance, les investissements R&D vs sales.

---

# Cadre décisionnel suggéré

| Question | Décision recommandée par défaut | Pourquoi |
|---|---|---|
| 1. Persona | Boutiques M&A FR mid-market | Marché atteignable, douleur réelle, réseau possible |
| 2. Use case | Sourcing M&A | Différenciation max vs Pappers/Diane |
| 3. Périmètre | 5M (avec profondeur variable) | SEO + crédibilité + flexibilité |
| 4. Budget | Pré-amorçage 200-700k€ | Aligné roadmap V2 |
| 5. Stack | Garder front, refactorer backend | Pragmatique, vélocité préservée |
| 6. Souveraineté | Scaleway (FR strict) | Indispensable pour Enterprise UE |
| 7. Europe | Y3 | Focus PMF FR d'abord |
| 8. Exit | Build to sell vers acteur data | Marché data M&A consolide depuis 10 ans |

---

# Si tu veux raisonner par scénario

## Scénario A — "MVP Bootstrap"

> Réponses : Boutiques M&A FR / Sourcing / 150k entreprises / <200k€ / Garder existant + minimal refacto / Scaleway / FR only / Long-term independent

**Pour qui** : si pas de capacité de levée, ambition rentabilité rapide
**Roadmap adaptée** : voir `ROADMAP_BOOTSTRAP.md` (à créer si scénario retenu)
**Timeline** : 50k€ ARR en Y1, 500k€ Y2, 1.5M€ Y3, rentable Y3

## Scénario B — "Roadmap V2 standard" (recommandée)

> Réponses : Boutiques M&A FR / Sourcing / 5M / 200-700k€ pré-amorçage / Refonte progressive / Scaleway / Y3 Europe / Build to sell

**Pour qui** : trajectoire VC classique B2B SaaS, exit 5-7 ans
**Roadmap adaptée** : `ROADMAP_4ANS.md` V2 (déjà rédigée)
**Timeline** : 100k€ ARR Y1, 800k€ Y2, 3M€ Y3, 12M€ Y4

## Scénario C — "Ambition européenne accélérée"

> Réponses : PE/Banques / Sourcing+DD / 5M FR + tests UE / Seed direct 1.5M€+ / Refonte totale / Scaleway / Y2 Europe / Build to scale (IPO)

**Pour qui** : si fondateurs avec réseau VC fort, équipe complète disponible immédiatement
**Roadmap adaptée** : `ROADMAP_AMBITIEUSE.md` (à créer si retenu)
**Timeline** : 200k€ ARR Y1, 1.5M€ Y2, 6M€ Y3, 20M€+ Y4

---

# Comment répondre

Tu peux :
1. **Répondre directement à chaque question** (le plus rapide) — je mets à jour la doc en conséquence
2. **Choisir un scénario A/B/C** — j'adapte tout
3. **Demander un atelier de 2h** où on creuse chaque question — je prépare un guide

> **Recommandation** : commence par répondre aux **questions 1, 2, 4, 8** (les 4 vraiment structurantes). Les 4 autres se déduisent.

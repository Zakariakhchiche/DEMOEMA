# VALIDATION MARCHÉ

> ⚠️ **Document V2 — calendrier décalé +3 mois post-audit 2026-04-17.**
>
> ⚠️ Toute référence à **"Q1 2026"** dans ce document doit être lue comme **"Q2 2026 (avril-juin)"**.
>
> Plan opérationnel à jour : [`PLAN_DEMARRAGE_Q2-Q4_2026.md`](./PLAN_DEMARRAGE_Q2-Q4_2026.md)
> Templates terrain prêts : [`KIT_ACTION_30JOURS.md`](./KIT_ACTION_30JOURS.md)
>
> 30 interviews clients à mener avant tout développement majeur. Méthodologie inspirée de "The Mom Test" (Rob Fitzpatrick) et "Continuous Discovery Habits" (Teresa Torres).
>
> **État au 17/04/2026** : 2 interviews déjà réalisées (boutiques M&A), démo a plu, **objectif 30 fin juin 2026**. 0 LOI signée.

---

## Pourquoi cette phase est non-négociable

Le risque #1 d'un projet data ambitieux comme DEMOEMA n'est **PAS technique** — il est de **construire la mauvaise chose**.

À ce stade, je ne sais pas avec certitude :
- Si les boutiques M&A FR achèteraient à 199€/mois ou 1990€/mois
- Si le graphe dirigeants est leur vrai pain ou un nice-to-have
- Si les fonds PE préfèrent une intégration Affinity ou un standalone
- Si le scoring M&A automatisé est crédible aux yeux des analystes
- Si la fraîcheur J+1 sur les signaux justifie le coût infra

**Sans validation, on construit pour 6 mois et on découvre qu'on s'est trompés.**

---

## Période et timing

- **Quand** : Janvier-Février 2026 (Q1, en parallèle de la refonte technique fondations)
- **Durée** : 6 semaines
- **Effort** : 1 personne (founder ou product) à 50% temps + 1 designer à 30% temps

---

## Cibles d'interview (30 personnes)

### Répartition par persona

| Persona | Nb cible | Comment recruter |
|---|---|---|
| **Boutiques M&A FR mid-market** | 8 | LinkedIn, réseau, salons CFNews |
| **Fonds PE FR mid-market (50-500M€ AUM)** | 6 | LinkedIn, réseau France Invest |
| **M&A team banques d'aff. FR** | 4 | Réseau (banque privée, BNP M&A, etc.) |
| **Corporate développement (dpt M&A grands groupes)** | 4 | LinkedIn |
| **Conseil M&A / TS (Big4 + indep.)** | 4 | LinkedIn, alumni écoles |
| **Family offices** | 2 | Réseau |
| **VC Series A/B** (test marché annexe) | 2 | LinkedIn, Frst, Eutopia |

### Critères de qualification

- ✅ Personne qui **utilise quotidiennement** des outils de sourcing/intel M&A
- ✅ A le pouvoir d'**influencer/décider** un achat outil
- ✅ Travaille dans une équipe de **2-50 personnes** (sweet spot mid-market)
- ❌ Pas d'amis/famille (biais)
- ❌ Pas de personnes qui veulent juste "rendre service"

---

## Script d'interview (45 min)

### Partie 1 — Contexte (10 min)
1. Pouvez-vous me décrire votre rôle et l'équipe ?
2. Combien de deals/cibles regardez-vous par mois ?
3. Quelle est votre journée type côté sourcing/research ?

### Partie 2 — Situation actuelle (15 min) — **NE PAS pitcher le produit**
4. Quels outils utilisez-vous actuellement pour sourcer/qualifier ?
5. Combien dépensez-vous par an en outils de data/intel ?
6. Décrivez-moi la dernière fois que vous avez cherché à qualifier une cible. Qu'avez-vous fait étape par étape ?
7. Qu'est-ce qui vous prend le plus de temps dans cette tâche ?
8. Quelle a été la dernière fois où vous avez raté une info importante ? Que s'est-il passé ?

### Partie 3 — Pain points (10 min)
9. Quelles sont les 3 choses les plus frustrantes dans vos outils actuels ?
10. Si vous pouviez **créer la fonctionnalité parfaite**, ce serait quoi ?
11. Y a-t-il une donnée que vous **rêveriez** d'avoir mais n'avez pas accès ?
12. Comment décidez-vous d'arrêter de creuser une cible ?

### Partie 4 — Disposition à payer (5 min) — **À la fin uniquement**
13. Sans entrer dans les détails, si un outil résolvait [pain point principal mentionné], combien seriez-vous prêt à payer par mois/par user ?
14. Qui valide ce type d'achat dans votre équipe ?
15. Quel est votre budget annuel "outils data" ?

### Partie 5 — Démo light (5 min) — **Optionnel, dernière partie**
- Montrer 1-2 mockups statiques (pas de demo interactive)
- "Est-ce que ça résoudrait le problème que vous m'avez décrit ?"
- "Qu'est-ce qui vous ferait NE PAS l'acheter ?"

---

## Règles d'or (The Mom Test)

| ✅ À FAIRE | ❌ À ÉVITER |
|---|---|
| Parler de leur vie, pas de votre idée | Pitcher votre produit |
| Demander des **faits passés** | Demander des opinions sur le futur |
| Demander des **détails spécifiques** | Accepter des généralités |
| Creuser quand quelqu'un dit "intéressant" | Se contenter du compliment |
| Chercher les **engagements** (essai, mise en relation) | Chercher la validation émotionnelle |

**Test ultime** : si vous ressortez de l'interview en pensant "ils ont adoré l'idée", vous avez raté l'interview. Si vous ressortez avec **3 nouveaux pain points concrets**, c'est gagné.

---

## Livrables à la fin

### 1. Synthèse quantitative

| Métrique | Cible |
|---|---|
| Nb interviews réalisées | 30 |
| Pain points mentionnés ≥ 3 fois | 5-10 |
| Disposition à payer médiane | À calculer |
| % qui acceptent un suivi (essai bêta) | >40% |
| % qui mentionnent Pappers/Diane/Pitchbook | À mesurer (calibrer concurrence) |

### 2. Personas affinés

3 personas détaillés avec :
- Background, contexte, journée type
- Top 3 pain points
- Outils actuels utilisés et budgets
- Critères d'achat
- Quote signature ("In their words")

### 3. Décisions produit

- ✅ **Confirmer / Pivoter** la priorité Y1 (graphe dirigeants vs scoring vs alertes vs copilot)
- ✅ **Pricing validé** ou ajusté
- ✅ **Liste features** Y1 priorisée par ICE (Impact × Confidence × Ease)
- ✅ **Beta list** : 10-20 personnes prêtes à tester le MVP

---

## Méthodologie de prise de notes

Pour chaque interview :
- **Audio** (avec consentement) — Otter.ai ou Notta pour transcription auto
- **Notes structurées** dans un Notion/Airtable :
  - Persona, entreprise, role
  - Outils actuels + budget
  - Top 3 pains (verbatim)
  - Disposition à payer
  - Suivi (essai ? mise en relation ?)
- **Tag** : signaux forts (mentionné par >5 personnes)

---

## Critères de Go/No-Go

À la fin des 30 interviews, on lance le développement V2 si :

- ✅ Au moins **15 personnes** ont mentionné le pain point principal
- ✅ Au moins **10 personnes** sont prêtes à payer notre tarif Pro (199€/mois)
- ✅ Au moins **5 personnes** acceptent de payer un pré-engagement (Letter of Intent)
- ✅ Au moins **3 entreprises** acceptent de payer un POC (1-3 mois)

**Si 2 critères sur 4 manquent** → pivot ou scope reduction.

---

## Coût estimé

| Poste | Coût |
|---|---|
| Temps founder/product (50% × 6 sem) | inclus salaires |
| Temps designer (30% × 6 sem mockups) | inclus |
| Outils (Calendly, Otter, Notion) | 200€ |
| Cadeaux/remerciements (carte 50€ × 30) | 1500€ |
| Déjeuners interviews physiques (10) | 500€ |
| Recrutement via Respondent.io ou User Interviews | 2000€ (si pas assez de réseau) |
| **Total** | **~4200€** |

**ROI** : éviter 6 mois de développement à perte = **>500k€** économisés.

---

## Ce qu'on fait après

- **Semaines 7-8** : synthèse, ateliers décision, mise à jour roadmap
- **Q2 2026** : développement V1 informé par la validation
- **Continu** : maintenir 5 interviews clients / mois après le launch (continuous discovery)

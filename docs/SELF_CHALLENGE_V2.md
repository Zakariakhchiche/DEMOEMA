# SELF-CHALLENGE V2 — Audit post-V3 (propagation incomplète)

> **Tour 8 de revue critique. Date : 2026-04-17 après-midi.**
>
> Ce document fait suite à `SELF_CHALLENGE.md` (V1, 131 questions). L'agent a produit une V3 majeure (`REPONSES_SELF_CHALLENGE`, `FINANCES_UNIFIE`, `MODELE_FINANCIER`, `PLAN_DEMARRAGE_Q2-Q4_2026`) qui adresse **la majorité des 🔴 bloquantes de V1**.
>
> **Mais la propagation des corrections n'est qu'à ~60%.** Plusieurs docs n'ont pas été regénérés avec les nouveaux chiffres. Résultat : contradictions internes visibles en 10 min à un VC.
>
> **Objectif de ce doc** : lister les 19 points résiduels (Q133-Q151) avec le fichier à corriger pour chacun. C'est une **to-do list mécanique**, pas un re-challenge stratégique.

---

## Table des matières

- [✅ Wins reconnus de la V3](#wins-v3)
- [🔴 Partie A — Propagation non terminée](#partie-a-propagation)
- [🔴 Partie B — Fichiers référencés inexistants](#partie-b-fichiers-fantômes)
- [🔴 Partie C — Modèle financier non décalé](#partie-c-modele)
- [🟠 Partie D — Incohérences numériques internes](#partie-d-incoherences)
- [🟠 Partie E — Hypothèses économiques à creuser](#partie-e-economique)
- [🟡 Partie F — Ouvertures](#partie-f-ouvertures)
- [📌 Checklist d'action mécanique](#checklist)

---

<a id="wins-v3"></a>

## ✅ WINS RECONNUS DE LA V3 (à ne pas défaire)

| Sujet | État V1/V2 | État V3 |
|---|---|---|
| Déni temporel | Plan Q1 au futur alors que Q1 fini | "RIEN n'est fait" assumé, plan décalé +3 mois |
| Existant V1 | Non documenté | Démo Vercel, 0 client, 0 revenu, 0 source branchée |
| Discovery client | 0 mentionné | 2 interviews, démo a plu, thèse Pappers légitimée |
| Cap table | 102-122% | 100% exact (founder 45.8% post-pool) |
| ARR vs Revenue total | Confondus | Distinction rigoureuse |
| BvD = Moody's | Ignoré 2 fois | 8 acquéreurs réels listés |
| Pappers IA / Société.com IA / Harvey $300M | Faux | Corrigés |
| INPI RBE / Trustpilot / Google Reviews | Maintenus | Retirés (140 sources actives) |
| Fine-tuning Mistral | Prévu Y2 | Abandonné (simplifie AI Act) |
| DPO budget | 30k€ vs 5-15k€/mois contradictoire | 60k€/an figé |
| Source unique de vérité chiffrée | Inexistante | `FINANCES_UNIFIE.md` |

**Ces acquis doivent survivre à la passe de propagation.**

---

<a id="partie-a-propagation"></a>

## 🔴 PARTIE A — PROPAGATION NON TERMINÉE

> Plusieurs docs V3 n'ont pas été regénérés avec les nouveaux chiffres de `FINANCES_UNIFIE.md`.

### Q133 (🔴) — `DECISIONS_VALIDEES.md` contient encore les anciens chiffres V2

**Fichier à corriger** : `DECISIONS_VALIDEES.md`

**Contradictions :**
- Ligne 80 : "Y1 2026 | 525k€ | 50-100k€ | 700k€ pré-amorçage Q1"
  - FINANCES_UNIFIE : 600k€ coûts / 80k€ ARR / 600k€ pré-amorçage **fin juin 2026**
- Ligne 93 : "Fondateurs 50-55%" (post-Series A)
  - FINANCES_UNIFIE §5 : 45.8% post-pool dilué
- Ligne 121 : "Pré-amorçage Closing avant fin Q1 2026"
  - Q1 est fini, closing = fin juin
- Ligne 138 §Q1 : "30 interviews, 5 LOI, 700k€ pré-amorçage" présenté comme Q1 2026
  - Tout décalé en Q2-Q4 2026
- Ligne 184 : "Prochain livrable : `PLAN_EXECUTION_Q1_2026.md`"
  - Fichier renommé en `PLAN_DEMARRAGE_Q2-Q4_2026.md`

**Action** : regénérer intégralement `DECISIONS_VALIDEES.md` en citant `FINANCES_UNIFIE.md` comme référence unique.

### Q134 (🔴) — `BUDGET_EQUIPE.md` non mis à jour

**Fichier à corriger** : `BUDGET_EQUIPE.md`

**Contradictions :**
- Dit Y1 coûts = 525k€
- FINANCES_UNIFIE dit Y1 coûts = 600k€
- MODELE_FINANCIER dit Y1 coûts = 578k€

**3 chiffres différents sur un même poste**, dans trois docs censés tous dire la même chose.

**Action** : réécrire `BUDGET_EQUIPE.md` pour renvoyer explicitement à `FINANCES_UNIFIE.md` (pattern "cf. FINANCES_UNIFIE §X") plutôt que dupliquer les tableaux.

### Q135 (🔴) — `PRICING.md` toujours en V1

**Fichier à corriger** : `PRICING.md`

**Contradictions :**
- Y4 ARR annoncé 15-25M€ → FINANCES_UNIFIE dit 8-15M€
- Prix Pro "199€/mois" figé → FINANCES_UNIFIE §6 : "à benchmarker en priorité, fourchette 199-299€"
- Pay-per-report "Buyer list 2990€" figé → FINANCES_UNIFIE : "fourchettes à confirmer après interviews"
- Stratégie Free "10 fiches/mois" → toujours non argumentée vs Pappers 5M pages indexables

**Action** : reframer `PRICING.md` en "**Hypothèses pricing à valider** (benchmark interviews Q2 2026)". Remplacer les prix fixes par des fourchettes. Ajouter une section "À confirmer : combien payent les 2 boutiques M&A pour Pappers ?".

### Q136 (🔴) — `CONCURRENCE.md` corrigé en surface mais pas en fond

**Fichier à corriger** : `CONCURRENCE.md`

**Contradictions internes au doc :**
- Ligne 11 (tableau) : "Pappers IA depuis 2024" ✅ corrigé
- Ligne 33-38 (analyse détaillée) : "pas d'IA générative" ❌ non corrigé
- Ligne 43 : "Copilot LLM (Pappers ne fait pas)" ❌ (Pappers IA fait du copilot)
- Ligne 160-162 : TAM/SAM/SOM 500M€/150M€/15M€ toujours non sourcés
- ARPU TAM 10k€/an ≠ ARPU PRICING mix ≈ 3-4k€/an → TAM devrait être ~200M€ pas 500M€

**Action** :
1. Refaire l'analyse détaillée §Pappers ligne 24-47 cohérente avec "Pappers IA" existe
2. Sourcer TAM/SAM/SOM (Gartner, IDC, ou calcul explicite)
3. Recalculer SAM/SOM avec l'ARPU réel du pricing proposé

---

<a id="partie-b-fichiers-fantômes"></a>

## 🔴 PARTIE B — FICHIERS RÉFÉRENCÉS INEXISTANTS

### Q137 (🔴) — `KIT_ACTION_30JOURS.md` manquant

**Fichiers qui le référencent :**
- `README.md` ligne 45
- `README.md` ligne 103
- `PLAN_DEMARRAGE_Q2-Q4_2026.md` ligne 55

**3 dead links.** Ce sont les premiers endroits où un VC cliquerait.

**Action** : créer `KIT_ACTION_30JOURS.md` avec :
- Template email re-contact boutique M&A (personnalisé thèse Pappers)
- Template LinkedIn InMail 50 prospects
- Script interview 45 min (extrait de `VALIDATION_MARCHE.md`)
- Template LOI client (bêta-testeur premium 6 mois gratuit)
- Template email intro investisseur BA / VC seed
- Checklist setup outillage (Linear, Notion, Calendly, Otter, comptes APIs)
- Demande de rendez-vous BPI (trame)

### Q138 (🔴) — `ETAT_REEL_2026-04-17.md` promis, pas créé

**Fichier qui le promet** : `REPONSES_SELF_CHALLENGE.md` ligne 41
> "Action immédiate : créer `ETAT_REEL_2026-04-17.md`"

**Action** : créer un doc court (1 page) qui formalise l'état zéro :
- Site Vercel accessible
- 0 client, 0 revenu, 0 LOI
- 25 sources listées, 0 branchée
- 1 founder, 0 hire, 0 freelance actif
- 0 cash levé, 0 DPO, 0 RGPD compliance
- Prototype front = socle à conserver
- 2 boutiques M&A interlocutrices + réseau personnel

Ce doc devient la **baseline de comparaison** pour le bilan fin décembre 2026.

---

<a id="partie-c-modele"></a>

## 🔴 PARTIE C — MODÈLE FINANCIER NON DÉCALÉ DANS LE TEMPS

### Q139 (🔴) — CSV et tableaux mensuels utilisent M1 = janvier 2026

**Fichier à corriger** : `MODELE_FINANCIER.md` + `modele_financier.csv`

**Problème** :
- Ligne 41 : "Pré-amorçage M3 (mars 26) +400k€"
- Ligne 133 : "M4 (avril 2026) Lead Data Eng arrive"
- Ligne 139 : "M10 (octobre 2026) ML Engineer"

**Réalité** : on est le 17 avril 2026. M3 (mars) est passé **sans aucune levée**. M4 (avril) ne voit aucun Lead Data Eng.

**Conséquence** : le cash-flow affiche des injections fictives. Un VC qui ouvre le CSV voit un modèle basé sur un calendrier qui ne correspond pas à la réalité.

**Action** : décaler **tous les mois de +3**. M1 devient avril 2026 (pas janvier). Pré-amorçage = M3 du nouveau calendrier = juin 2026. Lead Data = M4 = juillet 2026. ML = M10 = janvier 2027 (cohérent avec "ML décalé Y2 Q1 2027" de REPONSES).

### Q140 (🔴) — Montant pré-amorçage : 4 chiffres différents

**Fichiers concernés** : FINANCES_UNIFIE, MODELE_FINANCIER, DECISIONS_VALIDEES, REPONSES_SELF_CHALLENGE

| Doc | Chiffre |
|---|---|
| `FINANCES_UNIFIE.md` | **600 k€** |
| `MODELE_FINANCIER.md` ligne 41 | **400 k€** |
| `MODELE_FINANCIER.md` ligne 178 | **+400 k€** |
| `DECISIONS_VALIDEES.md` | **700 k€** |
| `REPONSES_SELF_CHALLENGE.md` | **600 k€** |

**Action** : trancher **une** valeur (recommandation : 600 k€ selon FINANCES_UNIFIE), la mettre partout, supprimer les autres.

### Q141 (🔴) — Y1 coûts : 3 chiffres différents dans la source unique de vérité

**Fichiers concernés** : FINANCES_UNIFIE, MODELE_FINANCIER

| Emplacement | Y1 coûts |
|---|---|
| FINANCES_UNIFIE §Tableau consolidé (ligne 56) | **600 k€** |
| FINANCES_UNIFIE §7 checks ligne 201 | "~600 k€" ✓ |
| MODELE_FINANCIER §Synthèse annuelle ligne 71 | **578 k€** |
| MODELE_FINANCIER §Synthèse trimestrielle ligne 102 | **603 k€** |

**Écart ~25 k€** dans une "source unique de vérité". Discrédite tout.

**Action** : passer le modèle financier mois par mois, recalculer le total annuel, et aligner **les 4 emplacements** sur un seul chiffre.

### Q142 (🔴) — Dilution pré-amorçage : écart ×2

**Fichiers concernés** : REPONSES_SELF_CHALLENGE, FINANCES_UNIFIE

- REPONSES ligne 78 : "Valorisation pre-money cible 3-4M€ → dilution 13-17%"
- FINANCES_UNIFIE §5 ligne 149 : "Pré-amorçage 8% @ 7M€ post-money"

**Math :**
- 600 k€ / 3 M€ post = 20%
- 600 k€ / 7 M€ post = 8.5%

**Écart × 2 sur la dilution du fondateur au premier tour.** Critique : Un VC seed ne comprendra pas.

**Action** : trancher la valo pré-money (probablement 3-4 M€ post-money = dilution 15-17% pour une pré-amorçage à ce stade — pas 8%).

---

<a id="partie-d-incoherences"></a>

## 🟠 PARTIE D — INCOHÉRENCES ÉCONOMIQUES RESTANTES

### Q143 (🟠) — Founder bootstrap avril-juin sans salaire ni cash

- Founder passe à 60 k€/an chargé en M14 (février 2027 — nouveau calendrier)
- Du 17 avril (maintenant) à juin (closing pré-amorçage) = 10 semaines sans revenue ni cash entrant
- REPONSES dit vaguement "personal money / advance founders"
- **Montant personnel disponible ? Durée tenable ? Limite au-delà de laquelle bridge dette personnelle ?**

**Action** : ajouter une section dans `ETAT_REEL_2026-04-17.md` qui documente la capacité bootstrap founder (ex: "capacité 20k€ personnel sur 4 mois max").

### Q144 (🟠) — Timing LOI investisseur → closing en ~4 semaines

`PLAN_DEMARRAGE_Q2-Q4_2026.md` §Juin dit : "15 pitchs → 3 LOI → term sheet → closing 600 k€" en 4-5 semaines.

**Standard pré-amorçage BPI + BA :**
- Due diligence investisseur : 2-3 semaines
- Négociation term sheet + pacte d'associés : 1-2 semaines
- Modification statuts + KBIS : 2-3 semaines
- Virement effectif : 1 semaine
- **Total : 6-9 semaines minimum**

**Action** : étaler le closing sur juin + début juillet. Assumer que Lead Data Eng ne peut pas démarrer avant fin juillet. Revoir le cash flow en conséquence.

### Q145 (🟠) — Pricing figé dans le modèle sans benchmark

- FINANCES_UNIFIE §6 : "à benchmarker en priorité après interviews"
- MODELE_FINANCIER hypothèses : Starter 49€, Pro 199€, Enterprise 25 k€ **figés**

Si benchmark boutiques révèle Pappers payé 20€/user/mois → Starter 49€ inaccessible → **écroulement total du modèle financier**.

**Action** : produire **3 scénarios** financiers (pricing bas / médian / haut) et voir si le modèle reste viable dans les 3 cas. Sinon identifier quel pricing minimal est nécessaire.

### Q146 (🟠) — 2 interviews = biais réseau non contrôlé

- REPONSES : "2 boutiques ont vu la démo, ont aimé"
- Ces 2 sont-elles du réseau personnel ? Amis ? Anciens collègues ?
- Biais Mom Test : "ils voulaient être sympas"

**Action** : dans le PLAN_DEMARRAGE, les 28 interviews suivantes doivent inclure **≥15 prospects non-réseau** (sourcing froid LinkedIn / annuaires). Et tagger chaque interview "réseau" vs "froid" pour mesurer le signal.

### Q147 (🟠) — Thèse "affranchissement Pappers" = généralisable ?

Founder a utilisé Pappers → cher + lock-in → veut construire. **Sa thèse personnelle vécue.**

Pour être une thèse marché : les 198 autres boutiques M&A paient-elles Pappers aussi et s'en plaignent-elles ?

**Action** : dans les 30 interviews, question obligatoire : "Quel outil data utilises-tu aujourd'hui ? Combien ça coûte ? T'en plains-tu ? Si on te propose −30% à qualité équivalente, tu bouges ?"

### Q148 (🟠) — CONCURRENCE TAM/SAM/SOM non recalculé post-pricing

- TAM 500M€ = 50k users × 10k€/an
- Mais ARPU mix du PRICING ≈ 3-4k€/an (Starter+Pro dominent) pas 10k€
- **TAM réel à ce pricing = ~200M€**, pas 500M€
- SAM / SOM à recalculer en conséquence

**Action** : `CONCURRENCE.md` §Marché cible à réécrire. Ou sourcer un TAM 500M€ (Gartner M&A intel software) crédible qui justifie 10k€ ARPU moyen (= full Enterprise).

---

<a id="partie-e-economique"></a>

## 🟠 PARTIE E — POINTS À CREUSER AVANT CLOSING PRÉ-AMORÇAGE

### Q149 (🟠) — Éviter le biais des 2 boutiques interlocutrices

Comment éprouver la demande au-delà des 2 prospects actuels ?

**Action** : interviewer **séparément** un associé ET un analyste junior de chaque boutique. Si les deux niveaux ont le même pain et la même disposition à payer → signal fort. Sinon biais de leadership.

### Q150 (🟠) — ML Engineer : Y1 M10 ou Y2 Q1 ?

- MODELE_FINANCIER ligne 139 : ML Engineer M10 (200k€/an)
- FINANCES_UNIFIE §Recrutements : décalé Y2 Q1 2027
- REPONSES : décalé Y2 Q1 2027

**Impact Y1 coûts** : avec ML M10 (décembre 2026 nouveau calendrier) = +50 k€ Y1 / sans = économie 50 k€.

**Action** : trancher. Si 600 k€ levés au pré-amorçage + ML décalé Y2 → Y1 coûts = 550 k€ → runway plus long. Option préférable.

### Q151 (🟠) — Audit CGU sources : 140 actives, combien juridiquement fragiles ?

`VALIDATION_API.md` prévoit audit CGU en Q2 (semaine S1-S2 selon PLAN_DEMARRAGE). Mais combien d'autres pièges similaires à INPI RBE (cassé CJUE) / Trustpilot (CGU) sont encore dans la liste des 140 ?

**Action** : prioriser l'audit CGU sur les 20 sources top + sur les 30 sources les plus atypiques (réseaux sociaux, scraping, registres étrangers, données individuelles). Total 50 sources auditées en profondeur.

---

<a id="partie-f-ouvertures"></a>

## 🟡 PARTIE F — OUVERTURES

- **Architecture Y3-Y4** : quand on passe à ClickHouse + Neo4j, qui opère ? DevOps/SRE à embaucher Y3 mais seul : bus factor = 1 sur l'infra data. Prévoir redondance.
- **IA Act 2026-2027** : le calendrier d'application bouge. Ajouter un flag de monitoring dans le doc AI_ACT.
- **Pricing Y2 evolution +10-15%** : politique de grandfathering clients pré-existants non documentée. Risque churn.
- **SEO vs Pappers** : stratégie "Free 10 fiches/mois" ne bat pas 5M pages indexées Pappers. Plan SEO séparé à produire Y2.

---

<a id="checklist"></a>

## 📌 CHECKLIST D'ACTION MÉCANIQUE (ordre suggéré)

### Jour 1 — propagation chiffres (1-2 h)

- [ ] Trancher montant pré-amorçage (**600 k€** recommandé)
- [ ] Trancher ML Engineer timing (**Y2 Q1 2027** recommandé)
- [ ] Trancher dilution pré-amorçage (**15-17%** recommandé, réaliste BA)
- [ ] Regénérer `DECISIONS_VALIDEES.md` → renvoyer à `FINANCES_UNIFIE`
- [ ] Réécrire `BUDGET_EQUIPE.md` → renvoyer à `FINANCES_UNIFIE`
- [ ] Reframer `PRICING.md` comme "hypothèses à benchmarker"
- [ ] Corriger analyse Pappers détaillée dans `CONCURRENCE.md`
- [ ] Recalculer TAM/SAM/SOM de `CONCURRENCE.md`

### Jour 2 — décalage temporel modèle (1-2 h)

- [ ] Décaler tous les mois M1→M36 de +3 dans `MODELE_FINANCIER.md`
- [ ] Regénérer le CSV `modele_financier.csv`
- [ ] Aligner les 4 emplacements du Y1 coûts sur un seul chiffre
- [ ] Vérifier cash flow mensuel cohérent avec nouveau calendrier

### Jour 3 — fichiers manquants (2-3 h)

- [ ] Créer `KIT_ACTION_30JOURS.md` (templates)
- [ ] Créer `ETAT_REEL_2026-04-17.md` (baseline)
- [ ] Ajouter section "capacité bootstrap founder" dans ETAT_REEL

### Jour 4 — robustesse modèle (3-4 h)

- [ ] Produire 3 scénarios pricing (bas/médian/haut)
- [ ] Documenter politique grandfathering Y2
- [ ] Prioriser audit CGU 50 sources à risque
- [ ] Flag monitoring IA Act dans `AI_ACT_COMPLIANCE.md`

### Livrable final

- [ ] Mettre à jour CHANGELOG README V3 → V3.1 avec les corrections propagation
- [ ] Toutes les contradictions Q133-Q151 résolues
- [ ] Aucun dead link dans les docs

---

## Pourquoi cette phase est critique

L'agent doc a fait un **saut qualitatif majeur** avec la V3. Mais si la propagation n'est pas terminée, le sponsor présente à son board/VC une suite de docs qui se contredisent.

**Règle** : un doc incohérent avec un autre = doc perdu. Mieux vaut **10 docs propres que 15 docs contradictoires.**

Après la passe de propagation, le projet est prêt pour :
1. Re-contacter les 2 boutiques (KIT_ACTION_30JOURS)
2. Démarrer les 30 interviews (VALIDATION_MARCHE)
3. Préparer le deck pré-amorçage (600 k€, juin)

**Puis stop la production doc et passer au terrain.**

---

_Document généré le 2026-04-17. 19 questions (Q133-Q151) à résoudre avant de produire de nouvelles docs._

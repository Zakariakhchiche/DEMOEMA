# PRODUCT GAPS — Retour persona cible (Pierre, associé M&A)

> **Source** : simulation role-play par auditeur externe le 2026-04-17. Un associé M&A mid-market fictif (Pierre, 47 ans, boutique 12 pers., 15 deals/an) a évalué la proposition actuelle de DEMOEMA et identifié **6 pains non résolus** + **10 features manquantes**.
>
> **Objectif de ce doc** : donner à l'agent produit une liste actionnable de features à intégrer dans la roadmap Y1-Y3 pour que le produit matche le vrai pain du persona cible.
>
> **Warning** : sans ces ajustements, le pricing 199€/Pro sera **difficile à défendre** (Pierre paye déjà Pappers 50€ + LinkedIn 80€ + Infogreffe 100€ et notre produit **s'ajouterait** au lieu de remplacer).

---

## 🎯 Repositionnement du value prop (le plus important)

### Avant (positionnement actuel)

> "Plateforme d'intelligence M&A alimentée par 140 sources gratuites."

**Problème** : le persona se fiche du nombre de sources. Ce n'est pas le pain.

### Après (positionnement proposé)

> **"Le premier outil qui connecte un associé M&A avec le bon décisionnaire au bon moment."**

Ou variante plus opérationnelle :
> **"Vous perdez 3h/jour sur des cibles mortes. DEMOEMA élimine 60% du bruit et vous dit qui appeler en premier."**

**Justification** : Pierre ne cherche pas "plus de data". Il cherche **moins de bruit + meilleurs contacts**. C'est mesurable, testable, vendable.

### Impact documents

- [ ] `README.md` §Vision → réécrire
- [ ] `CONCURRENCE.md` §Positionnement final → réécrire
- [ ] `PITCH_DECK.md` Slide 1 tagline + Slide 3 Solution → réécrire

---

## 🔴 PAINS NON RÉSOLUS (reconnaissance à ajouter dans la doc)

### Pain #1 — Accès au décisionnaire (pas à la donnée)

**Verbatim Pierre** :
> "Je ne cherche pas plus de data sur une boîte. Je cherche **l'email et le tel portable du dirigeant** pour lui passer un coup de fil. Tes sources publiques ne me le donnent pas."

**Constat** : les 140 sources publiques ne fournissent **jamais** les coordonnées directes (email perso, mobile). LinkedIn est exclu du scope par AI Act + CGU.

### Pain #2 — Comptes non déposés (50% des PME)

**Verbatim** :
> "La moitié de mes cibles sont des SARL familiales qui ne déposent pas leurs comptes au greffe. Ton INPI ne me sert à rien pour elles."

### Pain #3 — Valorisations / multiples sectoriels

**Verbatim** :
> "Pour pricer un deal je paie Capital IQ 15k€/an parce qu'ils ont les **multiples EBITDA récents par secteur**. Tes sources publiques ne donnent pas ça."

### Pain #4 — Historique advisors (qui conseille qui)

**Verbatim** :
> "Quand je vois une cible, je veux savoir **qui l'a conseillée sur son dernier deal** pour pouvoir appeler le banquier et demander une intro. C'est 80% de mon sourcing."

### Pain #5 — Intégration CRM deal

**Verbatim** :
> "Si ton outil ne se branche pas à mon Affinity / Dealcloud / HubSpot, je vais devoir ressaisir à la main. Adoption = 0%."

### Pain #6 — Responsabilité IA en cas d'erreur

**Verbatim** :
> "Si ton copilot hallucine et me fait recommander une mauvaise cible à mon client, qui prend la poursuite ? Moi ou toi ?"

---

## ✅ 10 FEATURES À AJOUTER À LA ROADMAP

### Feature #1 — ⭐ "Who advises whom" (killer feature proposée)

**Description** : base de données historique des M&A advisors, scrapée depuis sources publiques (CFNews RSS, Mergermarket public feed, presse spécialisée, communiqués de presse boursiers).

**Pour chaque deal historique** :
- Cible + acquéreur
- Valorisation annoncée (si publique)
- **Advisors côté vendeur** (boutique M&A, banque d'affaires)
- **Advisors côté acquéreur**
- Date deal

**Value** : quand Pierre regarde une cible, il voit immédiatement "Société X a été conseillée par Cabinet Y en 2023" → il appelle Cabinet Y pour une intro.

**Implémentation** :
- Sources : **source 123 CFNews RSS** (déjà dans `ARCHITECTURE_DATA_V2`) + scraping presse éco (Les Échos, La Tribune, Usine Nouvelle)
- Parsing NLP : extraction nommée de deals (cible, acquéreur, conseillers)
- **Coût data = 0€** (sources déjà listées)
- **Effort tech** : modèle CamemBERT fine-tuné sur 500 communiqués labellisés → 4-6 semaines de dev

**Priorité** : 🔴 **Y1 Q4 2026** (killer feature pour pitch + conversion Pro)

**Impact doc** :
- [ ] Ajouter dans `ROADMAP_4ANS.md` Y1 Q4
- [ ] Créer fiche produit dédiée

---

### Feature #2 — "Alerte intention de cession" (2ème killer feature)

**Description** : détection de signaux faibles pré-cession via signaux publics **pertinents au M&A** (pas Certificate Transparency qui est du tech).

**Signaux monitorés** :
- Changement de mandataires sociaux (BODACC) → 30-50% prédictif de cession sous 18 mois
- Nouvelles délégations en AG (InfoGreffe) → préparation gouvernance
- Nomination d'un **directeur financier externe** à 55+ ans sans successeur → préparation transmission
- Mandats croisés : dirigeant qui rejoint un fonds PE (signal pré-deal)
- Recrutement d'un Deputy CEO / COO après 2 ans de stabilité

**Value** : Pierre reçoit une alerte hebdo ciblée "3 entreprises de ton secteur montrent des signaux pré-cession cette semaine".

**Implémentation** :
- Sources existantes : BODACC (#30), INPI RNE (#4), annonces AG (scrapable)
- Scoring rules-based (pas besoin de ML complexe)
- **Effort** : 3-4 semaines

**Priorité** : 🔴 **Y1 Q3 2026** (différenciation vs Pappers qui fait du lookup statique)

**Impact doc** :
- [ ] Ajouter dans `ROADMAP_4ANS.md` Y1 Q3
- [ ] Remplacer dans le pitch deck Slide 3 "Score trajectoire IA" par "Alertes intention cession"

---

### Feature #3 — Enrichissement contact (intégration Apollo/Lusha)

**Description** : pour chaque dirigeant affiché dans la fiche, proposer email + tel portable via **API Apollo ou Lusha**.

**Modèle économique** : add-on payant (5-10€/contact débloqué) ou inclus dans Enterprise.

**Questions légales** :
- Apollo/Lusha opèrent sous US law → vérifier conformité RGPD européen
- Alternative FR : **Kaspr** (acteur FR, mieux RGPD)
- Opt-in obligatoire du contact (consentement ou intérêt légitime documenté)

**Priorité** : 🟠 **Y2 Q1 2027** (après validation produit Y1)

**Impact doc** :
- [ ] Ajouter dans `ARCHITECTURE_DATA_V2.md` comme "source payante optionnelle"
- [ ] `PRICING.md` ajouter add-on "Contact enrichment : 5€/contact débloqué"
- [ ] `AI_ACT_COMPLIANCE.md` + `RISQUES_CONFORMITE.md` DPIA spécifique

---

### Feature #4 — Multiples sectoriels EBITDA (base open + enrichie)

**Description** : base de multiples EBITDA récents par secteur NAF / taille entreprise, construite depuis sources publiques.

**Sources utilisables** :
- **BODACC transactions** : montants parfois publiés (fusions/acquisitions) → 15-20% des deals
- **ESANE INSEE** : ratios sectoriels agrégés (pas par entreprise mais par secteur)
- **Banque de France Centrale des Bilans** : marges + endettement sectoriels
- **CFNews** : deals publiés avec valorisation

**Implémentation** :
- Agrégation rolling 24 mois
- Affichage médiane + fourchette P25-P75 par secteur × taille
- **Disclaimer** : indicatif, pas engageant

**Priorité** : 🟠 **Y2 Q2 2027**

**Impact doc** :
- [ ] Ajouter dans `ROADMAP_4ANS.md` Y2
- [ ] Créer dataset `multiples_sectoriels` dans `ARCHITECTURE_TECHNIQUE.md`

---

### Feature #5 — Partenariat Société.com / Ellisphere (comptes PME)

**Description** : pour les 50% de PME qui ne déposent pas au greffe, partenariat avec un acteur data crédit pour **estimations qualifiées** (pas scraping).

**Options** :
1. **Ellisphere** : filiale BNP, data crédit FR, API payante (~5-15k€/an)
2. **Altares** (D&B France) : idem
3. **Creditsafe** : moins cher, couverture acceptable

**Économie proposée** :
- Option A : intégration Enterprise only (inclus dans 15-25k€/an)
- Option B : add-on 50€/mois/user pour Pro

**Priorité** : 🟠 **Y2 Q3 2027**

**Impact doc** :
- [ ] Revoir `ARCHITECTURE_DATA_V2.md` — la catégorie "sources gratuites" n'est plus 100% exacte
- [ ] `PRICING.md` ajouter add-on
- [ ] `CONCURRENCE.md` ajuster positionnement (pas 100% gratuit à la source mais 100% propre juridiquement)

---

### Feature #6 — Extension Chrome / LinkedIn enrichment

**Description** : extension navigateur qui enrichit les pages LinkedIn + sites d'entreprises en temps réel avec les données DEMOEMA.

**Value** : Pierre ne change pas son workflow. Il continue à browser LinkedIn et voit les infos DEMOEMA en overlay.

**Implémentation** :
- Chrome extension basique (~4-6 semaines)
- API DEMOEMA `/enrich?linkedin_url=...`
- **Note légale** : l'extension ne scrape pas LinkedIn, elle enrichit uniquement l'URL visitée par l'user

**Priorité** : 🟠 **Y2 Q1 2027**

**Impact doc** :
- [ ] Ajouter dans `ROADMAP_4ANS.md` Y2
- [ ] `PITCH_DECK.md` Slide 6 — ajouter screenshot extension comme 4ème use case

---

### Feature #7 — Intégration CRM dealflow (Affinity / Dealcloud / HubSpot)

**Description** : connecteur natif vers les 3 CRM M&A principaux.

**Note critique** : la roadmap actuelle prévoit ça en **Y3**. **Le persona dit "Y1 ou je passe"**. À avancer.

**Priorité minimale** :
- **Y1 Q4 2026** : export CSV/Excel compatible Affinity (colonnes standards) — 1 semaine de dev
- **Y2 Q2 2027** : API bidirectionnelle officielle Affinity — 4-6 semaines

**Impact doc** :
- [ ] Modifier `ROADMAP_4ANS.md` — avancer CRM integration de Y3 → Y1/Y2
- [ ] `PITCH_DECK.md` Slide 10 Roadmap ajouter "intégration Affinity Q4 2026"

---

### Feature #8 — Export Excel natif avec templates

**Description** : export Excel/Google Sheets avec templates M&A standard :
- Template "Teaser target"
- Template "Buyer list"
- Template "Longlist secteur"
- Template "Cible DD brief"

**Value** : Pierre utilise déjà des templates Excel. Il veut un bouton "Exporter en [mon template]".

**Effort** : 2-3 semaines (API openpyxl ou équivalent)

**Priorité** : 🟡 **Y1 Q3 2026**

**Impact doc** :
- [ ] `ROADMAP_4ANS.md` Y1 Q3

---

### Feature #9 — Clause de responsabilité IA claire

**Description** : CGU + produit clarifient sans ambiguïté :
1. Le copilot IA est **aide à la décision**, pas décision
2. L'utilisateur reste **seul responsable** de l'usage professionnel
3. **Transparence des sources** : chaque affirmation du copilot est sourcée (lien vers la donnée d'origine)
4. **Audit log** : les réponses IA sont loguées pour contestation future
5. **Mode "sans IA"** possible (bouton pour désactiver le copilot)

**Note légale** : cela simplifie AI Act et protège le user (art. 14 "surveillance humaine").

**Priorité** : 🔴 **Y1 Q3 2026** (avant lancement Pro)

**Impact doc** :
- [ ] `AI_ACT_COMPLIANCE.md` — ajouter section "Transparence sources + mode sans IA"
- [ ] CGU à rédiger par avocat

---

### Feature #10 — Social proof (pré-launch)

**Description** : avant le pitch investisseur, obtenir :
- 2-3 logos de boutiques M&A reconnues visibles sur le site (avec accord)
- 1 case study documenté : "Boutique X a trouvé deal Y en Z semaines grâce à DEMOEMA"
- Advisor board visible : 3 noms avec leur ancien titre (ex: "Jean Dupont, ex-partner Lazard")
- **2 LOI signées** visibles (même bêta gratuit)

**Priorité** : 🔴 **Q2 2026 (immédiat)**

**Impact doc** :
- [ ] `PLAN_DEMARRAGE_Q2-Q4_2026.md` — ajouter tâche "Obtenir 3 logos + case study + advisor board visible" avant pitch
- [ ] `PITCH_DECK.md` Slide 11 Team + Slide 9 Traction

---

## 📋 MATRICE PRIORITÉ × EFFORT

| Feature | Impact persona | Effort tech | Priorité | Quand |
|---|---|---|---|---|
| #1 "Who advises whom" | 🔴🔴🔴 | Medium (4-6 sem NLP) | ⭐ KILLER | **Y1 Q4 2026** |
| #2 Alertes intention cession | 🔴🔴🔴 | Low (3-4 sem rules) | ⭐ KILLER | **Y1 Q3 2026** |
| #9 Clause responsabilité IA | 🔴🔴 | Low (1-2 sem) | 🔴 Obligatoire | Y1 Q3 2026 |
| #10 Social proof | 🔴🔴🔴 | Low (opérationnel) | 🔴 Obligatoire | **Q2 2026 immédiat** |
| #7 Export Excel + CRM base | 🔴🔴 | Low (1-2 sem) | 🔴 Avancer | Y1 Q4 2026 |
| #8 Export Excel templates | 🔴 | Low (2-3 sem) | 🟡 | Y1 Q3 2026 |
| #3 Contact enrichment | 🔴🔴 | Medium (API + RGPD) | 🟠 | Y2 Q1 2027 |
| #6 Extension Chrome | 🔴 | Medium (4-6 sem) | 🟠 | Y2 Q1 2027 |
| #4 Multiples EBITDA | 🔴🔴 | High (agrégation) | 🟠 | Y2 Q2 2027 |
| #5 Partenariat data crédit | 🔴🔴 | Low (API partenariat) | 🟠 | Y2 Q3 2027 |

---

## 💰 IMPACT SUR LE PRICING ET LE MODÈLE

### Repositionnement à considérer

**Si on ajoute ces features Y1-Y2**, le pricing actuel 199€/Pro devient **défendable** :

| Feature | Impact Pro value | Price support |
|---|---|---|
| "Who advises whom" | +70€/mois valeur perçue | Justifie 199€ |
| Alertes intention cession | +50€/mois | Justifie 199€ |
| Export CRM + Excel templates | +30€/mois | Remplace Excel manual |
| **Total uplift** | **+150€/mois** | **199€ legit** |

### Add-ons payants (nouveau revenue)

| Add-on | Prix | Cible |
|---|---|---|
| Contact enrichment | 5€/contact | Starter + Pro |
| Comptes PME enrichis (Ellisphere) | +50€/mois | Pro |
| Multiples EBITDA database | +100€/mois | Pro + Enterprise |
| Extension Chrome | Gratuit | Acquisition |

Revenue Y2+ potentiellement **+15-25%** avec ces add-ons si adoption 30% users.

---

## 🧭 RECOMMANDATION GLOBALE À L'AGENT PRODUIT

### Action #1 — Repositionner le value prop (immédiat, 1h)

Avant tout autre ajout, **reécrire** les 3 endroits :
- `README.md` §Vision
- `CONCURRENCE.md` §Positionnement final
- `PITCH_DECK.md` Slide 1 + Slide 3

De "140 sources gratuites" → "connecter l'associé M&A au bon décisionnaire".

### Action #2 — Confirmer ou invalider avec les 30 interviews

Dans les 30 interviews prévues Q2 2026, **poser obligatoirement ces 3 questions** :
1. "La dernière fois que vous avez raté une cible, qu'est-ce qui vous a manqué ?"
2. "Comment trouvez-vous actuellement qui a conseillé une boîte sur son dernier deal ?"
3. "Combien payeriez-vous pour une alerte qui vous dit 'cette boîte montre des signaux pré-cession' ?"

Si les réponses matchent les pains #1, #4, #2 → **les 2 killer features (Feature #1 et #2) sont validées**.

Si les réponses diffèrent → **re-pivoter le produit** avant de coder.

### Action #3 — Mettre à jour la roadmap

- **Y1 Q3 2026** : Feature #2 (alertes cession) + #8 (Excel templates) + #9 (responsabilité IA)
- **Y1 Q4 2026** : Feature #1 (who advises whom) + #7 (export CRM base)
- **Y2 Q1 2027** : Feature #3 (contact) + #6 (Chrome) + #7 API Affinity
- **Y2 Q2-Q3 2027** : Feature #4 (multiples) + #5 (Ellisphere)
- **Q2 2026 immédiat** : Feature #10 (social proof) via campagne commerciale

### Action #4 — Ajuster le pitch deck

- **Slide 3 Solution** : remplacer "Score trajectoire IA" (que Pierre n'achète pas) par "Who advises whom + Alerte intention cession"
- **Slide 8 Concurrence** : ajouter "Pappers fait du lookup, Clay/Apollo font de l'email B2B, Capital IQ fait des multiples → **personne ne fait les 3 ensemble**"

---

## ⚠️ RAPPEL IMPORTANT

Ces features sont **proposées sur la base d'une simulation**, pas d'interviews réelles.

**Avant de figer la roadmap**, l'agent produit doit :
1. Lancer les 30 interviews (cf. `VALIDATION_MARCHE.md`)
2. **Tester verbatim** les features #1 et #2 auprès des 30 prospects
3. Mesurer willingness to pay concrète (pas intention, paiement acompte / LOI)
4. Arbitrer feature par feature selon retours terrain

Les features proposées ici sont des **hypothèses haute priorité** à valider, pas des décisions.

---

_Document généré le 2026-04-17 après simulation persona "Pierre, associé M&A mid-market". À confronter aux retours terrain des 30 interviews Q2 2026._

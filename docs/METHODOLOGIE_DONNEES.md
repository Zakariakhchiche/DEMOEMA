# Origin — Méthodologie, sources & calculs des données

> Document de référence : pour chaque donnée affichée, **d'où elle vient** (source),
> **comment elle est obtenue** (extraction ou calcul) et **son périmètre** (portée + limites).
> Principe directeur : **uniquement de la donnée réelle (sourcée officiellement) ou
> calculée à partir de données réelles.** Aucune valeur inventée n'est présentée comme réelle.

Dernière mise à jour : 2026-06-12.

---

## 1. Sources de données (toutes officielles / publiques)

| Source | Fournisseur | Ce qu'on en tire | Mise à jour |
|---|---|---|---|
| **INPI RNE** | INPI (Registre National des Entreprises) | Dirigeants, mandats, formes juridiques, formalités | Flux quotidien |
| **INPI – Comptes annuels** | INPI (dépôts de bilans / liasses fiscales) | CA, résultat, EBITDA, postes de bilan | À chaque dépôt (annuel) |
| **INSEE / SIRENE** | INSEE | Identité, code NAF, capital social, état (actif/radié), effectif, adresse | Quotidien |
| **BODACC** | DILA (Journal Officiel) | Annonces légales : procédures collectives, cessions, ventes | Quotidien |
| **DVF** | DGFiP (Demandes de Valeurs Foncières) | Transactions immobilières (prix, surfaces) | Semestriel |
| **OpenSanctions / ICIJ** | OpenSanctions, ICIJ Offshore Leaks | Sanctions (OFAC/UE/UK/ONU), liens offshore, PEP | Régulier |
| **OSINT (domaines)** | Scan web (Maigret + domaines) | Présence digitale, site web | Ponctuel |

**Preuve d'exactitude** : nos valeurs sont croisées avec `recherche-entreprises.api.gouv.fr`
(API officielle de l'État, basée INPI/INSEE). Sur un échantillon aléatoire de 40 sociétés :
**code NAF 97,5 % exact**, **résultat net identique au centime**, **CA 88,6 % exact à ±5 %**.

---

## 2. Données d'identité (100 % sourcées, aucun calcul)

| Champ | Source | Périmètre |
|---|---|---|
| Dénomination, sigle | INSEE / INPI | Raison sociale officielle |
| SIREN / SIRET | INSEE | Identifiant légal |
| Code NAF / APE | INSEE | Activité principale |
| Forme juridique | INSEE | SAS, SARL, SA, SCI… |
| Capital social | INSEE / INPI | Capital déclaré |
| État administratif | INSEE | Actif (A) / Radié (F) |
| Adresse, ville, département | INSEE | Siège social |
| Effectif (tranche) | INSEE | Tranche déclarée |
| Date de création | INSEE | Immatriculation |

---

## 3. Données financières (sourcées INPI, codes CERFA de la liasse fiscale)

Extraites des **liasses fiscales déposées à l'INPI** (formulaires CERFA 2050-2052,
régime réel normal). Chaque poste = un code CERFA précis.

| Donnée | Code CERFA | Définition | Vérifié |
|---|---|---|---|
| **Chiffre d'affaires net** | **FJ** (colonne Total) | Ventes marchandises + production vendue biens + services | ✅ = officiel au centime |
| Total produits d'exploitation | FR | CA + production stockée + reprises + autres (≠ CA !) | conservé à part |
| **Résultat net** | **HN** | Bénéfice/perte après impôt | ✅ = officiel au centime |
| **Résultat d'exploitation (EBIT)** | **GG** | Résultat opérationnel | ✅ |
| Dotations d'exploitation | GA + GB + GC + GD | Amortissements + provisions | ✅ |
| Capitaux propres | DL | Fonds propres | ✅ |
| Total actif / passif | CO / EE | Total bilan | ✅ |
| Emprunts & dettes | DU | Dettes financières | ✅ |
| Charges d'intérêts | GU | Intérêts et charges assimilées | ✅ |
| Achats consommés | FS+FU+FT+FV | Achats marchandises/matières + variation stock | ✅ |
| Dettes fournisseurs | DX | Dettes fournisseurs et comptes rattachés | ✅ |

> ⚠️ **Correctif majeur (2026-06-12)** : le CA lisait auparavant le code **FR**
> (« Total des produits d'exploitation » = CA + production stockée + reprises),
> ce qui le **surévaluait de 15 à 25 %**. Désormais on lit **FJ** (le vrai
> chiffre d'affaires net), validé au centime contre la source officielle.

### EBITDA — calculé, mais sur données 100 % réelles
**EBITDA = Résultat d'exploitation (GG) + Dotations d'exploitation (GA+GB+GC+GD)**

C'est la formule comptable standard (EBIT + amortissements & provisions).
*Exemple Roederer 2024 : 72,5 M€ (EBIT) + 6,1 M€ (dotations) = **78,7 M€** ; marge 41,8 %.*
> (Auparavant un proxy `résultat net + 5 % du capital` était utilisé — supprimé.)

---

## 4. Ratios financiers (calculés à partir des postes réels ci-dessus)

Toutes les divisions sont protégées contre la division par zéro. « CA » = FJ (chiffre d'affaires net).

| Ratio | Formule | Interprétation |
|---|---|---|
| Marge EBITDA | EBITDA / CA | Rentabilité opérationnelle |
| Marge nette | Résultat net / CA | Rentabilité finale |
| Marge sur consommations | (CA − Achats) / CA | Structure de coûts |
| **ROA** | Résultat net / Total actif | Rentabilité des actifs |
| Dette / EBITDA | Emprunts & dettes / EBITDA | Capacité de remboursement |
| Dette / Fonds propres | Emprunts & dettes / Capitaux propres | Levier financier |
| Ratio d'endettement | (Total actif − Capitaux propres) / Total actif | Part de dette dans l'actif |
| **Couverture des intérêts** | EBIT / Charges d'intérêts | Service de la dette (LBO) |
| **DSO** (clients) | Créances clients / CA × 365 | Délai de paiement clients (jours) |
| **DPO** (fournisseurs) | Dettes fournisseurs / Achats × 365 | Délai de paiement fournisseurs (jours) |
| **BFR** (jours) | (Stocks + Créances) / CA × 365 | Cash immobilisé dans l'exploitation |
| Intensité capitalistique | Total actif / CA | Asset-heavy vs asset-light |
| Croissance CA (YoY) | (CA_n − CA_n-1) / CA_n-1 | Évolution annuelle (sur vrai CA multi-exercices) |

**Drapeaux de détresse** (booléens, sur EBITDA réel) :
- Capitaux propres négatifs · EBITDA négatif · Surendettement (dette/EBITDA > 4 ou dette/FP > 2) · Chute d'activité (croissance < −15 %).

---

## 5. Historique du CA (réel, multi-exercices)

Affiché en fiche et sur les cartes : les **5 derniers exercices déposés** (code FJ),
1 valeur par année. Données réelles INPI, jamais interpolées.
*Exemple Roederer : 154 M€ (2020) → 185 → 218 → 232 → 188 M€ (2024).*

---

## 6. Scoring M&A « Origin » (calcul propriétaire — clairement un SCORE, pas une donnée brute)

Le deal score 0-100 est **notre méthodologie** d'évaluation d'attractivité M&A.
Il combine 4 axes, chacun 0-100, calculés sur des données réelles.

### Les 4 axes
| Axe | Mesure | Principaux facteurs |
|---|---|---|
| **Transmission** | Probabilité de cession | Âge dirigeant (55→75+), patrimoine SCI, dirigeant unique senior, retard de dépôt |
| **Attractivity** | Valeur réelle de la cible | Marge, stabilité (≥3 exercices), premium sectoriel/géographique, solidité (fonds propres) |
| **Scale** | Taille transactionnelle | CA absolu (paliers 2M→100M€), multi-établissements, code LEI |
| **Structure** | Aptitude à la transaction | Forme juridique propre, holding patrimoniale, multi-mandats, capital social |

### Score composite
**deal_score = (Transmission × Attractivity × Scale)^(1/3) × multiplicateur_de_risque**

- Moyenne **géométrique** : un axe faible pénalise tout le score (≠ moyenne qui sature).
- **Multiplicateur de risque** (0 à 1) : abaissé par sanctions, procédure collective,
  retard de dépôt, perte. = 0 (éliminé) si sanction OFAC/UE, société radiée ou procédure en cours.

### Tier (classement par percentile)
`A_HOT` = top 1 %, `B_WARM` = top 5 %, `C_PIPELINE` = top 20 %, `D_WATCH` = top 50 %, `E_REJECT` = reste, `Z_ELIM` = éliminé (risque = 0).

### EV indicative — ⚠️ ESTIMATION (pas une donnée réelle)
**EV ≈ EBITDA × multiple sectoriel × facteur de taille.** C'est une **fourchette de
valorisation indicative**, pas une transaction réelle. À présenter comme telle.

---

## 7. Signaux & compliance (sourcés)

| Signal | Source | Calcul |
|---|---|---|
| Procédure collective | BODACC | Détection sur familles d'avis (redressement, liquidation, sauvegarde) 24 mois |
| Cession récente / vendeur en série | BODACC + INPI | Cessions sur 36 mois ; ≥ 2 sociétés cédées = serial seller (graphe Neo4j) |
| Sanctions | OpenSanctions | Match SIREN sur listes OFAC/UE/UK/ONU |
| Lien offshore | ICIJ | Match dirigeant ↔ entités offshore |
| Patrimoine immobilier dirigeant | INPI (SCI) + DVF | SCI détenues + transactions immobilières réelles |
| Asset-rich | INPI (bilan) | Immobilisations corporelles > 30 % de l'actif |
| Maturité digitale | OSINT | Score de présence web + domaine (couverture partielle ~2,3 %) |

---

## 8. Contactabilité dirigeant — ⚠️ GÉNÉRÉ (à vérifier)

Les **emails dirigeants** sont des **candidats probables générés** (domaine société +
nom : `prenom.nom@domaine`), **non vérifiés**. Affichés avec la mention « à vérifier
avant envoi ». Ce ne sont pas des données confirmées.

---

## 9. Périmètres & limites à connaître (transparence)

1. **Comptes SOCIAUX, pas consolidés** : on lit les comptes déposés par entité légale.
   Pour les **groupes/holdings**, les chiffres peuvent différer des comptes **consolidés**
   publiés (ex. une société-mère opérationnelle vs le périmètre groupe). Les deux sont réels,
   périmètres différents.
2. **Dernier exercice déposé** : l'année varie d'une société à l'autre (2022→2025 selon le dépôt).
   Un léger décalage avec une source tierce vient souvent de l'exercice retenu.
3. **Couverture du CA : ~32,5 %** des sociétés. Beaucoup de PME, SCI et holdings FR
   **ne déposent pas de comptes publics** (ou en confidentiel) → pas de CA disponible.
   Ce n'est pas un manque de qualité, c'est la réalité du dépôt légal en France.
4. **Nature des données** — 3 catégories, toujours distinguables :
   - 🟢 **Sourcée** : valeurs officielles (identité, CA, résultat, bilan, BODACC, DVF, sanctions).
   - 🟡 **Calculée** : ratios et scores, dérivés des données réelles (formules ci-dessus).
   - 🟠 **Estimée / générée** : EV indicative, emails candidats — **explicitement étiquetés**.

---

*Origin — plateforme d'origination M&A. Données issues exclusivement de sources publiques
officielles françaises ; calculs déterministes documentés ci-dessus.*

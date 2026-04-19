# ANALYSE CONCURRENTIELLE

> ⚠️ **Document V2 — corrigé post-audit 2026-04-17.**
>
> **Mises à jour majeures** :
> - **Pappers a un assistant IA depuis 2024** (Pappers IA) — corrigé
> - **Société.com a un assistant IA depuis 2024** — corrigé
> - **Harvey AI a levé $300M en 2024 à $3Md** — n'est plus "émergent"
> - **+9 concurrents ajoutés** : Clay, Apollo, Ocean.io, Ellisphere, Altares, Creditsafe, Preqin, Infogreffe Pro, Orbis, Zephyr
> - **Note exit** : BvD, Diane, Orbis, Zephyr = filiales Moody's. Pitchbook = Morningstar. **8 acquéreurs réels** (cf. `DECISIONS_VALIDEES.md`).
>
> Cartographie des concurrents directs et indirects, positionnement, différenciation.

---

## Matrice synthétique

| Concurrent | Cible | Forces | Faiblesses | Prix indicatif | Notre angle |
|---|---|---|---|---|---|
| **Pappers** | Tous (B2B + B2C) | UX moderne, prix bas, freemium puissant, **Pappers IA depuis 2024** | Légèreté de l'enrichissement, pas de scoring M&A propriétaire, pas de graphe relationnel | 9-99€/mois user | Profondeur graphe + signaux M&A prédictifs |
| **Société.com** | Pro généraliste | SEO ultra-dominant, base de prospects, **assistant IA depuis 2024** | Stack vieillissante, IA limitée à Q&A documentaire | 9-39€/mois | Intelligence trajectoire + graphe vs lookup |
| **Diane (Bureau van Dijk / Moody's)** | Banques d'aff., audit, M&A | Profondeur historique, comptes consolidés, Europe | Très cher, UX legacy lourde, contrats annuels rigides | 15-50k€/an/user | UX moderne + prix accessible |
| **Doctrine** | Avocats, juristes | Recherche juridique IA avancée | Vertical juridique, peu d'enrichissement entreprise | 200-500€/mois user | Couverture entreprise + juridique combinés |
| **Pitchbook** | PE, VC, banques d'aff. | Référence mondiale deals + comparables + valos | Ultra-cher, US-centric, faible profondeur ETI FR | 25-80k€/an/user | ETI mid-market FR/UE |
| **Crunchbase** | VC, startups | Référence levées startups, freemium | Faible sur ETI/Mid-market, US-centric | 30-99€/mois user (Pro) | Scope ETI/PME au-delà des startups |
| **Capital IQ (S&P)** | Banques, conseil, fonds | Profondeur financière mondiale | 20-40k€/an, US-centric | 20-40k€/an/user | Mid-market FR + signaux locaux |
| **Affinity / Attio** | PE, VC (relationship CRM) | Graphe relationnel + emails | Ne fournit PAS la donnée entreprise (à brancher) | 1-5k€/an user | Données + graphe en un seul outil |
| **CFNews** | M&A FR | Référence presse deals FR | Pas de base entreprise, lecture seule | 2-5k€/an user | Données + intelligence vs édito |
| **DealEdge / Mergermarket** | Banques, conseil | Deals tracker | Cher, lecture seule | 10-30k€/an | Datalake intégré + outils action |

---

## Pappers — analyse détaillée (concurrent #1 sur le low end)

**Forces**
- Freemium jusqu'à 5 fiches/mois
- API gratuite limitée, payante au-delà
- UX claire, mobile-first
- Couvre 100% des entreprises FR

**Faiblesses**
- Lookup + Q&A IA, **mais pas d'intelligence prédictive** sur la trajectoire de l'entreprise
- Pas de graphe dirigeants visuel (juste liste)
- Pas de scoring M&A propriétaire
- Notification basique
- Pappers IA = surface answer, pas un agent M&A spécialisé
- Pas d'Europe

**Notre angle de différenciation**
1. **Graphe dirigeants visuel** (Pappers a une simple liste)
2. **Scoring M&A propriétaire** (Pappers ne fait pas)
3. **Copilot LLM spécialisé M&A** (Pappers IA = Q&A documentaire généraliste)
4. **Signaux faibles temps réel** (Certificate Transparency, presse, GDELT)
5. **Cartographie écosystème** (clients/fournisseurs publics, brevets, etc.)

**Pricing à mettre face à Pappers** : freemium 5 fiches → tier "Pro" à 49€/user/mois (vs 39€ Pappers, mais bcp + de fonctionnalités).

---

## Diane / BvD — analyse détaillée (concurrent #1 sur le high end)

**Forces**
- 30+ ans de profondeur historique
- Comptes consolidés des groupes (donnée premium)
- Couverture Europe quasi-complète
- Standard de fait dans les Big4 audit

**Faiblesses**
- UX 1995, formation lourde
- Contrats annuels minimum (~15-50k€)
- Pas d'IA conversationnelle
- Lent à itérer (Moody's = grande organisation)
- Pas de signaux M&A automatisés

**Notre angle**
1. **UX moderne** (ratio 10× plus rapide à utiliser)
2. **Pricing accessible** (5-15k€/an vs 25-50k€)
3. **IA conversationnelle** (Diane = forms + tableaux)
4. **API moderne REST/GraphQL** (Diane = SOAP legacy souvent)
5. **Signaux temps réel** (Diane = données froides)

**Stratégie** : ne pas attaquer frontalement Diane sur l'audit Big4 (rétention forte), mais positionner sur les **équipes M&A des banques d'aff. moyennes, fonds PE mid-market, corporates avec dépt M&A**.

---

## Pitchbook — analyse détaillée (concurrent #1 sur le marché PE)

**Forces**
- Référence mondiale deals + comparables + valorisations
- Connecteur direct avec workflows PE/VC
- Couverture US ultra-dense

**Faiblesses**
- 25-80k€/an/user — inaccessible pour fonds < 100M€ AUM
- US-centric, faible profondeur ETI FR
- Pas de graphe dirigeants FR détaillé
- Pas de signaux faibles digitaux

**Notre angle**
1. **Mid-market FR/UE** où Pitchbook est faible
2. **Graphe dirigeants FR profond** (mandats croisés, INPI)
3. **Tarif 5-15k€/an** vs 25-80k€
4. **Signaux faibles** (web, presse, judiciaire)

---

## Affinity / Attio — concurrence indirecte (CRM relationnel)

**Forces**
- Très bons sur "qui connaît qui" via emails/calendar
- Adopté par les fonds PE/VC modernes

**Faiblesses**
- **Ne fournit PAS la donnée entreprise** — il faut la brancher (Crunchbase, Pitchbook, etc.)
- Coûteux quand on cumule Affinity + base données

**Notre angle**
- **Tout-en-un** : données entreprise + graphe relationnel
- **Intégrations Affinity/Attio** plutôt que les remplacer (en Y3)

---

## Concurrents émergents IA (à surveiller)

| Acteur | Description | Risque |
|---|---|---|
| **Harvey AI** (US) | LLM pour avocats — **levé $300M en 2024 à $3Md valo** | Acteur établi, pas émergent. Risque mid s'ils étendent au M&A |
| **Hebbia** (US) | Agents IA pour finance/M&A — levés $130M | Concurrent direct potentiel |
| **Causal / Capilex** | Outils M&A IA | Risque mid |
| **Doctrine + LLM** | Évolution probable de Doctrine vers M&A ? | Risque mid |
| **Clay** | Sales intelligence US (mid-market) — $100M+ levés | Overlap fort sur enrichissement données B2B |
| **Apollo** | Sales platform avec data B2B | Forte concurrence sur le segment "fiche entreprise enrichie" |
| **Ocean.io** | Lookalike B2B accounts | Niche complémentaire |

## Concurrents BvD/Moody's (groupe consolidé)

| Acteur | Position |
|---|---|
| **Diane** | Mid-market FR (mentionné plus haut) |
| **Orbis** | Base mondiale entreprises (50M+) |
| **Zephyr** | Base deals M&A mondiale |

> ⚠️ **Tous filiales de Moody's** — un seul acquéreur potentiel "groupe Moody's" dans la liste exit.

## Concurrents FR data crédit / risk

| Acteur | Description |
|---|---|
| **Ellisphere** | Data crédit + risk FR |
| **Altares** | D&B France, risk + business info |
| **Creditsafe** | Risk crédit FR + UE |
| **Infogreffe Pro** | Data officielle entreprises FR (registres) |
| **Preqin** | Référence PE/VC mondial |

---

## Positionnement final proposé

> **DEMOEMA = "L'OS des équipes M&A européennes mid-market : datalake + graphe + copilot."**

### Trois différenciateurs structurants

1. **GRATUIT À LA SOURCE** : 100% sources publiques → marges supérieures, pas de dépendance contractuelle
2. **GRAPHE NATIF** : pas un tableau, un réseau visuel (mandats, holdings, écosystèmes)
3. **COPILOT IA-FIRST** : conversation naturelle, pas des formulaires de recherche

### Marché cible (TAM SAM SOM) — recalculé V3.1 post-audit

> ⚠️ **Correction Q148** : la V2 affichait TAM 500M€ basé sur ARPU 10k€/an. Mais notre mix pricing (Starter+Pro+Enterprise) donne ARPU moyen ~3-5k€/an. Le TAM est donc **plus petit que ce qu'affichait la V2**, ou alors il faut viser plus Enterprise.

#### Calcul ARPU mix (scénario médian PRICING)

- 30% des clients en **Starter** (49€/mois × 12 = 588€/an)
- 50% en **Pro** (199€/mois × 12 = 2 388€/an)
- 20% en **Enterprise** (avg 25 k€/an)
- **ARPU mix moyen pondéré** : 0.30 × 588 + 0.50 × 2 388 + 0.20 × 25 000 = **6 370 €/an**

#### TAM/SAM/SOM cohérents avec ce ARPU

| Métrique | Calcul | Valeur | Notes |
|---|---|---|---|
| **TAM** (Europe M&A intel) | 50 000 utilisateurs × 6 370 € | **~320 M€/an** | (vs 500M€ V2 surévalué) |
| **SAM** (FR/BENELUX/DACH mid-market) | 15 000 utilisateurs × 6 370 € | **~95 M€/an** | (vs 150M€ V2) |
| **SOM cible Y4** (1 500-2 000 utilisateurs) | 2 000 × 6 370 € | **~13 M€ ARR** | Cohérent avec FINANCES_UNIFIE 8-15 M€ |

> **Sources des hypothèses** :
> - 50 000 utilisateurs M&A Europe : estimation France Invest + EVCA + benchmarks BvD/Pitchbook subscriber base
> - 15 000 mid-market FR/BNL/DACH : recoupement annuaires France Invest + AFIC + équivalents pays
> - ARPU 6 370 € : calcul direct depuis pricing scénario médian
>
> **À sourcer plus rigoureusement** : commander un rapport Gartner Market Guide for M&A Software (5-10k€) avant pitch Series A.

#### TAM si scénario HAUT (pricing)

Avec ARPU 9-10k€ (mix orienté Enterprise) :
- TAM = 50 000 × 10k = **500 M€** (= chiffre V2 légitime)
- Mais nécessite >50% Enterprise → **plus difficile à atteindre commercialement**

#### Wedge Y1 (rappel)

200 boutiques M&A FR mid-market × ARPU ~3 000 € (mix Starter+Pro) = **~600 k€/an de marché atteignable directement** par sales du founder. Cohérent avec ARR Y1 80 k€ (= ~13% de pénétration).

### Wedge Y1-Y2

Commencer par **les boutiques M&A FR mid-market** (~200 boutiques, ~2000 utilisateurs) :
- Pourquoi : douleur réelle (Diane trop cher, Pappers insuffisant), cycle de vente court
- Comment : démos directes via réseau personnel + LinkedIn fondateur
- Cible : 50 logos en Y1, 200 en Y2

---

## Veille concurrentielle continue

- **Trimestriel** : revue produit/pricing des 5 concurrents principaux
- **Mensuel** : revue presse/levées des concurrents émergents IA
- **Annuel** : repositionnement narratif si nécessaire

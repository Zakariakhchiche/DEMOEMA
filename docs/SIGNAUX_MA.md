# Scoring M&A DEMOEMA — Approche advisor pro

> Réécrit 2026-04-30 : passage du modèle additif 13 dimensions / 123 signaux
> à un modèle **multiplicatif 4 axes business + 1 axe risk** calibré sur la
> pratique réelle des cabinets M&A small/mid cap (Lazard, Rothschild, EdR,
> ESL, Argos). L'ancien barème additif produisait 50% des entreprises au-dessus
> de 65 — statistiquement absurde. Le nouveau utilise **percentile-based
> ranking** (top 1% / 5% / 20%) au lieu de seuils absolus.

---

## 1. Pourquoi cette refonte

Le barème précédent additionnait 13 dimensions de bonus avec une **baseline
50** (« tout le monde commence à 50/100 »). Conséquence :
- Une boîte avec juste un bilan récent + 1 SCI + dirigeant 60 ans = **70/100**
- 208 520 cibles `score >= 65` sur 411 303 (≈ 51%) = pas pertinent

**Un advisor M&A pense en 4 axes business multiplicatifs** + **un multiplicateur
risk**. Si UN axe est faible, le score composite est faible (effet entonnoir).

## 2. Les 4 axes business

| # | Axe | Signal n°1 | Pourquoi |
|---|---|---|---|
| **1** | **TRANSMISSION** | Âge dirigeant + patrimoine optimisé | 60% des cessions small cap viennent de la sortie du fondateur |
| **2** | **ATTRACTIVITY** | Marge proxy_EBITDA + multiple sectoriel | C'est ce qui détermine le prix réel |
| **3** | **SCALE** | CA absolu | Coûts de transaction fixes ~200k€ → barrière à 5M€ CA |
| **4** | **STRUCTURE** | Forme juridique + multi-mandats | SAS/SA + holding propre = transmission rapide |

Chaque axe est noté **0-100** indépendamment. Le score composite est :

```
deal_score = (transmission × attractivity × scale)^(1/3) × risk_multiplier
```

→ Moyenne géométrique : un 0 sur un axe = 0 composite. Pas de cibles bidons
qui « passent » par accumulation de bonus mineurs.

## 3. Détail axe par axe

### Axe 1 — TRANSMISSION (probabilité de cession)

Probabilité que le dirigeant veuille céder dans les 24 prochains mois.

| Signal | Points | Logique |
|---|---|---|
| Âge dirigeant max — courbe sigmoïde | 0 → 90 | 55→0pt, 60→22pt, 65→45pt, 70→67pt, 75+→90pt. Linéaire 4.5pt/an au-dessus de 55. |
| `n_sci ≥ 2 AND total_capital_sci > 500k€` | +30 | Patrimoine déjà optimisé fiscalement = signal ULTRA fort |
| `n_sci ≥ 2` (sans condition capital) | +20 | Holding patrimoniale active |
| `n_sci = 1` | +8 | Premier réflexe |
| `has_late_filing` | +12 | Lassitude opérationnelle (sortie mentale) |
| Dirigeant unique ET âge ≥ 60 | +8 | Homme-clé sans relève |

Cap à 100. Plus l'axe TRANSMISSION est fort, plus la cible est *prête à
être travaillée*.

### Axe 2 — ATTRACTIVITY (la valeur réelle de la cible)

Capacité à dégager du cash. Combine **marge** et **multiples sectoriels
implicites**.

```
proxy_ebitda = resultat_net + (capital_social × 0.05)
proxy_margin = proxy_ebitda / ca_latest
```

| Signal | Points |
|---|---|
| `proxy_margin ≥ 20%` | +50 |
| `proxy_margin ∈ [15%, 20%[` | +40 |
| `proxy_margin ∈ [10%, 15%[` | +30 |
| `proxy_margin ∈ [5%, 10%[` | +15 |
| `proxy_margin ∈ [0%, 5%[` | +5 |
| Stable (≥3 exercices déposés ET age ≥ 5 ans) | +15 |
| Sectoriel premium (NAF 62, 63, 86, 71, 70, 30, 58) | +15 |
| Géographie premium (75, 92, 78, 94, 93, 77, 95, 91, 69, 13, 06, 33, 31, 35, 59, 67, 44, 38) | +10 |
| Capitaux propres > 2× capital social | +10 |
| Capitaux propres > 0 | +5 |

### Axe 3 — SCALE (barrière transactionnelle)

Plus la boîte est petite, moins elle intéresse un cabinet (frais de transaction
fixes). Seuils calibrés sur la pratique :

| CA | Points | Catégorie |
|---|---|---|
| `≥ 100 M€` | 100 | Large cap |
| `≥ 50 M€` | 85 | Mid cap haut |
| `≥ 20 M€` | 70 | Mid cap |
| `≥ 10 M€` | 55 | Small cap haut |
| `≥ 5 M€` | 35 | Small cap (notre cœur) |
| `≥ 2 M€` | 15 | Micro cap |
| `< 2 M€` | 0 | Pas éligible advisor |

Bonus :
- Multi-établissements (effectif ≥ 11) : +5
- LEI présent (consolidé international) : +5

### Axe 4 — STRUCTURE (suitability)

| Signal | Points |
|---|---|
| Forme juridique propre (SAS/SA codes 5710-5599) | +40 (sinon +10) |
| `has_pro_ma` (dirigeant a déjà fait du M&A — n_mandats ≥ 5) | +25 |
| `n_mandats_dirigeant_max ≥ 5` | +15 |
| `has_holding_patrimoniale` | +20 |

## 4. Multiplicateur RISK

Pas additif — multiplicatif. Donc cumulatif (un risque haircut, plusieurs
risques empilent).

| Risque | Action |
|---|---|
| Sanction OFAC/UE/UK (`silver.opensanctions`) | × **0** → ELIMINATED |
| Radiation INSEE (`etat_administratif = 'F'`) | × **0** → ELIMINATED |
| Procédure collective < 24 mois (`silver.bodacc_annonces`) | × **0** → ELIMINATED |
| Sanction CNIL | × 0.75 |
| Sanction DGCCRF | × 0.80 |
| ≥ 3 contentieux récents (`silver.judilibre_decisions`) | × 0.70 |
| 1-2 contentieux récents | × 0.85 |
| `has_late_filing` | × 0.90 |
| Déficit (résultat net < 0) | × 0.90 |

Les 3 cas × 0 sont matérialisés en tier `Z_ELIM` mais gardés dans la table
pour traçabilité (un user qui interroge un siren radié doit voir « Éliminé :
radiation 2017 », pas « 0 résultats »).

## 5. Multiples sectoriels implicites (Argos Mid-Market 2024)

Utilisés pour calculer `ev_estimated_eur = proxy_ebitda × multiple × scale_premium`.

| Secteur (NAF) | Multiple | Justification |
|---|---|---|
| Tech / SaaS (62.xx, 63.xx) | 8.5× | Recurring revenue, scalable |
| Santé / MedTech (86.xx) | 9.5× | Demande structurelle |
| Industrie premium aéro/médical (30.xx, 32.50) | 7.0× | Barrières techniques |
| Édition / médias (58.xx) | 7.5× | IP / contenu |
| Services B2B (70.xx, 71.xx) | 6.0× | Récurrence |
| Industrie générale (25.xx, 28.xx) | 5.5× | |
| Finance / assurance (64-66) | 5.0× | |
| Construction / BTP (41-43) | 4.5× | Cyclique |
| Logistique (52-53) | 4.0× | Marges fines |
| Retail / Resto (47, 56) | 3.5× | Capex lourd |
| Default | 5.0× | |

`scale_premium` = +20% si CA ∈ [10M€, 50M€[, +40% si CA ≥ 50M€.

## 6. Tier basé PERCENTILE (vraie approche pro)

Calculé via `ntile(100) OVER (ORDER BY deal_score DESC)`.

| Tier | Percentile | Volume estimé sur 411k cibles | Action |
|---|---|---|---|
| **A_HOT** | ≤ 1% | ~4 100 boîtes | Pitch immédiat, dossier prio |
| **B_WARM** | 1-5% | ~16 500 boîtes | Approche commerciale ciblée |
| **C_PIPELINE** | 5-20% | ~62 000 boîtes | Veille active, qualification |
| **D_WATCH** | 20-50% | ~125 000 boîtes | Base données, pas d'action |
| **E_REJECT** | > 50% | reste | Hors-radar |
| **Z_ELIM** | n/a | sanctionnés/radiés | Éliminés (gardés en archive) |

L'avantage du percentile : si demain on injecte 1M de cibles supplémentaires,
le ranking se réajuste automatiquement, A_HOT reste le top 1%.

## 7. Fiche entreprise — affichage utilisateur

```
DUFOUR SISTERON (979598943)
└─ DEAL SCORE : 60 / 100 (percentile 12 → C_PIPELINE)

Détail des 4 axes :
├─ TRANSMISSION  : 78  ← dirigeant 67 ans, holding patrimoniale
├─ ATTRACTIVITY  : 42  ← CA 18 M€, marge 4.2%, secteur ×4
├─ SCALE         : 65  ← CA 18 M€ = small cap haut
└─ STRUCTURE     : 70  ← SAS, holding, multi-mandats

Risk : -30% (-1 contentieux récent, late filing)
EV estimée : 9.2 M€ (proxy EBITDA 0.76M × 4 × 1.0)

Pourquoi C_PIPELINE et pas A_HOT :
- Score TRANSMISSION fort mais ATTRACTIVITY faible
- Marge sectorielle insuffisante pour multiple premium
```

L'utilisateur voit immédiatement **l'axe fort**, **l'axe faible**, et la
**fourchette EV**. C'est ce qui rend l'outil exploitable par un vrai dealer.

## 8. Schema gold.scoring_ma

Colonnes principales (champs business) :

```sql
siren                 char(9)
denomination          text
code_ape              varchar(16)
adresse_dept          text

-- Proxies financiers
proxy_ebitda          numeric
proxy_margin          numeric    -- ratio 0-1
sector_multiple       numeric    -- ex 8.5
ev_estimated_eur      numeric    -- valorisation indicative

-- 4 axes business 0-100
transmission_score    int
attractivity_score    int
scale_score           int
structure_score       int

-- Risk
has_sanction_ofac_eu      boolean
has_sanction_cnil         boolean
has_sanction_dgccrf       boolean
has_proc_collective_recent boolean
has_cession_recent         boolean
n_contentieux_recent       int
risk_multiplier           numeric(4,3)  -- 0..1

-- Composite
deal_score_raw        int       -- 0-100, le score affiché
deal_percentile       int       -- 1-100, ntile DESC
tier                  varchar   -- A_HOT, B_WARM, C_PIPELINE, D_WATCH, E_REJECT, Z_ELIM

materialized_at       timestamptz
```

Indexes :
- `siren`, `tier`, `deal_score_raw DESC`, `deal_percentile`
- `transmission_score DESC`, `attractivity_score DESC`, `scale_score DESC`
- `ev_estimated_eur DESC NULLS LAST`
- `code_ape`, `adresse_dept`

## 9. Sources de signaux

| Signal | Source silver |
|---|---|
| Identité, financier, dirigeant | `silver.entreprises_signals` (via `gold.entreprises_master`) |
| Sanctions internationales | `silver.opensanctions` |
| Sanctions CNIL | `silver.cnil_sanctions` |
| Sanctions DGCCRF | `silver.dgccrf_sanctions` |
| Procédures collectives, modifications | `silver.bodacc_annonces` |
| Cessions détectées | `silver.cession_events` |
| Contentieux | `silver.judilibre_decisions` (proxy par dénomination) |
| LEI international | `silver.gleif_lei` |

À ajouter (non encore exploités dans v3) :
- `silver.press_mentions_matched` → presse négative récente (sentiment)
- `silver.osint_companies_enriched` → digital footprint
- `silver.transparence_sante_dirigeants` → KOL pharma signal
- `silver.icij_offshore_match` → offshore link compliance

## 10. Évolutions prévues

- **Croissance CA 3Y** dès qu'on a la time-series multi-bilan dans
  `silver.inpi_comptes` (actuellement on n'a que latest).
- **EBITDA réel** (pas proxy) si on parse les comptes annuels détaillés.
- **Sentiment presse** automatique sur `press_mentions_matched`.
- **Multiples sectoriels** : passer en table dédiée `gold.sector_multiples`
  rafraîchie trimestriellement avec source Argos / France Invest.
- **Filiation / actionnariat** via `silver.inpi_personnes_morales` pour
  détecter les filiales déjà vendables vs holding mère.

---

**Référence d'implémentation** : voir `infrastructure/agents/scripts/gold/scoring_ma_v3_pro.sql`

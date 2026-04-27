# Stratégie OSINT — Maximum coverage dirigeants

**Objectif** : enrichissement maximal des dirigeants français pour le scoring
M&A, croisement de **mandats × SCI/patrimoine × financier consolidé × réseau ×
événements × légal × presse × digital**.

## État courant (post-migration VPS)

| Source | Volume disponible | Usage feature store |
|---|---:|---|
| `silver.inpi_dirigeants` | ~8M dirigeants | identité + mandats actifs |
| `silver.dirigeant_sci_patrimoine` | ~3.5M | SCI / patrimoine |
| `silver.inpi_comptes` | ~6M dépôts | financier consolidé |
| `silver.bodacc_annonces` | ~30M | événements légaux |
| `silver.opensanctions` | ~280K | sanctions internationales |
| `silver.judilibre_decisions` | ~15K ⚠️ | contentieux (couverture trop faible) |
| `silver.press_mentions_matched` | ~39K ⚠️ | presse (couverture trop faible) |
| `silver.osint_persons_enriched` | ~2K ⚠️ | digital (couverture trop faible) |

**Cible** : au moins 1M dirigeants enrichis OSINT, 8M dirigeants 360° via le
feature store `silver.dirigeants_360`.

## Feature store cible : `silver.dirigeants_360`

Spec dans [`silver_specs/dirigeants_360.yaml`](../agents/platform/ingestion/silver_specs/dirigeants_360.yaml).

Pour chaque person_uid (clé = sha1(nom + prenoms triés + date_naissance)) :

```yaml
identité          : person_uid, nom, prenom, prenoms[], date_naissance, age_2026
mandats           : n_mandats_actifs, sirens_mandats[], denominations_mandats[]
patrimoine SCI    : n_sci, sci_sirens[], total_capital_sci, first_sci_date
financier         : ca_total, capital_total_companies, resultat_net_total
network           : co_mandataires[], n_co_mandataires
événements        : n_bodacc_cessions, n_bodacc_difficultes, has_cession_recente
légal             : n_jugements, has_contentieux_recent
sanctions         : is_sanctionne, sanction_programs[]
presse            : n_press_mentions_90d, has_press_buzz
digital           : has_linkedin, has_github, n_total_social, digital_presence_score
score composite   : pro_ma_score (0-100)
```

Le silver bootstrap topologique va créer cette MV automatiquement au prochain
boot agents-platform (toutes les sources sont en amont).

## Stratégie d'enrichissement OSINT — 4 phases

### Phase 1 — Sources gratuites massives (0 €, 1-2 jours, +500K dirigeants)

5 specs YAML déjà dans le repo mais bronze tables vides à ce jour. Trigger
`bronze_bootstrap` ou `silver_maintainer` pour les remplir :

| Source | API | Volume cible |
|---|---|---|
| **Wikidata SPARQL** | `query.wikidata.org/sparql` (FR humans/entreprises) | 50-150K |
| **HAL** | API HAL gratuite | 10-50K chercheurs |
| **OpenAlex** | `api.openalex.org` (works) | 20-80K auteurs scientifiques |
| **GitHub** | `api.github.com/search/users` (5K req/h auth) | 30-80K founders tech |
| **crt.sh** | API certificats SSL | tous domains FR (5M certs) → CEO via WHOIS |
| **OpenCorporates** | API freemium 50K req/jour | 5M entreprises FR + officers |

**Total potentiel** : 200-500K dirigeants enrichis avec data structurée.

### Phase 2 — Web scraping coordonné (50-200 €/mois, 2-3 semaines, +2-4M)

Pour les dirigeants sans présence sur les sources Phase 1, scraping ciblé :

| Cible | Méthode | Volume |
|---|---|---|
| LinkedIn public profiles | Google `site:linkedin.com/in/` + nom + entreprise | 1-3M |
| Sites perso | Google `"prenom nom" "siren"` | 200-500K |
| Press archives | Mediapart, Le Monde, Les Echos | 100-300K |
| Conférences alumni | HEC, ESCP, Sciences Po, X | 50-100K |

**Infrastructure requise** :
- IPs rotating (Bright Data ou Smartproxy) : ~150 €/mois
- Captcha solver (2captcha déjà dans le projet) : ~10 €/mois
- Headless browser pool (Playwright via openclaw existant) : 0
- Rate limit : 50-100 req/s à plusieurs IPs

**Risque légal** : LinkedIn TOS interdit le scraping, CNIL en France. Mitigation :
- Stocker UNIQUEMENT les données publiques (nom + position + URL profile)
- Pas de redistribution
- Hashage du lien pour traçabilité
- Anonymisation possible sur demande utilisateur (RGPD art. 17)

### Phase 3 — APIs payantes ciblées (200-2 000 €/mois, ongoing)

Pour les **emails** + **téléphones** + **historique professionnel** :

| API | Use case | Coût | Volume |
|---|---|---|---|
| **Apollo.io** | email + tel + intent data | 99-300 €/mois | 50K credits/mois |
| **Hunter.io** | email patterns par domaine | 50-150 €/mois | 5-25K |
| **Cognism** | sales intelligence enterprise | 1500 €/mois | unlimited |
| **PhantomBuster** | semi-auto LinkedIn | 50-200 €/mois | 5-20K |

**Démarrage recommandé** : Apollo.io 99 €/mois (50K credits) pour les
dirigeants prioritaires (Tier 1 du feature store : pro_ma_score ≥ 50).

### Phase 4 — Continuous enrichment

- **Daily delta** : nouveaux dirigeants depuis INPI (~2K/jour) → enrich
  automatique via le silver_maintainer
- **Monthly refresh** : ré-enrich top 10% pro_ma_score (changements LinkedIn
  fréquents, fusions, départs)
- **On-demand** : trigger immédiat quand un siren passe dans
  `/api/copilot/query` ou `/api/targets/search-pappers`

## Roadmap

| Étape | Action | Coverage cumulée | Délai |
|---|---|---|---|
| 1 | Migration VPS terminée + `dirigeants_360` MV bootstrappée | 8M dirigeants 360° | en cours |
| 2 | Phase 1 — backfill specs Wikidata/HAL/OpenAlex/GitHub/crt.sh | +500K OSINT | 1-2 jours |
| 3 | Phase 2a — pipeline LinkedIn via openclaw + proxies | +1-2M | 2 sem |
| 4 | Phase 2b — sites perso + press archives | +500K-1M | 3 sem |
| 5 | Phase 3 — Apollo.io ciblé Tier 1 | +50K emails/mois | continu |
| 6 | Phase 4 — daily delta + monthly refresh | maintenance | continu |

## Stockage à prévoir

```
Phase 1  : ~5-10 GB structured (gratuit)
Phase 2  : ~50-100 GB raw HTML + ~10-20 GB structured
Phase 3  : ~5-10 GB API responses (cached 90j)
Total    : ~80-130 GB enrichissement OSINT (sur 945 GB libres du nouveau VPS)
```

## Considérations RGPD / éthiques

- Article 6 RGPD : intérêt légitime (M&A advisory) pour traitement
- Article 17 (droit à l'effacement) : endpoint `/api/admin/rgpd/delete?person_uid=X`
- Article 32 (sécurité) : données chiffrées at rest (Postgres TDE optionnel),
  accès via API key seulement
- CNIL : déclaration de traitement à mettre à jour si OSINT massif passe en prod

Données à ne JAMAIS scraper :
- Données de santé
- Opinions politiques (sauf HATVP qui est public)
- Orientation sexuelle / religion
- Mineurs (filtrer par age >= 18)

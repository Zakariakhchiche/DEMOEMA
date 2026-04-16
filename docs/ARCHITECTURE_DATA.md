# Architecture Data — EdRCF 6.0

## 1. Contexte : migration Pappers vers sources gratuites

Pappers MCP etait la source unique du projet. Il agregait des donnees publiques
gratuites (INSEE, INPI, BODACC) dans une API payante. Nous remplacons par des
appels directs aux sources gouvernementales.

### Schema global

```
AVANT (payant)                    APRES (gratuit)
-----------------                 -----------------------------
                                  +- API Recherche Entreprises
                                  +- INSEE SIRENE
  Pappers MCP --- tout --->      +- INPI RNE (dirigeants, comptes)
  (1 source payante)              +- API BODACC (publications legales)
                                  +- Infogreffe Open Data
                                  +- GLEIF (ownership international)
                                  +- 19 sources additionnelles
                                  +- Score defaillance interne
```

## 2. Les 25 sources gratuites

### Couche 1 — Identification entreprise

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| API Recherche Entreprises | recherche-entreprises.api.gouv.fr | Aucune | SIREN, nom, siege, NAF, dirigeants, CA, resultat net |
| INSEE SIRENE | portail-api.insee.fr | OAuth2 gratuit | SIREN/SIRET, etablissements, statut, effectif |

Filtres disponibles sur API Recherche Entreprises :
- `q` : texte libre (nom, SIREN, SIRET, adresse)
- `activite_principale` : code NAF
- `departement` : departement
- `etat_administratif` : A (active) / C (cessée)
- `ca_min` / `ca_max` : chiffre d'affaires
- `resultat_net_min` / `resultat_net_max`
- `nature_juridique` : forme juridique
- `tranche_effectif_salarie` : effectif
- `categorie_entreprise` : PME / ETI / GE

### Couche 2 — Dirigeants

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| INPI RNE | data.inpi.fr | Compte gratuit | nom, prenom, role, date naissance, date prise de poste |
| API Recherche Entreprises | idem | Aucune | nom, prenoms, annee naissance, qualite |

Endpoint INPI : `GET /api/companies/{siren}` -> champ `representants`
Quota : 10 000 req/jour.

### Couche 3 — Donnees financieres

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| API Recherche Entreprises | idem | Aucune | CA et resultat net par annee |
| INPI RNE Comptes annuels | data.inpi.fr | Compte gratuit | Liasses fiscales structurees JSON (code FJ=CA, DI=resultat net) |
| ESANE INSEE | data.gouv.fr | Aucune | Benchmark sectoriel (CA, VA, effectifs) |

### Couche 4 — Publications legales (BODACC)

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| API BODACC | bodacc-datadila.opendatasoft.com | Aucune | 48.8M annonces, recherche par SIREN |

Endpoint : `GET /api/records/1.0/search/?dataset=annonces-commerciales&q=registre:{siren}`

Categories BODACC :
- BODACC A : creations, ventes/cessions, procedures collectives (3.3M + 872K)
- BODACC B : modifications, radiations (8.3M + 4.0M)
- BODACC C : depots des comptes (25.3M)

### Couche 5 — Procedures collectives

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| API BODACC | idem | Aucune | familleavis = "Procedures collectives" |
| URSSAF Open Data | open.urssaf.fr | Aucune | Series trimestrielles procedures par secteur/region |

### Couche 6 — Ownership & Groupe

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| GLEIF API | api.gleif.org/api/v1 | Aucune | Parent direct, parent ultime, filiales |
| INPI RNE | data.inpi.fr | Compte gratuit | Beneficiaires effectifs (acces restreint) |
| OpenCorporates | opencorporates.com | Gratuit (public benefit) | 200M entreprises, 140 pays |

Lookup GLEIF par SIREN : `GET /lei-records?filter[entity.registeredAs]={siren}`
Limitation : seulement ~2% des entreprises FR ont un LEI (80-100K sur 5M).

### Couche 7 — Score de defaillance (calcul interne)

Pappers fournissait un `scoring_non_financier`. Aucun equivalent gratuit n'existe.
Nous le recalculons en interne :

| Facteur | Poids | Source |
|---------|-------|--------|
| Nb procedures BODACC recentes | 30% | API BODACC |
| Tendance CA sur 3 ans | 25% | INPI comptes |
| Age dirigeant sans successeur | 15% | INPI RNE |
| Resultat net negatif | 15% | INPI comptes |
| Nb publications BODACC recentes | 10% | API BODACC |
| Effectif en baisse | 5% | INSEE SIRENE |

Inspire du projet Signaux Faibles (startup d'Etat : github.com/signaux-faibles).

### Couche 8 — Marches publics

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| BOAMP | boamp.fr/api | Aucune | Appels d'offres, attributions |
| DECP | data.economie.gouv.fr/decp-v3 | Aucune | Montants, attributaires |

### Couche 9 — Propriete intellectuelle

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| INPI Brevets | data.inpi.fr/api/brevets | Compte gratuit | Applications brevets depuis 1902 |
| INPI Marques | data.inpi.fr/api/marques | Compte gratuit | Marques actives |
| MESR Brevets | data.enseignementsup-recherche.gouv.fr | Aucune | Brevets INPI + OEB |
| CIR/CII | data.esr.gouv.fr | Aucune | Entreprises agreees recherche |

### Couche 10 — Emploi & Signaux sociaux

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| France Travail | francetravail.io/data/api | Aucune | Offres d'emploi (signal croissance) |
| URSSAF Open Data | open.urssaf.fr | Aucune | Effectifs, masse salariale |
| DARES | data.dares.travail-emploi.gouv.fr | Aucune | Tensions metiers, dynamique emploi |

### Couche 11 — Immobilier / Patrimoine

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| DVF / DVF+ | data.gouv.fr/dvf | Aucune | Transactions foncieres depuis 2014 |
| API Cadastre | api.gouv.fr/carto/cadastre | Aucune | Parcelles et batiments (GeoJSON) |

### Couche 12 — Compliance & Sanctions

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| Gels des Avoirs | gels-avoirs.dgtresor.gouv.fr | Aucune | Sanctions FR/UE/ONU (JSON/XML) |
| AMF listes noires | data.gouv.fr/amf | Aucune | Entites non autorisees |
| ACPR REGAFI/Refassu | regafi.fr / acpr.banque-france.fr | Aucune | Autorisations bancaires/assurance |

### Couche 13 — ESG / Environnement

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| ADEME Bilans GES | bilans-ges.ademe.fr | Aucune | Emissions carbone par entreprise |
| ADEME Base Carbone | data.ademe.fr | Aucune | Facteurs d'emission |

### Couche 14 — Lobbying & Transparence

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| HATVP | hatvp.fr/open-data | Aucune | 3215+ lobbyistes, activites, contacts |
| Transparence Sante | transparence.sante.gouv.fr | Aucune | Paiements pharma (secteur sante) |

### Couche 15 — Presse & Veille media

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| Google News RSS | news.google.com/rss | Aucune | Actualites par entreprise |
| Le Journal des Entreprises | lejournaldesentreprises.com/rss | Aucune | Presse regionale (14 editions) |
| Atlas des Flux RSS | atlasflux.saynete.net | Aucune | Repertoire flux eco (Capital, Xerfi, AFP) |

### Couche 16 — Aides & Subventions

| Source | URL | Auth | Donnees |
|--------|-----|------|---------|
| Data.Subvention | datasubvention.beta.gouv.fr/api | Aucune | Subventions recues |
| les-aides.fr | les-aides.fr/api | Inscription gratuite | Catalogue aides publiques |

## 3. Matrice de couverture Pappers vs Sources gratuites

| Donnee Pappers | Couverte | Source gratuite |
|----------------|----------|-----------------|
| Recherche par nom | 100% | API Recherche Entreprises |
| Recherche par NAF | 100% | API Recherche Entreprises |
| Recherche par departement | 100% | API Recherche Entreprises |
| Filtre entreprise cessee | 100% | API Recherche Entreprises (etat_administratif) |
| Filtre age dirigeant | 80% | INPI RNE -> post-filtrage |
| Filtre CA min/max | 100% | API Recherche Entreprises (ca_min/ca_max) |
| siren | 100% | API Recherche Entreprises |
| nom_entreprise | 100% | API Recherche Entreprises |
| siege (adresse, CP, ville) | 100% | API Recherche Entreprises |
| date_creation | 100% | API Recherche Entreprises |
| code_naf | 100% | API Recherche Entreprises |
| libelle_code_naf | Mapping local | Table NAF INSEE (telechargeable) |
| effectif | 100% | API Recherche Entreprises (tranche) |
| forme_juridique | 100% | API Recherche Entreprises (code, mapping local) |
| capital | 100% | INPI RNE |
| representants (tous champs) | 100% | INPI RNE |
| finances (CA, resultat, annee) | 100% | API Recherche Entreprises + INPI comptes |
| beneficiaires_effectifs | Restreint | INPI RNE (autorites AML uniquement) |
| etablissements | 100% | INSEE SIRENE |
| publications_bodacc | 100% | API BODACC OpenDataSoft |
| procedure_collective | 100% | API BODACC + URSSAF |
| scoring_non_financier | Recalcule | Score interne EdRCF |
| cartographie entreprise | 90% | GLEIF + INPI beneficiaires |
| comptes detailles (liasses) | 100% | INPI RNE (JSON + PDF) |
| recherche dirigeant par nom | 100% | API Recherche Entreprises |
| concurrents (meme NAF/dept) | 100% | API Recherche Entreprises |

Couverture globale : 95%+ des donnees Pappers + 10 couches nouvelles.

## 4. Schema d'architecture technique

```
                         +-------------------------------+
                         |     FRONTEND (Next.js)        |
                         |  Dashboard / Targets / Graph  |
                         +---------------+---------------+
                                         |
                         +---------------v---------------+
                         |     BACKEND (FastAPI)         |
                         |  main.py + data_sources.py    |
                         +---------------+---------------+
                                         |
              +--------------------------+-------------------------+
              |                          |                         |
    +---------v--------+     +-----------v----------+    +---------v--------+
    |  IDENTIFICATION   |     |    ENRICHISSEMENT    |    |   INTELLIGENCE   |
    |  (Couches 1-2)    |     |    (Couches 3-7)     |    |   (Couches 8-16) |
    +--------+---------+     +----------+-----------+    +--------+---------+
             |                          |                         |
   +---------+---------+    +----------+----------+    +---------+---------+
   |         |         |    |          |          |    |         |         |
+--v--+ +----v---+ +---v-+ +--v--+ +--v---+ +---v-+ +--v--+ +--v---+ +---v----+
|Rech.| |INSEE   | |INPI | |INPI | |BODACC| |GLEIF| |BOAMP| |France| |INPI    |
|Entr.| |SIRENE  | |RNE  | |Cptes| |API   | |API  | |DECP | |Trav. | |Brevets |
+-----+ +--------+ +-----+ +-----+ +------+ +-----+ +-----+ +------+ +--------+
Aucune   OAuth2     Compte  Compte  Aucune   Aucune  Aucune  Aucune   Compte
 auth    gratuit    gratuit gratuit                                    gratuit
```

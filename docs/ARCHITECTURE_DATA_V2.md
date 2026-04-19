# ARCHITECTURE DATA V2.1 — 144 Sources Gratuites (141 actives)

> ⚠️ **Document V2.1 — corrigé post-audit `SELF_CHALLENGE_V3_DATA_CATALOG` (2026-04-18).**
>
> **3 sources retirées** :
> - ❌ #41 INPI RBE : fermé public depuis CJUE 22/11/2022 (WM/Luxembourg) — **trancher : RETIRÉ Y1-Y4** (pas de dérogation)
> - ❌ #125 Trustpilot : CGU interdisent scraping commercial — **RETIRÉ Y1-Y2, ré-intégration Y3 via Trustpilot Business API (~300€/mois)**
> - ❌ #126 Google Reviews : CGU Google interdisent scraping — **RETIRÉ définitivement**
>
> **6 sources presse en mode dégradé** (#119-124) : titre + URL + date uniquement (droits voisins) — **insuffisant pour Who advises whom** → cf. couche 17bis ci-dessous
>
> ⭐ **Nouvelle couche 17bis ajoutée** : sites web boutiques M&A FR (publication volontaire de leurs deals — usage public légitime). Indispensable pour Who advises whom V1 Q4 2026.
>
> ⚠️ **Validation requise** : aucune des 144 sources n'a été testée techniquement à ce jour. Cf. [`VALIDATION_API.md`](./VALIDATION_API.md) pour la procédure (à exécuter Q2-Q3 2026).
>
> Objectif : cartographier **toutes les entreprises de France** (5M SIREN actifs, 31M établissements) avec enrichissement profond sur fonctionnement, dirigeants et écosystèmes. Extension européenne prévue en année 3.

## Vue d'ensemble

| Métrique | V1 (au 17/04/2026) | V2.1 (cible) |
|---|---|---|
| Nombre de sources | **25 documentées / 0 branchées dans le code** (démo Vercel sans ingestion data) | **144 cataloguées / 141 actives** |
| Couches fonctionnelles | 16 | **20** (ajout couche 17bis sites boutiques M&A) |
| Coût mensuel API data publique | 0€ (rien en prod) | **0€ Y1 sur data publique** (hors LLM Y2+ ~50k€/an + partenariats Y2 Ellisphere/CFNews ~10-50k€/an) |
| Entités couvertes FR | 0 | 5M entreprises + 1.5M associations + 31M étab + 15M personnes |
| Extension UE | ❌ | ✅ (année 3) |

---

## COUCHE 1 — Identification entreprise (clés primaires)

| # | Source | URL | Auth | Volume | Données clés |
|---|---|---|---|---|---|
| 1 | API Recherche Entreprises | recherche-entreprises.api.gouv.fr | ❌ | 5M | SIREN, dénomination, dirigeants, finances |
| 2 | INSEE SIRENE V3 | api.insee.fr/entreprises/sirene/V3 | OAuth2 | 31M étab | SIREN/SIRET, NAF, effectifs, géoloc |
| 3 | INSEE SIRENE Stock (Parquet) | files.data.gouv.fr/insee-sirene | ❌ | 31M | Bulk téléchargement mensuel |
| 4 | INPI RNE | data.inpi.fr | OAuth2 | 5M | Représentants légaux, bénéficiaires effectifs, comptes |
| 5 | annuaire-entreprises.data.gouv.fr | annuaire-entreprises.data.gouv.fr/api | ❌ | 5M | Vue consolidée officielle |
| 6 | data.gouv.fr SIRENE géolocalisé | data.gouv.fr/dataset/base-sirene-geolocalisee | ❌ | 31M | Coordonnées XY |
| 7 | RNA (associations) | data.gouv.fr/rna | ❌ | 1.5M | Associations loi 1901 |
| 8 | JOAFE | data.gouv.fr/journal-officiel-associations | ❌ | continu | Annonces associations |

**Clé primaire FR :** `siren` (9 chiffres) pour les entreprises, `rna_id` (W + 9 chiffres) pour les associations.

---

## COUCHE 2 — Identifiants internationaux (résolution d'entités)

| # | Source | URL | Apport |
|---|---|---|---|
| 9 | GLEIF API | api.gleif.org/api/v1 | LEI mondial, structures parent/filiale |
| 10 | OpenCorporates Open Data | opencorporates.com/data | 200M entreprises, 140 pays — ⚠️ **snapshot gelé depuis 2019, pas de deltas gratuits** (Plan B : croiser GLEIF + Wikidata) |
| 11 | Wikidata Query Service | query.wikidata.org | QID, biographies, presse |
| 12 | OpenSanctions | opensanctions.org/api | 200+ listes sanctions consolidées |
| 13 | ROR (Research Org Registry) | ror.org | Identifiants organismes de recherche |
| 14 | ~~GRID.ac~~ | ~~grid.ac~~ | ⚠️ **Marqué "legacy" — RETIRER du catalog actif** (utiliser ROR à la place) |
| 15 | OpenPermid (Refinitiv) | permid.org | PermID — ⚠️ **Refinitiv = filiale LSEG (acquéreur cité DECISIONS_VALIDEES)** = conflit d'intérêt latent. À évaluer Y2. |

**Rôle :** résolution d'entités multi-sources — un même groupe peut apparaître avec 7 identifiants différents.

---

## COUCHE 3 — Comptes annuels & finances

| # | Source | URL | Apport |
|---|---|---|---|
| 16 | INPI comptes annuels | data.inpi.fr/comptes | Bilans, comptes de résultat (PDF + XBRL) |
| 17 | ESANE INSEE | insee.fr/fr/statistiques/esane | Benchmarks sectoriels CA/marge |
| 18 | Banque de France Webstat | webstat.banque-france.fr | Endettement, taux sectoriels |
| 19 | Centrale des Bilans BdF | banque-france.fr | Indicateurs sectoriels agrégés |
| 20 | ANC (Autorité Normes Comptables) | anc.gouv.fr | Référentiels, règles |
| 21 | data.economie.gouv.fr | data.economie.gouv.fr | Filiales, comptes consolidés grands groupes |

---

## COUCHE 4 — Marchés cotés & international

| # | Source | URL | Apport |
|---|---|---|---|
| 22 | AMF BDIF | bdif.amf-france.org | Franchissements de seuils, déclarations dirigeants |
| 23 | AMF GECO | geco.amf-france.org | Décisions, agréments |
| 24 | Euronext Open Data | live.euronext.com | Cours, capi, free float |
| 25 | SEC EDGAR | sec.gov/edgar | Filiales US (10-K, 20-F) |
| 26 | Companies House UK | companieshouse.gov.uk/api | Filiales UK (100% gratuit) |
| 27 | Bundesanzeiger | bundesanzeiger.de | Filiales DE |
| 28 | Registre BCE belge | kbopub.economie.fgov.be | Filiales BE |
| 29 | ESAP | esap.europa.eu | ⚠️ **"Live 2026" reporté plusieurs fois depuis 2021** — probabilité forte de nouveau décalage. Plan B Y3 : registres nationaux (Companies House UK, Bundesanzeiger DE, BCE belge) |

---

## COUCHE 5 — Publications légales & procédures

| # | Source | URL | Apport |
|---|---|---|---|
| 30 | BODACC | bodacc-datadila.opendatasoft.com | 48M annonces (création, modif, procédures) |
| 31 | Infogreffe Open Data | data.inpi.fr/infogreffe | Procédures collectives, RBE |
| 32 | URSSAF Open Data | open.urssaf.fr | Données trimestrielles cotisants |
| 33 | data.gouv.fr Procédures | data.gouv.fr | Datasets agrégés |

---

## COUCHE 6 — Juridique & Contentieux (nouveau)

| # | Source | URL | Apport |
|---|---|---|---|
| 34 | Judilibre | api.piste.gouv.fr/cassation/judilibre | Décisions Cass + CA + TJ + prud'hommes |
| 35 | Légifrance API | api.piste.gouv.fr/aife/legifrance | JORF, Conseil d'État, CC, décrets nominatifs |
| 36 | CNIL sanctions | cnil.fr/fr/la-cnil-sanctionne | Amendes RGPD publiées |
| 37 | Autorité de la Concurrence | autoritedelaconcurrence.fr | Décisions ententes, abus position |
| 38 | DGCCRF sanctions | economie.gouv.fr/dgccrf | Pratiques commerciales |
| 39 | ANSSI CERT-FR | cert.ssi.gouv.fr | Alertes cyber impactant entreprises |
| 40 | Conseil d'État ArianeWeb | conseil-etat.fr/arianeweb | Jurisprudence administrative |

---

## COUCHE 7 — Ownership & bénéficiaires effectifs

| # | Source | URL | Apport |
|---|---|---|---|
| 41 | ~~INPI RBE~~ | ~~data.inpi.fr~~ | ⚠️ **Accès public fermé depuis arrêt CJUE 22/11/2022 (WM/Luxembourg Business Registers).** Accès restreint aux personnes ayant un intérêt légitime documenté. **À retirer du datalake** ou à demander accès dérogatoire (avocat, journaliste, lutte blanchiment). |
| 42 | OpenSanctions Owners | opensanctions.org | Bénéficiaires consolidés monde |
| 43 | ICIJ Offshore Leaks DB | offshoreleaks.icij.org | Panama/Paradise/Pandora |
| 44 | OCCRP Aleph | aleph.occrp.org | Données fuites + sources publiques |
| 45 | UK PSC Register | companieshouse.gov.uk/psc | People with significant control UK |

---

## COUCHE 8 — Marchés publics

| # | Source | URL | Apport |
|---|---|---|---|
| 46 | BOAMP | boamp.fr/api | Appels d'offres FR |
| 47 | DECP | data.economie.gouv.fr/decp-v3 | Attributions FR |
| 48 | TED (UE) | ted.europa.eu | Marchés publics UE |
| 49 | data.economie aides-entreprises | data.economie.gouv.fr/aides | France 2030, Relance |
| 50 | OpenContracting | standard.open-contracting.org | Standard mondial contrats |

---

## COUCHE 9 — Propriété intellectuelle & R&D

| # | Source | URL | Apport |
|---|---|---|---|
| 51 | INPI Brevets | data.inpi.fr/api/brevets | Dépôts FR depuis 1902 |
| 52 | INPI Marques | data.inpi.fr/api/marques | Marques actives FR |
| 53 | EPO OPS | ops.epo.org | Brevets européens |
| 54 | EUIPO TMview | tmview.europa.eu | Marques UE |
| 55 | WIPO PatentScope | patentscope.wipo.int | Brevets mondiaux PCT |
| 56 | MESR Brevets | data.enseignementsup-recherche.gouv.fr | Indicateurs INPI/OEB |
| 57 | CIR/CII | data.esr.gouv.fr | Entreprises agréées recherche |
| 58 | Scanr | scanr.enseignementsup-recherche.gouv.fr | Liens labos↔entreprises, CIFRE |
| 59 | HAL | hal.science | Publications scientifiques |
| 60 | OpenAlex | openalex.org | 250M articles mondiaux |
| 61 | CrossRef | api.crossref.org | DOI, citations |
| 62 | ORCID | orcid.org | Chercheurs identifiés |

---

## COUCHE 10 — Emploi & RH

| # | Source | URL | Apport |
|---|---|---|---|
| 63 | France Travail API | francetravail.io/data/api | Offres publiques |
| 64 | DARES | data.dares.travail-emploi.gouv.fr | Tensions métiers |
| 65 | Welcome to the Jungle RSS | welcometothejungle.com | Offres tech/startup |
| 66 | Indeed RSS | fr.indeed.com | Offres généralistes |
| 67 | APEC Open Data | data.apec.fr | Offres cadres |
| 68 | OPCO Open Data | data.gouv.fr/opco | Formations financées |
| 69 | DSN agrégée | data.gouv.fr | Masse salariale sectorielle |

---

## COUCHE 11 — Immobilier & actifs physiques

| # | Source | URL | Apport |
|---|---|---|---|
| 70 | DVF / DVF+ | data.gouv.fr/dvf | Transactions immobilières depuis 2014 |
| 71 | API Cadastre (IGN) | api.gouv.fr/les-api/carto | Parcelles |
| 72 | BAN (Base Adresse Nationale) | adresse.data.gouv.fr | Normalisation adresses |
| 73 | BDNB | bdnb.io | Bâti national + DPE |
| 74 | ADEME DPE | observatoire-dpe.ademe.fr | Performance énergétique |
| 75 | IGN BD TOPO | geoservices.ign.fr | POI industriels |
| 76 | data.gouv RPG | data.gouv.fr/rpg | Parcellaire agricole |

---

## COUCHE 12 — Compliance & sanctions

| # | Source | URL | Apport |
|---|---|---|---|
| 77 | Gels des Avoirs DGTrésor | gels-avoirs.dgtresor.gouv.fr | Sanctions FR |
| 78 | EU Sanctions Map | sanctionsmap.eu | Sanctions UE |
| 79 | OFAC SDN (US) | home.treasury.gov/ofac | Sanctions US |
| 80 | UK HMT sanctions | gov.uk/ofsi | Sanctions UK |
| 81 | AMF listes noires | data.gouv.fr/amf | Entités non autorisées |
| 82 | ACPR REGAFI / REFASSU | regafi.fr | Banques/assurances autorisées |
| 83 | Bloctel | bloctel.gouv.fr | Liste opposition démarchage |

---

## COUCHE 13 — ESG, environnement, énergie

| # | Source | URL | Apport |
|---|---|---|---|
| 84 | ADEME Bilans GES | bilans-ges.ademe.fr | Émissions CO₂ obligatoires |
| 85 | ADEME Base Carbone | data.ademe.fr | Facteurs émission |
| 86 | EU ETS / EUTL | ec.europa.eu/clima/ets | Quotas CO₂ industriels |
| 87 | BASOL | basol.developpement-durable.gouv.fr | Sites pollués actifs |
| 88 | BASIAS | basias.brgm.fr | Anciens sites industriels |
| 89 | Inventaire ICPE | georisques.gouv.fr | Installations classées |
| 90 | GEOD'AIR / ATMO | geodair.fr | Émissions air |
| 91 | Agence de l'Eau | eaufrance.fr | Prélèvements industriels |
| 92 | Agribalyse | ademe.fr/agribalyse | ACV agricoles |
| 93 | ADEME Diag Eco-Flux | agirpourlatransition.ademe.fr | Audits énergétiques |
| 94 | RGE qualifications | france-renov.gouv.fr | Certifications travaux |

---

## COUCHE 14 — Lobbying & influence

| # | Source | URL | Apport |
|---|---|---|---|
| 95 | HATVP | hatvp.fr/open-data | Lobbying FR (3215+ représentants) |
| 96 | Registre Transparence UE | ec.europa.eu/transparencyregister | Lobbying Bruxelles |
| 97 | NosDéputés.fr / NosSénateurs | nosdeputes.fr | Auditions parlementaires |
| 98 | Transparence Santé | transparence.sante.gouv.fr | Paiements industrie↔médecins — ⚠️ **Données de santé (RGPD art. 9)** : conditions spéciales, DPIA dédié obligatoire avant ingestion |

---

## COUCHE 15 — Subventions & aides publiques

| # | Source | URL | Apport |
|---|---|---|---|
| 99 | FEDER bénéficiaires | europe-en-france.gouv.fr | Fonds européens développement régional |
| 100 | FEADER | agriculture.gouv.fr/feader | Fonds agricoles |
| 101 | FSE+ | fse.gouv.fr | Fonds social européen |
| 102 | ASP / Telepac | telepac.agriculture.gouv.fr | Aides PAC nominatives |
| 103 | Bpifrance Open Data | data.bpifrance.fr | Prêts, garanties publiées |
| 104 | aides-entreprises.fr | aides-entreprises.fr | Catalogue aides FR |
| 105 | France 2030 | info.gouv.fr/france2030 | Subventions innovation |

---

## COUCHE 16 — Web, digital & cyber (nouveau)

| # | Source | URL | Apport |
|---|---|---|---|
| 106 | Certificate Transparency (crt.sh) | crt.sh | Sous-domaines, projets cachés |
| 107 | Wayback Machine CDX API | archive.org/wayback | Historique sites web — ⚠️ **rate-limit agressif, bannissement fréquent** : usage parcimonieux (<100 req/h) |
| 108 | Common Crawl | commoncrawl.org | Corpus web mondial mensuel — ⚠️ **400 TB/dump** : compute massif requis, viable uniquement Y3+ avec Spark cluster |
| 109 | ~~AFNIC zone .fr~~ | ~~afnic.fr/donnees-partagees~~ | ⚠️ **Accès réservé recherche académique — usage commercial INTERDIT** : RETIRER du catalog ou demander accord commercial AFNIC (Y3) |
| 110 | RDAP / WHOIS | rdap.afnic.fr | Enregistrement domaines |
| 111 | GitHub API | api.github.com | Repos, employés tech, stack — ⚠️ **5 000 req/h auth** : ciblage sur 10-20k entreprises tech max Y1 (pas crawl 5M) |
| 112 | Stack Overflow | api.stackexchange.com | Communauté tech |
| 113 | Shodan free | shodan.io | ⚠️ **~100 queries/mois en free** : inutilisable à scale 5M, payer Shodan Membership ($59/mois) si besoin réel Y2 |
| 114 | Censys free | censys.io | ⚠️ **50 queries/mois en free** : inutilisable à scale, plan Pro $99/mois Y2 si besoin |
| 115 | BuiltWith / Wappalyzer OSS | wappalyzer.com | Stack web détectée |
| 116 | SecurityTrails free | securitytrails.com | Historique DNS |
| 117 | HaveIBeenPwned domain | haveibeenpwned.com | Fuites email entreprise — ⚠️ **Zone grise RGPD** : redistribuer fuites email = données personnelles "compromises" art. 9. À éviter Y1, DPIA dédié + base légale solide requis Y2+ |

---

## COUCHE 17 — Presse, signaux faibles, sentiment

| # | Source | URL | Apport |
|---|---|---|---|
| 118 | GDELT 2.0 | gdeltproject.org | 10M événements/jour mondial |
| 119 | Google News RSS | news.google.com/rss | ⚠️ **Mode "titre + URL + date" uniquement** (droits voisins presse) |
| 120 | Les Échos RSS | lesechos.fr/rss | ⚠️ **Mode "titre + URL + date" uniquement** |
| 121 | La Tribune RSS | latribune.fr/rss | ⚠️ **Mode "titre + URL + date" uniquement** |
| 122 | Usine Nouvelle RSS | usinenouvelle.com/rss | ⚠️ **Mode "titre + URL + date" uniquement** |
| 123 | CFNews RSS | cfnews.net | ⚠️ **Mode "titre + URL + date" uniquement** |
| 124 | Wikipedia / Wikidata | api.wikimedia.org | Notabilité, biographies (licence CC BY-SA, attribution requise) |
| 125 | ~~Trustpilot~~ | ~~trustpilot.com~~ | ⚠️ **RETIRÉ** : CGU interdisent scraping commercial. Re-évaluer Y3 via API Business officielle |
| 126 | ~~Google Reviews~~ | ~~maps.google.com~~ | ⚠️ **RETIRÉ** : CGU Google interdisent scraping. Pas d'API publique compatible |

---

## COUCHE 18 — Sectoriel spécialisé

| # | Secteur | Source | URL |
|---|---|---|---|
| 127 | Santé | ANSM | ansm.sante.fr |
| 128 | Santé | BDPM (médicaments) | base-donnees-publique.medicaments.gouv.fr |
| 129 | Santé | OpenMedic / OpenDamir | data.gouv.fr/ameli |
| 130 | Santé | RPPS | annuaire.sante.fr |
| 131 | ESS | Observatoire ESS France | ess-france.org |
| 132 | ESS | CGSCOP | les-scop.coop |
| 133 | Agri | Agreste | agreste.agriculture.gouv.fr |
| 134 | Transport | Registre transporteurs DREAL | data.gouv.fr/transporteurs |
| 135 | Finance | AMF GECO sociétés gestion | geco.amf-france.org |
| 136 | Assurance | ORIAS | orias.fr |

---

## COUCHE 19 — Europe & international

| # | Source | URL | Apport |
|---|---|---|---|
| 137 | BRIS (e-Justice EU) | e-justice.europa.eu/bris | Registres 27 pays UE |
| 138 | EBR (European Business Register) | ebr.org | Connecteur registres |
| 139 | Eurostat | ec.europa.eu/eurostat | Macro-éco UE |
| 140 | OECD Data | data.oecd.org | Indicateurs OCDE |
| 141 | World Bank Open Data | data.worldbank.org | Pays-clients/fournisseurs |
| 142 | Comtrade UN | comtrade.un.org | Commerce international |
| 143 | Douanes FR | lekiosque.finances.gouv.fr | Import/export agrégé par produit |

---

## ⭐ COUCHE 17bis — Sites web boutiques M&A (NOUVEAU, post-audit Q152)

> **Objectif** : alimenter `mart.who_advises_whom` (killer feature #2) **sans dépendre des droits voisins presse**. Les boutiques M&A publient volontairement leurs deals sur leurs propres sites (sections "Our Deals", "Track Record", "Transactions"). **Usage public légitime** = scraping autorisé.

| # | Acteur | URL deals | Volume estimé | Type |
|---|---|---|---|---|
| 144 | Cambon Partners | cambon.com/deals | ~30 deals/an | Boutique mid-market |
| 145 | Linklaters M&A FR | linklaters.com/fr | publié | Cabinet juridique |
| 146 | Oddo BHF Corp Finance | oddo-bhf.com | ~50/an | Banque d'aff. |
| 147 | Natixis Partners | natixis-partners.com | ~40/an | Banque d'aff. |
| 148 | Rothschild & Co FR | rothschildandco.com | publié | Banque d'aff. |
| 149 | Lazard FR | lazard.com/fr | publié | Banque d'aff. |
| 150 | Messier Maris & Associés | messier-maris.com | ~20/an | Boutique premium |
| 151 | BDO Corp Finance FR | bdo.fr | publié | Conseil M&A |
| 152 | Mazars Corp Finance FR | mazars.fr | publié | Conseil M&A |
| 153 | EY Parthenon FR | ey.com/fr_fr | publié | Conseil stratégie |
| 154 | DC Advisory | dcadvisory.com/fr | publié | Boutique cross-border |
| 155 | Edmond de Rothschild Corp Finance | edmond-de-rothschild.com | publié | Banque d'aff. |

> **Volume cumul cible V1 (Q4 2026)** : **3 000-5 000 deals FR historiques 2020-2026** (cohérent avec brochure "3 000+ deals indexés"). Approche : scraping respectueux (rate-limit, robots.txt, attribution) + validation humaine queue Notion.
>
> **Méthodologie** : Playwright + Crawlee + Mistral 7B (extraction structurée triplet `(cible, acquéreur, advisors[])`) — pas de fine-tuning.

---

## Matrice de priorité d'intégration (V2.1 — calendrier réel)

### 🎯 Top 20 Quick wins Q3 2026 (premier sprint post-closing pré-amorçage)

> Sources marquées 🎯 = **TOP 20 VALIDATION_API.md** à valider en priorité Q2-Q3 2026.

1. 🎯 **#1 API Recherche Entreprises** — fallback identification
2. 🎯 **#2 INSEE SIRENE V3 API** — deltas quotidiens
3. 🎯 **#3 INSEE SIRENE Stock Parquet** — bulk mensuel 5M SIREN
4. 🎯 **#4 INPI RNE** — 15M dirigeants
5. 🎯 **#5 annuaire-entreprises.data.gouv.fr** — vue consolidée
6. 🎯 **#6 data.gouv SIRENE géolocalisé** — coordonnées XY
7. 🎯 **#9 GLEIF** — LEI mondial
8. 🎯 **#10 OpenCorporates** ⚠️ snapshot 2019 gelé — alternative limitée
9. 🎯 **#12 OpenSanctions** — 200 listes mondiales consolidées
10. 🎯 **#30 BODACC** — 48M annonces, KILLER FEATURE #1 source
11. 🎯 **#34 Judilibre** — 5M décisions justice
12. 🎯 **#35 Légifrance** — JORF
13. 🎯 **#46 BOAMP** — appels d'offres
14. 🎯 **#47 DECP** — attributions marchés publics
15. 🎯 **#63 France Travail** — offres emploi (signaux RH)
16. 🎯 **#70 DVF** — transactions immobilières
17. 🎯 **#77 Gels Avoirs DGTrésor** — sanctions FR
18. 🎯 **#106 Certificate Transparency** ⚠️ rate-limited — signaux web M&A
19. 🎯 **#111 GitHub API** ⚠️ 5000 req/h auth — stack tech
20. 🎯 **#118 GDELT 2.0** — événements mondiaux (mode titre+URL+date)

### Priorité haute Y2 (2027)
- Couches 1-5 complètes (sources non-Top20), 7 (ownership), 8 (marchés publics), 10 (emploi)
- ⭐ Couche 17bis (sites M&A) **dès Q4 2026** pour killer feature #2
- Couche 9 (R&D), 11 (immobilier complémentaire)

### Priorité moyenne Y3 (2028)
- Couche 13 (ESG complet), 16 (web/digital approfondi)

### Priorité basse Y4 (2029)
- Couches 14 (lobbying), 15 (subventions), 17 (presse étendu), 18 (sectoriel), 19 (Europe/international)

---

## ⭐ SOURCES PAR KILLER FEATURE (NOUVEAU, post-audit V3)

### Killer feature #1 — Alertes pré-cession (livraison Q3 2026)

| Source | Rôle | Statut |
|---|---|---|
| **#30 BODACC** | Changements mandataires sociaux, modifications statuts, délégations AG | ✅ OK |
| **#4 INPI RNE** | Nominations, mandats, qualités | ✅ OK |
| **#31 Infogreffe Open Data** | Procédures collectives, RBE consolidé | ✅ OK |
| **#22 AMF BDIF** | Franchissements seuils (cotées) | ✅ OK |
| **#23 AMF GECO** | Décisions, agréments | ✅ OK |
| Référentiel `ref.fonds_pe` | Liste fonds PE FR (interne, ~400 fonds) | À constituer Q3 2026 |

**Statut global** : ✅ **Toutes les sources sont disponibles, licences OK, techniquement faisable**.

### Killer feature #2 — Who advises whom (livraison Q4 2026)

| Source | Rôle | Statut |
|---|---|---|
| ⭐ **Couche 17bis (sites M&A)** | **Source PRINCIPALE** : 3 000-5 000 deals historiques 2020-2026, publication volontaire = légal | ✅ Disponible (12 sites principaux listés) |
| **#22 AMF BDIF** | Communiqués deals cotées (~500/an) | ✅ OK |
| **#23 AMF GECO** | Décisions cotées | ✅ OK |
| **#124 Wikipedia/Wikidata** | Deals notables (CC BY-SA, attribution) | ✅ OK |
| **#119-123 Presse RSS** | ⚠️ Mode "titre+URL+date uniquement" → **insuffisant pour extraction triplet** | ⚠️ Limité (signal d'enrichissement uniquement) |
| Y2+ : Partenariat CFNews | Source presse N°1 deals FR (négociation 10-30k€/an) | ⏳ Y2 |
| Y2+ : Licence ADPI/CFC | Si scaling presse nécessaire (10-50k€/an) | ⏳ Y2 backup |

**Statut global** : ✅ **V1 réalisable Q4 2026 avec couche 17bis + AMF + Wikidata**. Volume cible 3 000-5 000 deals respecté. Pas de licence presse Y1.

### Module Compliance / KYC (livraison Q4 2026)

| Source | Rôle | Statut |
|---|---|---|
| **#12 OpenSanctions** | 200+ listes mondiales consolidées | ✅ OK |
| **#77 Gels DGTrésor** | Sanctions FR | ✅ OK |
| **#78 EU Sanctions Map** | UE | ✅ OK |
| **#79 OFAC SDN** | US (filiales US grands groupes) | ✅ OK |
| **#80 UK HMT** | UK (filiales UK) | ✅ OK |
| **#81 AMF listes noires** | Entités non autorisées FR | ✅ OK |

**Statut global** : ✅ **Toutes les sources OK, livraison Q4 2026 sans risque**.

### Scoring M&A v0 (livraison Q3 2026)

Croisement multi-sources : **#1-12** identification, **#16** comptes INPI, **#30** BODACC événements, **#34** Judilibre contentieux, **#46-47** marchés publics, **#51-52** brevets, **#63** France Travail (signaux RH), **#70** DVF (signaux immo), **#84** ADEME (ESG).

---

## Stratégie d'ingestion (V2.1 corrigée Q153+Q154)

> ⚠️ **Aucune source externe ne propose de webhook applicatif** (BODACC = JSON publié 1×/jour, Judilibre = REST polling, GDELT = dumps CSV 15min, CT = log stream non-applicatif, RSS = polling par définition). Toutes les ingestions "temps réel" se font par **polling incrémental + Dagster sensors**, pas par webhook.

| Fréquence | Sources | Stratégie technique (Y1-Y2) |
|---|---|---|
| **~1h (polling court)** | 30 BODACC (delta), 118 GDELT (15min), 106 CT (stream filter) | **Polling incrémental + Dagster sensors** (diff-based) |
| **Quotidien** | 2 INSEE deltas, 4 INPI, 34 Judilibre, 63 France Travail, 77-83 sanctions, 119-123 RSS presse | Dagster jobs nuit |
| **Hebdo** | 47 DECP, 46 BOAMP, 51-52 brevets | Batch hebdo |
| **Mensuel** | 3 SIRENE Stock, 17 ESANE, 70 DVF, 84 ADEME | **Batch DuckDB → Postgres** (ClickHouse seulement Y3+ quand >50M lignes événements, cf. ARCHITECTURE_TECHNIQUE.md) |
| **Annuel** | 16 Comptes annuels (parsing PDF), 84 ESG | Campagne annuelle |

---

## Conformité légale — CGU vérifiées

| Statut | Sources |
|---|---|
| ✅ Licence ouverte Etalab 2.0 (réutilisation libre) | 1-8, 30-33, 41, 46-50, 63-76, 84-105 |
| ✅ Licence ODbL (partage aux mêmes conditions) | 9, 10, 11 |
| ✅ API publique conditions standards | 22-29, 51-62 |
| ⚠️ Usage commercial à vérifier au cas par cas | 108, 118, 119-126 (presse — droits voisins) |
| ⚠️ RGPD sensible (données personnelles) | 4 (dirigeants), 98 (santé), 117 (fuites) |
| ❌ Scraping réseaux sociaux **interdit** dans cette archi | LinkedIn, Facebook, Instagram — exclus |

---

## Prochaines étapes

Voir :
- `ARCHITECTURE_TECHNIQUE.md` — comment ingérer ces 143 sources
- `ROADMAP_4ANS.md` — séquençage 2026-2029
- `RISQUES_CONFORMITE.md` — risques RGPD et mitigation

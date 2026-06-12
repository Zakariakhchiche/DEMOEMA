# Origin — Catalogue complet des sources du datalake

> Description de **toutes** les sources (≈ 60), regroupées par thème, avec pour chacune :
> ce qu'elle apporte, son volume, le fournisseur officiel, son **intérêt M&A**, et son **statut**
> (🟢 exploité dans le produit · 🟠 partiellement · ⚪ dormant = ingéré mais pas encore branché).

Dernière mise à jour : 2026-06-12.

---

## 🏢 1. Cœur entreprise — identité & financier

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `inpi_comptes_liasses` | 331,9 M | INPI | **Bilans détaillés** (CA, EBITDA, ratios) — le cœur financier de toute cible | 🟢 |
| `inpi_comptes_depots` / `_identite` | 6,2 M / 6,3 M | INPI | Métadonnées des dépôts (date, type, exercice) | 🟢 |
| `insee_sirene_siret_raw` | 43,3 M | INSEE | **Référentiel** : identité, NAF, capital, état, effectif, adresse | 🟢 |
| `inpi_formalites_entreprises` | 27,3 M | INPI RNE | Données légales entreprise (forme, immat.) | 🟢 |
| `inpi_formalites_etablissements` | 38,9 M | INPI RNE | Établissements, multi-sites (signal scale) | 🟢 |
| `inpi_formalites_activites` | 47,4 M | INPI RNE | Activités exercées par établissement | 🟢 |
| `inpi_formalites_observations` | 10,4 M | INPI RNE | Observations/mentions au registre | 🟠 |
| `inpi_formalites_historique` | 9,5 M | INPI RNE | Historique des modifications (changements de contrôle) | 🟠 |
| `inpi_formalites_inscriptions_offices` | 888 k | INPI | Inscriptions/privilèges (signal de tension) | ⚪ |
| `recherche_entreprises_raw` | 966 | API gouv | Fallback résolution SIREN par nom | 🟢 |
| `gleif_lei_raw` | 20,8 k | GLEIF | **Code LEI** = entité régulée/internationale (signal scale, cotation) | 🟠 |
| `wikidata_entreprises_raw` | 41,8 k | Wikidata | Notoriété, bio, occupation (enrichissement) | 🟠 |

---

## 👤 2. Dirigeants & personnes

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `inpi_formalites_personnes` | 15,0 M | INPI RNE | **Dirigeants, mandats, âges** — base du scoring transmission & réseau | 🟢 |
| `hatvp_representants_raw` | 459 k | HATVP | Lobbyistes inscrits (signal d'influence/compliance) | 🟢 |
| `transparence_sante_raw` | 11,5 k | Transparence Santé | Paiements pharma aux dirigeants (conflits d'intérêt / KOL) | ⚪ |
| `nosdeputes_raw` | 618 | NosDéputés | Élus / mandats publics (compliance PEP) | ⚪ |
| `rpps_professionnels_raw` | 1 | RPPS | Professionnels de santé (secteur médical) | ⚪ |

---

## ⚖️ 3. Signaux légaux & événements M&A

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `bodacc_annonces_raw` | 30,3 M | DILA / JO | **Procédures collectives, cessions, ventes** → killer feature pré-cession | 🟢 |
| `judilibre_decisions_raw` | 264 k | Cour de cassation | Décisions de justice (contentieux = red flag DD) | 🟠 |
| `juri_capp_raw` | 174 k | Cours d'appel | Jurisprudence appel | 🟠 |
| `juri_jade_raw` | 19,6 k | Conseil d'État | Jurisprudence administrative | ⚪ |
| `juri_constit_raw` | 11,6 k | Conseil constitutionnel | Décisions constitutionnelles | ⚪ |
| `amf_dila_raw` | 30,7 k | AMF | Sanctions/décisions marchés financiers | 🟠 |
| `legifrance_textes_raw` | 344 k | Légifrance | Textes réglementaires (veille sectorielle) | ⚪ |
| `jorf_textes_raw` | 306 k | Journal Officiel | Textes du JO | ⚪ |
| `kali_ccn_raw` | 158 k | Légifrance | Conventions collectives (coûts sociaux, secteur) | ⚪ |
| `bocc_avenants_raw` | 10 | DILA | Avenants conventions collectives | ⚪ |
| `cnil_deliberations_raw` | 287 | CNIL | Sanctions RGPD/données | 🟢 |
| `dgccrf_sanctions_raw` | 104 | DGCCRF | Sanctions concurrence/conso | 🟢 |

---

## 🛡️ 4. Compliance & risque international

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `opensanctions_entities_raw` | 496 k | OpenSanctions | **Sanctions OFAC/UE/UK/ONU + PEP** — deal-killer | 🟢 |
| `icij_offshore_raw` | 1,6 M | ICIJ | **Liens offshore** (Panama/Paradise Papers) | 🟢 |

---

## 🏠 5. Patrimoine immobilier & environnement

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `dvf_transactions_raw` | 15,0 M | DGFiP | **Transactions immobilières** → patrimoine dirigeant, asset-rich | 🟢 |
| `api_cadastre_ign_raw` | 31,0 k | IGN | Parcelles cadastrales (localisation actifs) | 🟠 |
| `ban_adresses_raw` | 12,4 k | BAN | Géocodage des adresses | 🟠 |
| `basias_sites_raw` | 12,5 k | BRGM | **Sites pollués** (passif environnemental = coût dépollution) | ⚪ |
| `basol_sites_raw` | 162 | Min. Écologie | Sites pollués (BASOL, pollution avérée) | ⚪ |
| `ademe_dpe_raw` | 12 | ADEME | Diagnostics de performance énergétique | ⚪ |

---

## 💡 6. Innovation, propriété intellectuelle & R&D

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `inpi_marques_raw` | 116 k | INPI | Marques déposées (actif incorporel) | ⚪* |
| `inpi_brevets_raw` | 10,0 k | INPI | Brevets (valeur techno) | ⚪* |
| `crossref_works_raw` | 29,9 k | Crossref | Publications scientifiques (intensité R&D) | ⚪ |
| `hal_publications_raw` | 46,5 k | HAL | Publications académiques FR | ⚪ |
| `openalex_works_raw` | 1,0 k | OpenAlex | Publications (graphe scientifique) | ⚪ |

*\* marques/brevets : ingérés mais le SIREN du titulaire n'est pas dans le payload → non joignable en l'état (chantier ré-extraction).*

---

## 🏛️ 7. Commande publique

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `decp_marches_raw` | 17,9 k | DGFiP/DECP | Marchés publics attribués (dépendance/stabilité du CA) | ⚪* |
| `boamp_avis_raw` | 22,1 k | DILA/BOAMP | Avis de marchés publics | ⚪* |

*\* siret titulaire non extrait → non joignable en l'état.*

---

## 🧪 8. Santé / pharma / agro (sectoriel)

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `ansm_decisions_raw` | 8,4 k | ANSM | Décisions médicament (risque réglementaire pharma) | ⚪ |
| `bdpm_medicaments_raw` | 8,4 k | ANSM/BDPM | Base médicaments (portefeuille produit pharma) | ⚪ |
| `agribalyse_products_raw` | 2,0 k | ADEME | ACV produits agroalimentaires | ⚪ |

---

## 🌍 9. Macro-économie & commerce

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `douanes_fr_raw` | 10,0 k | Douanes | Import/export (exposition internationale réelle) | ⚪ |
| `urssaf_opendata_raw` | 10,0 k | URSSAF | Données sociales agrégées (proxy dette sociale) | ⚪ |
| `world_bank_indicators_raw` | 15,9 k | World Bank | Indicateurs macro (contexte pays/secteur) | ⚪ |
| `bdf_webstat_raw` | 132 | Banque de France | Statistiques financières BdF | ⚪ |

---

## 🌱 10. ESG & environnement

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `ademe_bilans_ges_raw` | 5,1 k | ADEME | Bilans carbone (CSRD, due diligence ESG) | ⚪ |

---

## 💶 11. Aides publiques & subventions

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `fse_raw` | 567 k | Fonds Social Européen | Bénéficiaires d'aides FSE | ⚪ |
| `feder_raw` | 544 | FEDER | Aides régionales européennes | ⚪ |
| `aides_entreprises_raw` | 229 | aides-entreprises.fr | Dispositifs d'aide | ⚪ |
| `dole_dossiers_raw` | 263 | Min. Travail | Accords d'entreprise | ⚪ |

---

## 📰 12. Presse, OSINT & associations

| Source | Volume | Fournisseur | Intérêt M&A | Statut |
|---|---|---|---|---|
| `osint_companies` | 11,4 k | Scan web | **Présence digitale** (domaine, maturité web) | 🟢 |
| `osint_persons` | 2,1 k | Scan web (Maigret) | Profils sociaux dirigeants (LinkedIn…) | 🟠 |
| `press_articles_raw` | 7,5 k | Presse | Articles (sentiment, actualité cible) | ⚪ |
| `google_news_raw` | 6,6 k | Google News | Actualité temps réel | ⚪ |
| `rna_associations_raw` | 620 k | RNA | Répertoire des associations (secteur ESS) | ⚪ |

---

## 📊 Synthèse par statut

| Statut | Nb sources | Lecture |
|---|---|---|
| 🟢 **Exploité** (branché produit) | ~15 | Le cœur : identité, financier, dirigeants, BODACC, sanctions, DVF, OSINT |
| 🟠 **Partiel** | ~10 | Branché mais sous-exploité (judilibre, LEI, cadastre, AMF…) |
| ⚪ **Dormant** | ~35 | Ingéré, à fort potentiel mais pas encore relié (sites pollués, marchés publics, R&D, ESG, douanes, presse…) |

**Le moat** : ~580 M de lignes de données publiques officielles déjà ingérées. Le produit en exploite
aujourd'hui le cœur (~15 sources) ; les ~35 sources dormantes sont une **roadmap d'enrichissement**
(passif environnemental, dépendance commande publique, IP, ESG, contentieux…) — la matière est là,
il reste à la relier (souvent un chantier de ré-extraction du SIREN).

---

*Origin — catalogue généré depuis l'inventaire réel (pg_stat_user_tables, 2026-06-12).*

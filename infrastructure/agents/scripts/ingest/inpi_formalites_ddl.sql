-- Bronze tables INPI RNE formalités — schéma COMPLET couvrant 525 champs.
-- Union personneMorale + personnePhysique + exploitation (types P/M/E).
-- Chaque table garde aussi payload jsonb pour les champs non extraits + futures évolutions.

-- ============================================================================
-- 1) ENTREPRISES — core entity (1 row par SIREN / formality)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bronze.inpi_formalites_entreprises (
    formality_id                 text PRIMARY KEY,
    siren                        char(9),
    type_personne                varchar(4),            -- P / M / E / null
    updated_at_src               timestamptz,
    ingested_at                  timestamptz NOT NULL DEFAULT now(),
    nombre_etablissements_ouverts int,
    nombre_representants_actifs   int,
    siren_doublons               text[],
    diffusion_commerciale        boolean,
    diffusion_insee              boolean,
    forme_juridique              varchar(8),
    forme_exercice_activite_principale varchar(32),
    indicateur_structure_etablissement text,
    -- identite
    denomination                 text,
    sigle                        text,
    nom_commercial               text,
    nom_exploitation             text,
    code_ape                     varchar(8),
    date_debut_activite          date,
    date_immatriculation         date,
    effectif_salarie             int,
    effectif_apprenti            int,
    nombre_salarie               int,
    nic_siege                    varchar(5),
    -- description (personne morale surtout)
    objet                        text,
    forme_statuts                varchar(32),
    duree_annees                 int,
    date_cloture_exercice_social varchar(10),   -- "MM-DD"
    date_premiere_cloture        date,
    date_fin_existence           date,
    date_effet_25m               date,
    montant_capital              numeric,
    devise_capital               char(3),
    capital_variable             boolean,
    capital_minimum              numeric,
    indicateur_associe_unique    boolean,
    indicateur_associe_unique_dirigeant boolean,
    nature_gerance               text,
    ess                          boolean,               -- Économie Sociale et Solidaire
    societe_mission              boolean,
    continuation_actif_net_inf_moitie_capital boolean,
    -- entrepreneur (personne physique uniquement)
    entrepreneur_nom             text,
    entrepreneur_nom_usage       text,
    entrepreneur_prenoms         text[],
    entrepreneur_pseudonyme      text,
    entrepreneur_date_naissance  varchar(10),
    entrepreneur_siren           char(9),
    entrepreneur_qualite_artisan boolean,
    -- conjoint (personne physique)
    conjoint_nom                 text,
    conjoint_nom_usage           text,
    conjoint_prenoms             text[],
    conjoint_date_naissance      varchar(10),
    role_conjoint                varchar(32),
    -- nature création / cessation
    date_radiation               date,
    -- adresse siège (aplati)
    adresse_code_postal          varchar(10),
    adresse_commune              text,
    adresse_code_insee_commune   varchar(5),
    adresse_voie                 text,
    adresse_type_voie            varchar(8),
    adresse_num_voie             varchar(10),
    adresse_indice_repetition    varchar(4),
    adresse_complement           text,
    adresse_code_pays            varchar(3),
    adresse_pays                 text,
    adresse_distribution_speciale text,
    adresse_domiciliataire       boolean,
    -- noms de domaine (array car N)
    noms_de_domaine              text[],
    -- registre antérieur
    rncs_date_debut              date,
    rncs_date_fin                date,
    rnm_date_debut               date,
    rnm_date_fin                 date,
    -- structure entreprise (holdings)
    structure_entreprise_payload jsonb,
    -- full raw backup
    payload                      jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_f_ent_siren         ON bronze.inpi_formalites_entreprises(siren);
CREATE INDEX IF NOT EXISTS idx_f_ent_forme_jur     ON bronze.inpi_formalites_entreprises(forme_juridique);
CREATE INDEX IF NOT EXISTS idx_f_ent_type_personne ON bronze.inpi_formalites_entreprises(type_personne);
CREATE INDEX IF NOT EXISTS idx_f_ent_date_immat    ON bronze.inpi_formalites_entreprises(date_immatriculation DESC);
CREATE INDEX IF NOT EXISTS idx_f_ent_code_ape      ON bronze.inpi_formalites_entreprises(code_ape);
CREATE INDEX IF NOT EXISTS idx_f_ent_cp            ON bronze.inpi_formalites_entreprises(adresse_code_postal);

-- ============================================================================
-- 2) ÉTABLISSEMENTS (principal + secondaires + exploitation)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bronze.inpi_formalites_etablissements (
    etablissement_uid            text PRIMARY KEY,      -- formality_id || '#' || siret || '#' || index
    formality_id                 text NOT NULL,
    siren                        char(9),
    siret                        char(14),
    is_principal                 boolean,
    role_etablissement           varchar(32),
    role_pour_entreprise         varchar(32),
    -- description
    code_ape                     varchar(8),
    enseigne                     text,
    nom_commercial               text,
    destination_etablissement    text,
    autre_destination            text,
    activite_non_sedentaire      boolean,
    -- dates
    date_effet_fermeture         date,
    date_effet_transfert         date,
    date_fin_activite            date,
    -- flags
    indicateur_suppression       boolean,
    motif_suppression            text,
    etablissement_rdd            boolean,
    statut_pour_formalite        varchar(32),
    -- cessation (établissement)
    cessation_date_effet         date,
    cessation_date_radiation     date,
    cessation_date_totale_activite date,
    cessation_date_activite_salariee date,
    cessation_destination        text,
    -- location gérance
    is_location_gerance_ou_mandat boolean,
    domiciliataire_denomination  text,
    domiciliataire_siren         char(9),
    -- adresse (aplati)
    adresse_code_postal          varchar(10),
    adresse_commune              text,
    adresse_code_insee_commune   varchar(5),
    adresse_voie                 text,
    adresse_type_voie            varchar(8),
    adresse_num_voie             varchar(10),
    adresse_indice_repetition    varchar(4),
    adresse_complement           text,
    adresse_commune_ancienne     text,
    adresse_code_pays            varchar(3),
    adresse_pays                 text,
    adresse_distribution_speciale text,
    adresse_ambulant             boolean,
    adresse_domiciliataire       boolean,
    -- registre antérieur (établissement)
    rncs_date_debut              date,
    rncs_date_fin                date,
    rnm_date_debut               date,
    rnm_date_fin                 date,
    raa_date_debut               date,
    -- full payload
    payload                      jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_f_etab_siren        ON bronze.inpi_formalites_etablissements(siren);
CREATE INDEX IF NOT EXISTS idx_f_etab_siret        ON bronze.inpi_formalites_etablissements(siret);
CREATE INDEX IF NOT EXISTS idx_f_etab_principal    ON bronze.inpi_formalites_etablissements(is_principal) WHERE is_principal = true;
CREATE INDEX IF NOT EXISTS idx_f_etab_cp           ON bronze.inpi_formalites_etablissements(adresse_code_postal);
CREATE INDEX IF NOT EXISTS idx_f_etab_formality    ON bronze.inpi_formalites_etablissements(formality_id);

-- ============================================================================
-- 3) ACTIVITÉS (par établissement, N lignes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bronze.inpi_formalites_activites (
    activite_uid                 text PRIMARY KEY,
    etablissement_uid            text NOT NULL,
    formality_id                 text,
    siren                        char(9),
    siret                        char(14),
    activite_id                  text,
    code_ape                     varchar(8),
    code_aprm                    varchar(8),
    category_code                varchar(16),
    cat_1                        text,
    cat_2                        text,
    cat_3                        text,
    cat_4                        text,
    indicateur_principal         boolean,
    indicateur_prolongement      boolean,
    indicateur_artiste_auteur    boolean,
    indicateur_non_sedentaire    boolean,
    indicateur_activitee_ape     boolean,
    forme_exercice               varchar(32),
    exercice_activite            text,
    description_detaillee        text,
    precision_activite           text,
    precision_autre              text,
    qualite_non_sedentaire       text,
    role_principal_pour_entreprise varchar(32),
    date_debut                   date,
    date_fin                     date,
    soumission_au_precompte      boolean,
    activite_rattachee_eirl      boolean,
    locataire_gerant_mandat      text,
    origine_type                 varchar(32),
    origine_autre                text,
    origine_pub_date             date,
    origine_pub_journal          text,
    origine_pub_url              text,
    payload                      jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_f_act_siren         ON bronze.inpi_formalites_activites(siren);
CREATE INDEX IF NOT EXISTS idx_f_act_code_ape      ON bronze.inpi_formalites_activites(code_ape);
CREATE INDEX IF NOT EXISTS idx_f_act_principal     ON bronze.inpi_formalites_activites(indicateur_principal) WHERE indicateur_principal = true;
CREATE INDEX IF NOT EXISTS idx_f_act_etab          ON bronze.inpi_formalites_activites(etablissement_uid);

-- ============================================================================
-- 4) PERSONNES / POUVOIRS (dirigeants + représentants)
--    Union individu (physique) + entreprise (morale) — colonnes nullables selon le type
-- ============================================================================
CREATE TABLE IF NOT EXISTS bronze.inpi_formalites_personnes (
    representant_id              text PRIMARY KEY,
    formality_id                 text NOT NULL,
    siren                        char(9),               -- SIREN de l'entreprise représentée
    type_de_personne             varchar(16),           -- INDIVIDU / ENTREPRISE
    actif                        boolean,
    role_entreprise              varchar(16),           -- code (ex: "73")
    autre_role_entreprise        text,
    second_role_entreprise       varchar(16),
    libelle_second_role_entreprise text,
    indicateur_second_role       boolean,
    indicateur_actif_agricole    boolean,
    qualite_artisan              boolean,
    -- individu (personne physique)
    individu_nom                 text,
    individu_nom_usage           text,
    individu_prenoms             text[],
    individu_date_naissance      varchar(10),
    individu_role                varchar(16),
    individu_date_effet_role     date,
    individu_adresse_code_postal varchar(10),
    individu_adresse_commune     text,
    individu_adresse_code_insee_commune varchar(5),
    individu_adresse_pays        text,
    individu_adresse_code_pays   varchar(3),
    -- representant (dans certains cas — délégué du dirigeant morale)
    representant_nom             text,
    representant_nom_usage       text,
    representant_prenoms         text[],
    representant_date_naissance  varchar(10),
    representant_adresse_code_postal varchar(10),
    representant_adresse_commune text,
    -- entreprise (personne morale dirigeante)
    entreprise_siren             char(9),
    entreprise_denomination      text,
    entreprise_forme_juridique   varchar(8),
    entreprise_role_entreprise   varchar(16),
    entreprise_indicateur_associe_unique boolean,
    entreprise_lieu_registre     text,
    entreprise_pays              text,
    entreprise_adresse_code_postal varchar(10),
    entreprise_adresse_commune   text,
    -- full payload
    payload                      jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_f_pers_siren             ON bronze.inpi_formalites_personnes(siren);
CREATE INDEX IF NOT EXISTS idx_f_pers_entreprise_siren  ON bronze.inpi_formalites_personnes(entreprise_siren) WHERE entreprise_siren IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_f_pers_nom_prenom        ON bronze.inpi_formalites_personnes(individu_nom, (individu_prenoms[1]));
CREATE INDEX IF NOT EXISTS idx_f_pers_dob               ON bronze.inpi_formalites_personnes(individu_date_naissance);
CREATE INDEX IF NOT EXISTS idx_f_pers_role              ON bronze.inpi_formalites_personnes(role_entreprise);
CREATE INDEX IF NOT EXISTS idx_f_pers_type              ON bronze.inpi_formalites_personnes(type_de_personne);

-- ============================================================================
-- 5) OBSERVATIONS (modifications statutaires — signaux M&A)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bronze.inpi_formalites_observations (
    observation_uid              text PRIMARY KEY,
    formality_id                 text NOT NULL,
    siren                        char(9),
    date_observation             date,
    type_observation             text,
    libelle                      text,
    payload                      jsonb
);
CREATE INDEX IF NOT EXISTS idx_f_obs_siren             ON bronze.inpi_formalites_observations(siren);
CREATE INDEX IF NOT EXISTS idx_f_obs_date              ON bronze.inpi_formalites_observations(date_observation DESC);

-- ============================================================================
-- 6) HISTORIQUE (événements chronologiques entreprise)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bronze.inpi_formalites_historique (
    historique_uid               text PRIMARY KEY,
    formality_id                 text NOT NULL,
    siren                        char(9),
    patch_id                     text,
    numero_liasse                text,
    libelle_evenement            text,
    date_integration             timestamptz,
    payload                      jsonb
);
CREATE INDEX IF NOT EXISTS idx_f_hist_siren         ON bronze.inpi_formalites_historique(siren);
CREATE INDEX IF NOT EXISTS idx_f_hist_date          ON bronze.inpi_formalites_historique(date_integration DESC);

-- ============================================================================
-- 7) INSCRIPTIONS OFFICES (greffes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bronze.inpi_formalites_inscriptions_offices (
    inscription_uid              text PRIMARY KEY,
    formality_id                 text NOT NULL,
    siren                        char(9),
    office_code                  text,
    office_libelle               text,
    payload                      jsonb
);
CREATE INDEX IF NOT EXISTS idx_f_insc_siren         ON bronze.inpi_formalites_inscriptions_offices(siren);

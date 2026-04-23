-- Bronze tables OSINT — enrichissement dirigeants/BE + entreprises cibles

CREATE TABLE IF NOT EXISTS bronze.osint_persons (
    person_uid       text PRIMARY KEY,         -- sha1(nom|prenom|date_naissance|siren_main)
    siren_main       char(9),                  -- SIREN de la société principale
    representant_id  text,                     -- FK vers inpi_formalites_personnes.representant_id
    nom              text,
    prenoms          text[],
    date_naissance   varchar(10),
    -- Profils sociaux découverts
    linkedin_urls    text[],
    github_usernames text[],
    twitter_handles  text[],
    instagram_handles text[],
    medium_profiles  text[],
    crunchbase_url   text,
    facebook_urls    text[],
    youtube_channels text[],
    other_sites      jsonb,                    -- tout le rest (3000+ sites Maigret)
    -- Emails testés
    emails_tested    text[],
    emails_valid     text[],
    email_services   jsonb,                    -- {email: [linkedin, twitter, spotify, ...]}
    -- Metadata
    sources_scanned  text[],                   -- ["maigret","holehe","sherlock","manual"]
    last_scanned_at  timestamptz,
    ingested_at      timestamptz NOT NULL DEFAULT now(),
    payload          jsonb                     -- raw tool outputs
);
CREATE INDEX IF NOT EXISTS idx_osint_p_siren ON bronze.osint_persons(siren_main);
CREATE INDEX IF NOT EXISTS idx_osint_p_repr  ON bronze.osint_persons(representant_id);
CREATE INDEX IF NOT EXISTS idx_osint_p_scan  ON bronze.osint_persons(last_scanned_at DESC);


CREATE TABLE IF NOT EXISTS bronze.osint_companies (
    siren              char(9) PRIMARY KEY,
    domains            text[],                 -- sites web + subdomains
    subdomains_crt_sh  text[],                 -- via Certificate Transparency
    github_org         text,
    linkedin_company_url text,
    linkedin_employees int,
    twitter_handle     text,
    facebook_page      text,
    youtube_channel    text,
    tech_stack         jsonb,                  -- via Wappalyzer/BuiltWith
    similar_domains    text[],                 -- via DNSTwist
    email_patterns     text[],                 -- patterns détectés (prenom.nom@, etc.)
    whois              jsonb,                  -- RDAP data
    sources_scanned    text[],
    last_scanned_at    timestamptz,
    ingested_at        timestamptz NOT NULL DEFAULT now(),
    payload            jsonb
);
CREATE INDEX IF NOT EXISTS idx_osint_c_scan ON bronze.osint_companies(last_scanned_at DESC);


CREATE TABLE IF NOT EXISTS bronze.osint_relationships (
    rel_uid            text PRIMARY KEY,       -- sha1(source|target|type)
    source_person_uid  text,                   -- peut être null si source = siren (B2B)
    source_siren       char(9),
    target_person_uid  text,
    target_siren       char(9),
    relationship_type  text,                   -- board_member, co_investor, advisor, common_school, common_employer, common_domain
    source_dataset     text,                   -- inpi_rne, linkedin, crunchbase, presse, crt_sh
    evidence           jsonb,
    confidence         numeric(3,2),           -- 0.00-1.00
    first_seen_at      timestamptz,
    last_confirmed_at  timestamptz,
    ingested_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_osint_r_src_pers ON bronze.osint_relationships(source_person_uid);
CREATE INDEX IF NOT EXISTS idx_osint_r_tgt_pers ON bronze.osint_relationships(target_person_uid);
CREATE INDEX IF NOT EXISTS idx_osint_r_src_sir  ON bronze.osint_relationships(source_siren);
CREATE INDEX IF NOT EXISTS idx_osint_r_tgt_sir  ON bronze.osint_relationships(target_siren);
CREATE INDEX IF NOT EXISTS idx_osint_r_type     ON bronze.osint_relationships(relationship_type);

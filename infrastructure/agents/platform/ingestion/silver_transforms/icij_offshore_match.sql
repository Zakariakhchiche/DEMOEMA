-- silver.icij_offshore_match — SQL ÉCRIT À LA MAIN (déterministe, sans LLM).
-- Marqué `hand_authored: true` dans le spec → le moteur applique ce fichier tel
-- quel ; le maintainer ne le régénère via LLM que si l'apply/refresh échoue.
--
-- But : match dirigeants FR (silver.inpi_dirigeants) ↔ entités offshore ICIJ
-- (bronze.icij_offshore_raw, ~1,59M lignes — Panama/Paradise/Pandora/Bahamas/
-- Offshore Leaks). Red flag DD anti-blanchiment.
--
-- ⚠️ Pourquoi cette réécriture : l'ancienne version (désactivée) joignait via
--    `officer_name ILIKE '%' || nom || '%'` — wildcard en tête, non indexable,
--    quasi-produit cartésien 1,5M × 8,1M → process bloqué à l'infini (à l'origine
--    de la désactivation et des backends zombies). Ici : JOIN par ÉGALITÉ sur une
--    clé de nom normalisée (unaccent+lower+espaces compactés) → hash join borné.
--    Et person_uid est CALCULÉ (md5 nom|prenom|date_naissance), car
--    silver.inpi_dirigeants n'a pas de colonne person_uid.

CREATE MATERIALIZED VIEW silver.icij_offshore_match AS
WITH icij_all AS (
    SELECT
        node_id            AS icij_entity_id,
        name               AS icij_entity_name,
        lower(source_leak) AS icij_database,
        country            AS jurisdiction,
        role,
        regexp_replace(lower(unaccent(name)), '\s+', ' ', 'g') AS name_key
    FROM bronze.icij_offshore_raw
    WHERE name IS NOT NULL
      AND length(name) >= 6
      AND position(' ' IN btrim(name)) > 0            -- au moins 2 tokens (nom complet)
),
-- Garde-fou fréquence : un nom offshore qui revient >10 fois est un nom commun
-- (ou une entité générique) → match non actionnable en DD. On l'écarte. Borne
-- aussi le many×many qui faisait exploser l'estimation à ~1,2 Md de lignes.
icij_persons AS (
    SELECT i.*
    FROM icij_all i
    JOIN (
        SELECT name_key FROM icij_all GROUP BY name_key HAVING count(*) <= 10
    ) f USING (name_key)
),
dirigeant_all AS (
    -- deux variantes d'ordre (prénom nom / nom prénom) pour l'équi-jointure
    SELECT
        md5(coalesce(d.nom,'') || '|' || coalesce(d.prenom,'') || '|' || coalesce(d.date_naissance,'')) AS person_uid,
        d.nom,
        d.prenom,
        d.date_naissance,
        d.sirens_mandats,
        length(d.nom) AS nom_len,
        k.name_key
    FROM silver.inpi_dirigeants d
    CROSS JOIN LATERAL (VALUES
        (regexp_replace(lower(unaccent(coalesce(d.prenom,'') || ' ' || coalesce(d.nom,''))), '\s+', ' ', 'g')),
        (regexp_replace(lower(unaccent(coalesce(d.nom,'') || ' ' || coalesce(d.prenom,''))), '\s+', ' ', 'g'))
    ) AS k(name_key)
    WHERE d.nom IS NOT NULL
      AND d.prenom IS NOT NULL
      AND length(d.nom) >= 4                           -- évite les noms trop courts (homonymes)
),
-- Garde-fou fréquence côté dirigeants : on ne garde que les noms portés par <= 3
-- personnes distinctes (nom distinctif). Un "jean martin" partagé par 500
-- dirigeants n'est pas exploitable en DD et créerait du many×many.
dirigeant_keys AS (
    SELECT d.*
    FROM dirigeant_all d
    JOIN (
        SELECT name_key FROM dirigeant_all GROUP BY name_key HAVING count(DISTINCT person_uid) <= 3
    ) f USING (name_key)
),
matched AS (
    SELECT DISTINCT ON (dk.person_uid, o.icij_entity_id)
        md5(o.icij_entity_id || '|' || dk.person_uid) AS match_uid,
        dk.person_uid,
        dk.nom,
        dk.prenom,
        dk.date_naissance,
        dk.sirens_mandats,
        o.icij_entity_id,
        o.icij_entity_name,
        o.icij_database,
        o.jurisdiction,
        o.role,
        -- confiance : nom long (rare) → HIGH ; sinon MEDIUM (homonyme possible).
        -- Pas de 'LOW' fuzzy : c'était le bruit + la bombe perf de l'ancienne version.
        CASE WHEN dk.nom_len >= 6 THEN 'HIGH' ELSE 'MEDIUM' END AS match_confidence
    FROM dirigeant_keys dk
    JOIN icij_persons o ON o.name_key = dk.name_key
    ORDER BY dk.person_uid, o.icij_entity_id, match_confidence   -- 'HIGH' < 'MEDIUM' → garde HIGH
)
SELECT
    match_uid,
    person_uid,
    nom,
    prenom,
    date_naissance,
    sirens_mandats,
    icij_entity_id,
    icij_entity_name,
    icij_database,
    jurisdiction,
    role,
    match_confidence,
    now() AS materialized_at
FROM matched;

CREATE UNIQUE INDEX idx_icij_match_uid       ON silver.icij_offshore_match (match_uid);
CREATE INDEX        idx_icij_person_uid      ON silver.icij_offshore_match (person_uid);
CREATE INDEX        idx_icij_confidence      ON silver.icij_offshore_match (match_confidence);
CREATE INDEX        idx_icij_database        ON silver.icij_offshore_match (icij_database);
CREATE INDEX        idx_icij_nom_prenom      ON silver.icij_offshore_match (nom, prenom);
CREATE INDEX        idx_icij_sirens_mandats  ON silver.icij_offshore_match USING gin (sirens_mandats);

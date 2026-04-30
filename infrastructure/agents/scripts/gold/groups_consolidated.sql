-- gold.groups_consolidated v1 MVP — détection groupe + agrégation comptes
--
-- Layer 1 : détection groupe via 3 méthodes (LEI > dirigeants > adresse)
-- Layer 2 : SUM des comptes filiales par ultimate_parent
-- Confidence selon méthode (LEI=0.95, dirigeants=0.7, adresse=0.4)
--
-- Différenciateur DEMOEMA : approxime ce que Pappers Premium / Ellisphere
-- font à 1500€+/mois. Pour les groupes sans URD (pas cotés), c'est la seule
-- source publique gratuite.

SET statement_timeout = 0;
DROP TABLE IF EXISTS gold.groups_consolidated CASCADE;

CREATE TABLE gold.groups_consolidated AS
WITH
-- ───── Méthode 1 : LEI ultimate_parent (confidence 0.95)
-- Le groupe LEI est officiellement déclaré (réglementation EU/USA).
lei_groups AS (
    SELECT
        l.siren_fr AS member_siren,
        coalesce(l.ultimate_parent_lei, l.parent_lei) AS group_lei,
        'lei' AS detection_method,
        0.95::numeric AS confidence
    FROM silver.gleif_lei l
    WHERE l.siren_fr IS NOT NULL
      AND coalesce(l.ultimate_parent_lei, l.parent_lei) IS NOT NULL
),

-- Map LEI groupe → siren parent (la mère a son propre LEI = ultimate_parent_lei)
lei_parent_map AS (
    SELECT
        l.lei AS group_lei,
        l.siren_fr AS parent_siren,
        l.legal_name AS parent_name
    FROM silver.gleif_lei l
    WHERE l.siren_fr IS NOT NULL
),

-- ───── Méthode 2 : dirigeants communs via silver.inpi_dirigeants
-- Filter strict pour éviter explosion :
--   - is_multi_mandat = true (dirigeant a >= 2 mandats actifs)
--   - n_mandats_actifs in [2, 20] (exclut concentrateurs CAC type avocat)
--   - array_length(sirens_mandats) >= 2
-- → 60-100k personnes max (pas 8M)
multi_dir AS (
    SELECT
        nom, prenom, date_naissance,
        sirens_mandats,
        n_mandats_actifs,
        md5(coalesce(nom,'')||'|'||coalesce(prenom,'')||'|'||coalesce(date_naissance,'')) AS person_uid
    FROM silver.inpi_dirigeants
    WHERE is_multi_mandat = true
      AND n_mandats_actifs BETWEEN 2 AND 20
      AND sirens_mandats IS NOT NULL
      AND array_length(sirens_mandats, 1) BETWEEN 2 AND 20
),
-- Paire (siren_a, siren_b) si ≥ 2 dirigeants partagés
dirig_pairs AS (
    SELECT
        a.siren AS siren_a,
        b.siren AS siren_b,
        count(DISTINCT m.person_uid) AS n_dirig_communs
    FROM multi_dir m
    CROSS JOIN LATERAL unnest(m.sirens_mandats) AS a(siren)
    CROSS JOIN LATERAL unnest(m.sirens_mandats) AS b(siren)
    WHERE a.siren < b.siren
    GROUP BY a.siren, b.siren
    HAVING count(DISTINCT m.person_uid) >= 2
),
-- Composantes connexes simplifiées (1 hop) — racine = min siren du cluster
dirig_groups_raw AS (
    SELECT siren_a AS member_siren, LEAST(siren_a, siren_b) AS group_root, n_dirig_communs FROM dirig_pairs
    UNION ALL
    SELECT siren_b, LEAST(siren_a, siren_b), n_dirig_communs FROM dirig_pairs
),
dirig_groups AS (
    SELECT
        member_siren::text,
        ('dirig:' || group_root) AS group_lei,
        'dirigeants_communs'::text AS detection_method,
        LEAST(0.85, 0.5 + (max(n_dirig_communs) * 0.05))::numeric AS confidence
    FROM dirig_groups_raw
    GROUP BY member_siren, group_root
),

-- ───── Union des méthodes (priorité LEI sur dirigeants)
all_groups AS (
    SELECT * FROM lei_groups
    UNION ALL
    -- Garder dirig only si pas déjà capturé par LEI
    SELECT d.* FROM dirig_groups d
    WHERE NOT EXISTS (
        SELECT 1 FROM lei_groups l WHERE l.member_siren = d.member_siren
    )
),

-- ───── Layer 2 : agrégation comptes par groupe
-- Latest exercice par membre
latest_compte AS (
    SELECT DISTINCT ON (siren)
        siren,
        ca_net,
        resultat_net,
        capitaux_propres,
        immo_corporelles,
        effectif_moyen,
        date_cloture
    FROM silver.inpi_comptes
    WHERE date_cloture IS NOT NULL
    ORDER BY siren, date_cloture DESC NULLS LAST
),

aggregated AS (
    SELECT
        ag.group_lei,
        max(ag.detection_method) AS detection_method,  -- LEI > dirigeants
        max(ag.confidence) AS confidence,
        count(DISTINCT ag.member_siren) AS n_members,
        array_agg(DISTINCT ag.member_siren) AS members_sirens,
        SUM(c.ca_net) AS ca_consolidated,
        SUM(c.resultat_net) AS resultat_net_consolidated,
        SUM(c.capitaux_propres) AS capitaux_propres_consolidated,
        SUM(c.immo_corporelles) AS immo_corporelles_consolidated,
        SUM(c.effectif_moyen) AS effectif_consolidated,
        max(c.date_cloture) AS latest_exercice,
        count(c.siren) AS n_members_with_comptes
    FROM all_groups ag
    LEFT JOIN latest_compte c ON c.siren = ag.member_siren
    GROUP BY ag.group_lei
    HAVING count(DISTINCT ag.member_siren) >= 2  -- au moins 2 membres
),

-- ───── Identifier le siren parent + denomination
parent_resolution AS (
    SELECT
        a.*,
        -- LEI : siren mappé sur ultimate_parent_lei
        CASE
            WHEN a.detection_method = 'lei' THEN
                (SELECT pm.parent_siren FROM lei_parent_map pm
                 WHERE pm.group_lei = a.group_lei LIMIT 1)
            -- Dirigeants : on prend le siren du groupe avec le plus gros CA
            ELSE
                (SELECT lc.siren FROM latest_compte lc
                 WHERE lc.siren = ANY(a.members_sirens)
                 ORDER BY lc.ca_net DESC NULLS LAST LIMIT 1)
        END AS ultimate_parent_siren
    FROM aggregated a
)

SELECT
    pr.ultimate_parent_siren,
    -- Denomination du parent depuis multi-source
    coalesce(
        (SELECT em.denomination FROM gold.entreprises_master em
         WHERE em.siren = pr.ultimate_parent_siren LIMIT 1),
        (SELECT pm.parent_name FROM lei_parent_map pm
         WHERE pm.group_lei = pr.group_lei LIMIT 1),
        pr.ultimate_parent_siren
    ) AS ultimate_parent_denomination,
    -- LEI groupe (NULL si méthode dirigeants)
    CASE WHEN pr.detection_method = 'lei' THEN pr.group_lei ELSE NULL END AS group_lei,
    pr.detection_method,
    pr.confidence,
    pr.n_members,
    pr.members_sirens,
    pr.n_members_with_comptes,
    pr.ca_consolidated,
    pr.resultat_net_consolidated,
    pr.capitaux_propres_consolidated,
    pr.immo_corporelles_consolidated,
    pr.effectif_consolidated,
    -- Marge proxy consolidée
    CASE
        WHEN pr.ca_consolidated > 0 THEN
            -- Cap à [-10, 10] pour éviter numeric overflow sur groupes en perte massive
            GREATEST(-10.0, LEAST(10.0,
                pr.resultat_net_consolidated / pr.ca_consolidated
            ))::numeric(8,4)
        ELSE NULL
    END AS proxy_margin_consolidated,
    pr.latest_exercice,
    -- Tier groupe selon CA consolidé
    CASE
        WHEN pr.ca_consolidated >= 1000000000 THEN 'large_cap'
        WHEN pr.ca_consolidated >= 100000000 THEN 'mid_cap_haut'
        WHEN pr.ca_consolidated >= 50000000 THEN 'mid_cap'
        WHEN pr.ca_consolidated >= 10000000 THEN 'small_cap'
        ELSE 'micro_cap'
    END AS group_size_tier,
    NOW() AS materialized_at
FROM parent_resolution pr
WHERE pr.ultimate_parent_siren IS NOT NULL;

CREATE INDEX ON gold.groups_consolidated (ultimate_parent_siren);
CREATE INDEX ON gold.groups_consolidated (group_lei);
CREATE INDEX ON gold.groups_consolidated (detection_method);
CREATE INDEX ON gold.groups_consolidated (confidence DESC);
CREATE INDEX ON gold.groups_consolidated (ca_consolidated DESC NULLS LAST);
CREATE INDEX ON gold.groups_consolidated (n_members DESC);
CREATE INDEX ON gold.groups_consolidated USING gin (members_sirens);

ANALYZE gold.groups_consolidated;

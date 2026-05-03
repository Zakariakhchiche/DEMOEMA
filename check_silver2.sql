-- Reproduire la query exacte de _dirigeant_full
SELECT
    MAX(nom) AS nom, MAX(prenom) AS prenom,
    MAX(date_naissance) AS date_naissance, MAX(age_2026) AS age,
    MAX(n_mandats_total) AS n_mandats_total,
    MAX(n_mandats_actifs) AS n_mandats_actifs,
    array_length(ARRAY(SELECT DISTINCT unnest(array_agg(sirens_mandats))), 1) AS n_sirens,
    array_length(ARRAY(SELECT DISTINCT unnest(array_agg(denominations))), 1) AS n_deno,
    array_length(ARRAY(SELECT DISTINCT unnest(array_agg(roles))), 1) AS n_roles,
    bool_or(is_multi_mandat) AS is_multi
FROM silver.inpi_dirigeants
WHERE UPPER(unaccent(nom)) = UPPER(unaccent('LAMOUR'))
  AND UPPER(unaccent(prenom)) = UPPER(unaccent('VINCENT'));

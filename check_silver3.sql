-- Reproduire la requête EXACTE de _dirigeant_full après mon fix
SELECT
    nom, prenom, date_naissance, age_2026 AS age,
    n_mandats_total, n_mandats_actifs,
    array_length(sirens_mandats, 1) AS n_sirens,
    array_length(denominations, 1) AS n_deno,
    array_length(roles, 1) AS n_roles,
    is_multi_mandat
FROM silver.inpi_dirigeants
WHERE UPPER(unaccent(nom)) = UPPER(unaccent('LAMOUR'))
  AND UPPER(unaccent(prenom)) = UPPER(unaccent('VINCENT'))
ORDER BY coalesce(n_mandats_total, n_mandats_actifs, 0) DESC
LIMIT 1;

SELECT version_uid, applied_at, length(generated_sql) AS sql_len
FROM audit.silver_specs_versions
WHERE silver_name = 'silver.inpi_dirigeants'
ORDER BY applied_at DESC
LIMIT 5;

SELECT nom, prenom, n_mandats_actifs, n_mandats_total,
       array_length(sirens_mandats, 1) AS n_sirens,
       array_length(denominations, 1) AS n_deno,
       array_length(roles, 1) AS n_roles
FROM silver.inpi_dirigeants
WHERE nom = 'LAMOUR' AND prenom = 'VINCENT';

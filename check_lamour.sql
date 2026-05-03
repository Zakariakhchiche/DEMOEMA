-- 1. SCI patrimoine
SELECT nom, prenom, date_naissance, n_sci,
       total_capital_sci,
       array_length(sci_sirens, 1) AS n_sirens
FROM silver.dirigeant_sci_patrimoine
WHERE nom = 'LAMOUR' AND prenom = 'VINCENT'
LIMIT 10;

-- 2. Compter les SCI parmi ses 23 mandats (forme juridique 65xx)
SELECT count(*) AS n_sci_in_mandats,
       count(*) FILTER (WHERE e.montant_capital IS NOT NULL) AS n_with_capital,
       sum(coalesce(e.montant_capital, 0)) AS sum_capital
FROM bronze.inpi_formalites_personnes p
JOIN bronze.inpi_formalites_entreprises e ON e.siren = p.siren
WHERE p.individu_nom = 'LAMOUR'
  AND 'VINCENT' = ANY(p.individu_prenoms)
  AND e.forme_juridique LIKE '65%';

-- 3. Lister les SCI (entités forme 65xx) parmi ses mandats
SELECT p.siren, e.denomination, e.forme_juridique, e.montant_capital,
       e.adresse_code_postal, e.date_immatriculation
FROM bronze.inpi_formalites_personnes p
JOIN bronze.inpi_formalites_entreprises e ON e.siren = p.siren
WHERE p.individu_nom = 'LAMOUR'
  AND 'VINCENT' = ANY(p.individu_prenoms)
  AND e.forme_juridique LIKE '65%'
ORDER BY e.montant_capital DESC NULLS LAST
LIMIT 10;

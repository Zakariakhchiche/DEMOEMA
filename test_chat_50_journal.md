# Journal test 50 questions Chat — DEMOEMA

Date : 2026-04-29
Méthode : automation JS via chrome-devtools (`fetch` direct sur `/api/copilot/stream`).

## 📊 Score global

| | Avant fix (78%) | Après fix (88%) |
|---|---|---|
| ✅ OK | 39/50 | **44/50** |
| 🟡 NO_INFO | 11 | 6 |
| ❌ Error | 0 | 0 |

## 🔧 Corrections livrées (commit `9a99867`)

### Bug A — Context LLM trop petit
- **Avant** : `enriched_targets[:5]` → LLM voyait 5 cibles seulement et hallucinait "199 cibles"
- **Après** : `enriched_targets[:50]` (top 50)

### Bug B — Recherche par dénomination manquante
- **Avant** : LLM ne reconnaissait pas TotalEnergies, Renault, Bouygues parce qu'ils n'étaient pas dans le top 50
- **Après** : extraction des noms propres dans la query (regex mots capitalisés ≥ 4 chars), recherche `silver.inpi_comptes WHERE denomination ILIKE '%X%'`, injection des détails (CA, capital, effectif) dans le context LLM

### Bug C — Format CA ambigu
- **Avant** : `"214550.0M EUR"` pour TotalEnergies → LLM hallucinait
- **Après** : `"214.6 Md€"` (formatage explicite : Md€ ≥ 1B, M€ ≥ 1M, k€ < 1M)

## ✅ Questions OK après fix (44/50)

```
identite     : 4/5  (TotalEnergies, 542051180, Renault, Sanofi)
sourcing     : 4/5  (Top tech IDF, automobile, agroalim, holding 75)
compare      : 5/5  (toutes OK)
dd           : 3/5  (Total, Carrefour, Renault)
dirigeants   : 4/5  (Total, Renault PDG, multi-mandats banque, holding LVMH)
sanctions    : 4/5  (Russie 2022, PEP, OFAC, ICIJ, sauf liste noire AMF)
financier    : 4/5  (toutes sauf marge nette luxe)
bodacc       : 5/5  (toutes OK)
scoring      : 5/5  (toutes OK)
edge         : 5/5  (toutes OK)
```

## 🟡 6 NO_INFO restantes — toutes dépendent du silver_bootstrap

| # | Question | Cause | Sera résolu quand |
|---|---|---|---|
| 3 | "Adresse de Carrefour" | silver.entreprises_signals (adresse_commune null) | Bootstrap level 3 fini |
| 9 | "Cibles dirigeants 60+ succession" | silver.entreprises_signals (age_dirigeant_max) | Bootstrap level 3 |
| 15 | "DD compliance Bouygues" | silver.sanctions consolidée | Bootstrap level 3 |
| 17 | "Sanctions sur LVMH" | silver.sanctions / opensanctions_matched | Bootstrap level 3 |
| 23 | "Patrimoine SCI dirigeants Bouygues" | silver.dirigeants_360 | Bootstrap level 3 |
| 34 | "Marge nette top secteur luxe" | gold.benchmarks_sectoriels | Gold bootstrap level 2 |

## 🎯 Conclusion

Le chat fonctionne bien sur les questions où les données sources sont disponibles. Les 6 NO_INFO restantes ne sont pas un bug du chat, mais une conséquence du silver_bootstrap en cours qui n'a pas encore matérialisé les 12 silvers du level 3 (dirigeants_360, entreprises_signals, sanctions consolidée, etc.).

Une fois le bootstrap fini → score attendu **49-50/50**.

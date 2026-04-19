# VALIDATION API — Méthodologie

> ⚠️ **Document V2 — calendrier décalé +3 mois post-audit 2026-04-17.**
>
> ⚠️ Toute référence à **"Q1 2026"** dans ce document doit être lue comme **"Q2-Q3 2026"** (validation effective : avril-septembre 2026).
>
> ⚠️ **143 sources catalogées → 140 réellement exploitables** :
> - ❌ Source #41 INPI RBE : retirée (CJUE 22/11/2022)
> - ❌ Source #125 Trustpilot : retirée (CGU)
> - ❌ Source #126 Google Reviews : retirée (CGU)
> - ⚠️ Sources #119-124 presse : mode "titre + URL + date" uniquement (droits voisins)
>
> Avant d'intégrer une source dans le pipeline production, elle doit passer par cette procédure de validation. Évite les surprises (API morte, gratuit devenu payant, CGU incompatibles).

---

## Pourquoi cette étape

Les 143 sources cataloguées dans `ARCHITECTURE_DATA_V2.md` sont basées sur la **documentation publique**. Aucun appel HTTP réel n'a été fait pour valider :

- Que l'endpoint répond
- Que le format est conforme
- Que le rate limit est tenable
- Que les CGU autorisent notre usage commercial
- Que la qualité des données est suffisante

**Cette validation doit être faite AVANT d'intégrer chaque source en production.**

---

## Critères d'évaluation par source

Chaque source est notée sur 6 dimensions (note 0-3) :

| Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **Disponibilité** | API morte | Intermittente | Stable, downtime occasionnel | Stable, SLA documenté |
| **Format** | Non documenté, format chaotique | Doc partielle | Doc complète, format propre | OpenAPI/JSON Schema fourni |
| **Auth** | Bloquant (validation manuelle longue) | OAuth complexe | OAuth simple | Pas d'auth |
| **Volume** | <10% du périmètre attendu | 10-50% | 50-90% | 90-100% |
| **Rate limit** | <100 req/jour | 100-1k req/jour | 1k-10k req/jour | >10k req/jour ou bulk |
| **CGU** | Interdit usage commercial | Restrictions fortes | Restrictions mineures | Licence ouverte commercial OK |

**Score total** :
- 🟢 **Go** : ≥14/18 (utilisable directement)
- 🟡 **Conditionnel** : 9-13/18 (utilisable avec contournement, fallback)
- 🔴 **No-Go** : <9/18 (à exclure, chercher alternative)

---

## Procédure de validation par source (4 étapes)

### Étape 1 — Test technique de connectivité

```python
# Pseudo-code
def validate_source(source: str) -> dict:
    result = {
        "source": source,
        "status_code": None,
        "latency_ms": None,
        "format_ok": False,
        "sample_size": 0,
        "errors": []
    }

    # 1. Test endpoint
    try:
        resp = httpx.get(SOURCE_URL, timeout=30)
        result["status_code"] = resp.status_code
        result["latency_ms"] = resp.elapsed.total_seconds() * 1000
    except Exception as e:
        result["errors"].append(str(e))
        return result

    # 2. Vérifier format JSON conforme
    try:
        data = resp.json()
        validate_against_schema(data, EXPECTED_SCHEMA[source])
        result["format_ok"] = True
        result["sample_size"] = len(data) if isinstance(data, list) else 1
    except Exception as e:
        result["errors"].append(f"Schema mismatch: {e}")

    # 3. Test échantillon connu (10 SIREN référence)
    for siren in REFERENCE_SIRENS:
        try:
            resp = httpx.get(f"{SOURCE_URL}/{siren}")
            assert resp.status_code == 200
        except Exception as e:
            result["errors"].append(f"Reference SIREN {siren} failed: {e}")

    return result
```

### Étape 2 — Test de volumétrie

Pour chaque source, requêter 100 entreprises de l'échantillon de référence (mix taille/secteur) :

```python
REFERENCE_SAMPLE = [
    # 20 grandes (CAC 40)
    "542065479",  # LVMH
    "542107651",  # TotalEnergies
    # ...
    # 30 ETI variées
    # 30 PME
    # 20 micros
]

def test_coverage(source: str) -> float:
    found = 0
    for siren in REFERENCE_SAMPLE:
        if has_data(source, siren):
            found += 1
    return found / len(REFERENCE_SAMPLE)
```

**Seuil** : couverture >70% pour passer en production.

### Étape 3 — Audit juridique CGU

Pour chaque source, lire les CGU/licence et répondre à :

- [ ] Licence permet-elle l'**usage commercial** ?
- [ ] Permet-elle la **redistribution** des données enrichies ?
- [ ] Y a-t-il des **obligations d'attribution** ?
- [ ] Y a-t-il une clause **share-alike** (ex: ODbL) ?
- [ ] Quelles sont les **restrictions de fréquence** ?
- [ ] Quelles **données personnelles** sont incluses (RGPD) ?

**Validation par juriste** (DPO ou cabinet) requise pour :
- Sources contenant des données personnelles (dirigeants, BE)
- Sources avec licence "open" mais ambiguë
- Sources étrangères (juridictions différentes)

### Étape 4 — Test fraîcheur & stabilité (sur 30 jours)

- Programmer un appel quotidien pendant 30 jours
- Mesurer :
  - Taux de succès
  - Variation de latence
  - Stabilité du format (changements non documentés)
  - Quota consommé / quota théorique

**Source acceptée** si :
- >95% de succès
- Latence p95 < 5s
- Aucun changement de format non documenté
- Quota consommé < 50% du quota théorique

---

## Matrice de validation cible (livrable Q1 2026)

```
Source                    | Conn | Format | Auth | Vol  | RateL | CGU | Total | Verdict
--------------------------|------|--------|------|------|-------|-----|-------|--------
1. API Recherche Entrep. | 3    | 3      | 3    | 3    | 3     | 3   | 18/18 | 🟢 Go
2. INSEE SIRENE V3       | ?    | ?      | ?    | ?    | ?     | ?   | ?/18  | ⏳
3. INSEE SIRENE Stock    | ?    | ?      | ?    | ?    | ?     | ?   | ?/18  | ⏳
... (143 lignes)
```

Le tableau complet sera produit pendant la phase de validation.

---

## Sources à valider en priorité (Q1 2026)

**Top 20** sources critiques à valider en priorité :

1. API Recherche Entreprises
2. INSEE SIRENE V3 (API)
3. INSEE SIRENE Stock (bulk)
4. INPI RNE
5. INPI comptes annuels
6. annuaire-entreprises.data.gouv.fr
7. BODACC
8. Judilibre
9. Légifrance API
10. OpenSanctions
11. Gels des Avoirs DGTrésor
12. GLEIF API
13. OpenCorporates
14. DECP
15. BOAMP
16. France Travail API
17. DVF
18. Certificate Transparency (crt.sh)
19. GitHub API
20. GDELT 2.0

Si ces 20 passent toutes en 🟢 ou 🟡, le projet est viable. Sinon, replan.

---

## Que faire si une source est 🔴 ?

Pour chaque source bloquée, chercher un **plan B** :

| Source originale | Si bloquée | Alternative |
|---|---|---|
| INSEE SIRENE API | Quotas trop stricts | Bulk Sirene Stock mensuel |
| OpenCorporates | Devient payant | OpenSanctions (limité) + GLEIF |
| OpenSanctions | Devient payant | Recompiler depuis OFAC + EU + UK + FR séparément |
| INPI comptes annuels | Problème parsing PDF | Société.com en partenariat |
| GitHub API | Rate limit insuffisant | GH Archive (BigQuery public) |
| Certificate Transparency | Volume trop élevé | Censys (free tier) |

**Règle** : aucune source critique ne doit être un point de défaillance unique. Chaque source 🟢/🟡 doit avoir au moins **1 plan B documenté**.

---

## Outils & livrables

### Script de validation

Sera développé dans `scripts/validate_sources.py` :
- Configurable par fichier YAML
- Génère un rapport HTML + Markdown
- Réexécutable mensuellement (détection de régression)
- Intégré dans Dagster comme job programmé

### Dashboard de monitoring

Une fois en production, dashboard Grafana qui suit pour chaque source :
- Taux de succès (24h, 7j, 30j)
- Latence p50/p95/p99
- Quota consommé
- Dernier changement de format détecté

**Alerte Slack** si :
- Taux de succès < 90% sur 24h
- Latence p95 > 10s
- Quota >80% consommé
- Format changé (regression test)

---

## Calendrier de validation

| Semaine | Action |
|---|---|
| S1-S2 | Dev script de validation |
| S3 | Validation Top 20 (priorité 1) |
| S4 | Validation 30 sources priorité 2 |
| S5-S6 | Validation 50 sources priorité 3 |
| S7-S8 | Validation 43 sources restantes + audit juridique CGU |
| S9 | Synthèse + matrice finale + plans B |
| S10 | Mise à jour roadmap selon résultats |

**Total** : 10 semaines = **Q1 2026 dédié à valider** avant de tout coder.

---

## Maintenance continue

Après le lancement :
- **Mensuel** : exécution du script de validation sur les 143 sources
- **Trimestriel** : revue des CGU (recherche de changements)
- **Annuel** : audit juridique complet par cabinet

Toute évolution est documentée dans le **changelog des sources** (`SOURCES_CHANGELOG.md`, à créer).

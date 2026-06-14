# Plan — rebuild complet du graphe Neo4j (identité Person)

> Rédigé 2026-06-14. Contexte : audit graphe demandé par Zak.

## Problème (root cause)

Le graphe Neo4j (10,5 M Company · 6,6 M Person · ~18 M relations) a été construit
par **plusieurs imports en masse historiques** utilisant une formule
`person_uid` basée sur **le 1er prénom uniquement** (`prenoms[0]`), alors que le
sync quotidien (`ingestion/neo4j_sync.py::_person_uid`) utilise **la tuple triée
de TOUS les prénoms**. → **deux schémas d'identité Person incompatibles** coexistent.

Conséquences mesurées :
- Flag `actif` sur IS_DIRIGEANT : FALSE 10,5 M / TRUE 20 776 (la source INPI dit
  ~84 % actifs). Un backfill par uid n'a matché que **23 624 / 13 M** arêtes.
- Les nœuds Person du gros du graphe ont `prenoms = NULL` (uid = hash(nom|""|dob)).
- Enrichissements (actif, sanctions, lobbying) ne couvrent de façon fiable que la
  fenêtre incrémentale (~10 k sociétés/passage du cron).

## Corrigé (2026-06-14)

- ✅ **`scripts/neo4j/neo4j_loader.py::person_uid` aligné** sur `_person_uid`
  (prénoms triés complets) → plus de divergence loader vs sync à l'avenir.
- ✅ Enrichissements **lobbying** (20,5 k dirigeants) + **sanctions/offshore**
  (sociétés + 2 700 dirigeants) appliqués par match siren+nom (uid-indépendant,
  donc fonctionnent sur le graphe existant).
- ✅ Sync quotidien : volet compliance réparé, `entreprises_signals` restaurée.

## Reste à faire — rebuild complet (opération supervisée)

Objectif : un graphe à **identité Person unique et cohérente** + flag `actif`
fiable + enrichissements complets sur TOUT le périmètre.

Étapes (à exécuter de nuit, supervisé, ~plusieurs heures) :

1. **Décision de périmètre** : garder les 10,5 M sociétés (toutes formes), ou
   resserrer sur le périmètre M&A pertinent (formes SAS/SA + capital ≥ seuil) ?
   Le `neo4j_loader` actuel filtre `forme_juridique IN (...) AND capital≥500k` —
   il faut soit l'élargir (loader unifié sur tous les dirigeants), soit assumer
   le resserrement.
2. **Wipe** des nœuds Person + relations IS_DIRIGEANT/CO_MANDATE/A_CEDE en batch
   (`CALL { MATCH (p:Person) DETACH DELETE p } IN TRANSACTIONS OF 10000`).
3. **Reload** via loader unifié (uid canonique) — companies + persons + edges.
4. **Ré-enrichissements** : compliance, financials, cession (run_neo4j_rebuild),
   puis CO_MANDATE (`build_co_mandates_full.py`), A_CEDE, lobbying
   (`backfill_person_influence.py`), sanctions.
5. **Vérif** : distribution `actif` ≈ 84 % true ; lobbyistes ≈ 20 k+ ; serial
   sellers ; cohérence counts vs Postgres.

> ⚠️ Ne pas lancer en aveugle/non-supervisé : le wipe est destructif (le graphe
> est reconstructible depuis Postgres, mais la fenêtre de rebuild dure des heures).
> Recommandation : exécution pilotée (session dédiée) plutôt que cron one-shot.

## Pérennité (option not yet done)

Intégrer les passes **lobbying + sanctions** dans `run_neo4j_rebuild` (cron 04:00)
pour qu'elles soient maintenues automatiquement, pas juste les one-shots actuels.

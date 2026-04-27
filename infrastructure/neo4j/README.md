# Neo4j — DEMOEMA

Graph store des relations dirigeants ↔ entreprises (signal patrimoine + multi-mandats pour le scoring M&A).

## Accès

Container `demomea-neo4j` exposé en interne sur le réseau Docker. Ports `7474` (Browser HTTP) et `7687` (Bolt) **pas ouverts dans UFW** — accès via tunnel SSH :

```bash
ssh -L 7474:localhost:7474 -L 7687:localhost:7687 root@82.165.242.205
```

Puis dans le navigateur : http://localhost:7474/

- **Connect URL** : `bolt://localhost:7687`
- **Username** : `neo4j`
- **Password** : valeur de `NEO4J_PASSWORD` du `.env` (défaut `demoema_neo4j_pass`, à rotater)

## Premier setup d'une session Browser

Le Browser garde la config en localStorage par utilisateur. Pour que les nodes affichent un caption lisible (sinon : uid hash):

1. Ouvre le panneau de style : tape `:style` dans la barre Cypher → Enter
2. Colle le contenu de [`graphstyle.grass`](./graphstyle.grass)
3. Clique sur **Apply**

Effet immédiat :
- `Person` affiche `full_name` (= `prenom + ' ' + nom`)
- `Company` affiche `denomination`
- `IS_DIRIGEANT` affiche le rôle (`Président`, `Gérant`, …)

## Schema

| Label | Propriétés clés | Index |
|---|---|---|
| `Company` | siren (UNIQUE), denomination, forme_juridique, capital, code_ape, date_immat, code_postal | siren, forme_juridique |
| `Person` | uid (UNIQUE = sha1(nom\|prenom\|date_naissance)), nom, prenoms[], prenom, full_name, date_naissance | uid, nom, full_name |
| `IS_DIRIGEANT` | role, actif, individu_role | — |

## Rebuild

Job APScheduler `Neo4j graph rebuild` quotidien à 04:00 Paris (registered par `engine.start_scheduler`) :
- Source : `bronze.inpi_formalites_entreprises` + `bronze.inpi_formalites_personnes`
- Cible : top 10 000 SAS/SA/SCA avec capital ≥ 500 k€, plus leurs dirigeants individus actifs
- Code : [`infrastructure/agents/platform/ingestion/neo4j_sync.py`](../agents/platform/ingestion/neo4j_sync.py)

Pour déclencher manuellement :

```bash
docker exec demomea-agents-platform python -c \
  "import asyncio; from ingestion.neo4j_sync import run_neo4j_rebuild; print(asyncio.run(run_neo4j_rebuild()))"
```

## Requêtes-types

```cypher
// Top dirigeants multi-mandats — signal "Pro M&A" du scoring
MATCH (p:Person)-[:IS_DIRIGEANT]->(c:Company)
WITH p, count(c) AS n_mandats, collect(c.denomination)[..5] AS exemples
WHERE n_mandats >= 5
RETURN p.full_name AS dirigeant, n_mandats, exemples
ORDER BY n_mandats DESC LIMIT 20;

// Cluster patrimonial : dirigeants partageant ≥ 2 sociétés
MATCH (p1:Person)-[:IS_DIRIGEANT]->(c:Company)<-[:IS_DIRIGEANT]-(p2:Person)
WHERE id(p1) < id(p2)
WITH p1, p2, count(c) AS shared
WHERE shared >= 2
RETURN p1.full_name, p2.full_name, shared
ORDER BY shared DESC LIMIT 30;

// Ego-graph d'une entreprise
MATCH (c:Company {siren: '507523678'})<-[:IS_DIRIGEANT]-(p:Person)
OPTIONAL MATCH (p)-[:IS_DIRIGEANT]->(other:Company)
WHERE other <> c
RETURN c, p, other;
```

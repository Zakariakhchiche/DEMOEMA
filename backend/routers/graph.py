"""Routes Neo4j graph — expose les enrichissements + relations CO_MANDATE.

Endpoint principal : GET /api/graph/person/{nom}/{prenom}
Retourne les flags (sanctions/lobbying/offshore/sci) + top co-mandataires
+ companies du dirigeant.

Le driver Neo4j est lazy-init au 1er request (pas de pool persistant). Le
container agents-platform expose Neo4j sur bolt://neo4j:7687 (réseau interne).
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/graph", tags=["graph"])

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "demoema_neo4j_pass")

_driver = None


def _get_driver():
    """Lazy init driver. Réutilisé entre requests (thread-safe)."""
    global _driver
    if _driver is None:
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="neo4j driver not installed (pip install neo4j)",
            )
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


@router.get("/person/{nom}/{prenom}")
async def person_graph(nom: str, prenom: str, top_n: int = 10):
    """Retourne les enrichissements + top co-mandataires d'un dirigeant.

    Match par (UPPER(nom), UPPER(prenom)) avec fallback sur prénoms array.
    """
    driver = _get_driver()
    nom_uc = (nom or "").strip().upper()
    prenom_uc = (prenom or "").strip().upper()

    if not nom_uc or not prenom_uc:
        raise HTTPException(status_code=400, detail="nom + prenom requis")

    # 1. Person flags + props enrichies
    query_flags = """
    MATCH (p:Person)
    WHERE upper(p.nom) = $nom_uc
      AND (upper(p.prenom) = $prenom_uc
           OR $prenom_uc IN [x IN coalesce(p.prenoms, []) | upper(x)])
    RETURN
        p.uid AS uid,
        p.nom AS nom,
        p.prenom AS prenom,
        p.full_name AS full_name,
        p.date_naissance AS date_naissance,
        p.age_2026 AS age_2026,
        p.n_mandats_actifs AS n_mandats_actifs,
        coalesce(p.is_sanctioned, false) AS is_sanctioned,
        coalesce(p.is_lobbyist, false) AS is_lobbyist,
        coalesce(p.has_offshore, false) AS has_offshore,
        coalesce(p.n_sci, 0) AS n_sci,
        coalesce(p.total_capital_sci, 0.0) AS total_capital_sci,
        p.sci_denominations AS sci_denominations,
        p.linkedin_url AS linkedin_url,
        p.github_username AS github_username,
        p.twitter_handle AS twitter_handle,
        p.n_total_social AS n_total_social,
        p.wikidata_qid AS wikidata_qid,
        p.wikidata_birth_year AS wikidata_birth_year,
        p.wikidata_occupation AS wikidata_occupation,
        p.icij_leaks AS icij_leaks,
        p.icij_node_ids AS icij_node_ids,
        p.icij_countries AS icij_countries,
        p.sanctions_topics AS sanctions_topics,
        p.sanctions_programs AS sanctions_programs,
        p.sanctions_countries AS sanctions_countries,
        p.lobby_denominations AS lobby_denominations,
        p.lobby_categories AS lobby_categories
    LIMIT 1
    """

    # 2. Top N co-mandataires triés par n_shared_companies
    query_comandates = """
    MATCH (p:Person)
    WHERE upper(p.nom) = $nom_uc
      AND (upper(p.prenom) = $prenom_uc
           OR $prenom_uc IN [x IN coalesce(p.prenoms, []) | upper(x)])
    WITH p
    LIMIT 1
    MATCH (p)-[r:CO_MANDATE]-(other:Person)
    RETURN
        other.full_name AS full_name,
        other.nom AS nom,
        other.prenom AS prenom,
        coalesce(r.n_shared_companies, 1) AS n_shared,
        coalesce(r.via_sirens, []) AS via_sirens,
        coalesce(other.is_sanctioned, false) AS other_sanctioned,
        coalesce(other.has_offshore, false) AS other_offshore,
        coalesce(other.is_lobbyist, false) AS other_lobbyist
    ORDER BY n_shared DESC
    LIMIT $top_n
    """

    # 3. Companies du dirigeant via IS_DIRIGEANT
    query_companies = """
    MATCH (p:Person)
    WHERE upper(p.nom) = $nom_uc
      AND (upper(p.prenom) = $prenom_uc
           OR $prenom_uc IN [x IN coalesce(p.prenoms, []) | upper(x)])
    WITH p LIMIT 1
    MATCH (p)-[r:IS_DIRIGEANT]->(c:Company)
    RETURN
        c.siren AS siren,
        c.denomination AS denomination,
        c.forme_juridique AS forme_juridique,
        c.capital AS capital,
        c.code_postal AS code_postal,
        coalesce(r.role, '') AS role,
        coalesce(r.actif, false) AS actif
    ORDER BY c.capital DESC NULLS LAST
    LIMIT 50
    """

    try:
        with driver.session() as s:
            flags_record = s.run(query_flags, nom_uc=nom_uc, prenom_uc=prenom_uc).single()
            if flags_record is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Dirigeant introuvable dans Neo4j: {prenom} {nom}",
                )
            flags = dict(flags_record)

            comandates = [
                dict(r) for r in s.run(query_comandates, nom_uc=nom_uc, prenom_uc=prenom_uc, top_n=top_n)
            ]

            companies = [
                dict(r) for r in s.run(query_companies, nom_uc=nom_uc, prenom_uc=prenom_uc)
            ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unreachable: {type(e).__name__}: {e}")

    return {
        "person": flags,
        "top_co_mandataires": comandates,
        "companies": companies,
    }


@router.get("/health")
async def health():
    """Health check Neo4j connectivité."""
    driver = _get_driver()
    try:
        with driver.session() as s:
            r = s.run("MATCH (n) RETURN count(n) AS total LIMIT 1").single()
            return {"status": "up", "node_count": r["total"] if r else 0}
    except Exception as e:
        return {"status": "down", "error": f"{type(e).__name__}: {e}"}

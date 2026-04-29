"""Connecteur asyncpg vers le datalake Postgres (gold + silver + bronze).

Le datalake tourne dans le projet compose `demoema-agents` (host `datalake-db`,
db `datalake`). Le backend doit y être branché via le network external
`demoema-agents_agents-net` (cf. docker-compose.override.yml).

Pool unique partagé via FastAPI `app.state.dl_pool`. Lifespan du backend
acquiert/relâche le pool. DSN dérivée de DATALAKE_AGENTS_PASSWORD ou
DATALAKE_RO_PASSWORD (pref) pour read-only safety.
"""
from __future__ import annotations

import os
from typing import Any

import asyncpg


def _build_dsn() -> str:
    explicit = os.environ.get("DATALAKE_DSN", "").strip()
    if explicit:
        return explicit

    pwd = (
        os.environ.get("DATALAKE_RO_PASSWORD", "").strip()
        or os.environ.get("DATALAKE_AGENTS_PASSWORD", "").strip()
        or os.environ.get("DATALAKE_POSTGRES_ROOT_PASSWORD", "").strip()
    )
    user = (
        "datalake_ro"
        if os.environ.get("DATALAKE_RO_PASSWORD")
        else (
            "datalake_agents"
            if os.environ.get("DATALAKE_AGENTS_PASSWORD")
            else "postgres"
        )
    )
    host = os.environ.get("DATALAKE_HOST", "datalake-db")
    port = int(os.environ.get("DATALAKE_PORT", "5432"))
    db = os.environ.get("DATALAKE_DB", "datalake")
    if not pwd:
        return ""
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


async def create_pool() -> asyncpg.Pool | None:
    dsn = _build_dsn()
    if not dsn:
        return None
    return await asyncpg.create_pool(
        dsn,
        min_size=2,
        max_size=10,
        command_timeout=20,
        server_settings={"application_name": "edrcf-backend"},
    )


GOLD_TABLES_WHITELIST: dict[str, dict[str, Any]] = {
    "gold.entreprises_master": {
        "label": "Entreprises (Master)",
        "category": "core",
        "pk": "siren",
        "default_order": "score_ma DESC NULLS LAST",
        "search_cols": ["denomination", "siren", "naf_libelle", "siege_dept"],
        "preview_cols": [
            "siren",
            "denomination",
            "naf_libelle",
            "siege_dept",
            "ca_dernier",
            "score_ma",
            "statut",
        ],
    },
    "gold.dirigeants_master": {
        "label": "Dirigeants (Master)",
        "category": "core",
        "pk": "person_id",
        "default_order": "score_decideur DESC NULLS LAST",
        "search_cols": ["nom", "prenom", "qualite"],
        "preview_cols": [
            "person_id",
            "nom",
            "prenom",
            "qualite",
            "n_mandats",
            "age",
            "score_decideur",
        ],
    },
    "gold.cibles_ma_top": {
        "label": "Top cibles M&A",
        "category": "ma",
        "pk": "siren",
        "default_order": "score_ma DESC NULLS LAST",
        "search_cols": ["denomination", "siren", "naf_libelle"],
        "preview_cols": [
            "siren",
            "denomination",
            "naf_libelle",
            "ca_dernier",
            "score_ma",
            "tier",
        ],
    },
    "gold.signaux_ma_feed": {
        "label": "Signaux M&A (feed)",
        "category": "signals",
        "pk": "signal_id",
        "default_order": "event_date DESC",
        "search_cols": ["denomination", "siren", "signal_type"],
        "preview_cols": [
            "event_date",
            "denomination",
            "siren",
            "signal_type",
            "severity",
            "source",
        ],
    },
    "gold.network_mandats": {
        "label": "Réseau mandats",
        "category": "network",
        "pk": "edge_id",
        "default_order": "weight DESC NULLS LAST",
        "search_cols": ["nom", "denomination"],
        "preview_cols": [
            "person_id",
            "nom",
            "siren",
            "denomination",
            "qualite",
            "weight",
        ],
    },
    "gold.balo_operations_realtime": {
        "label": "BALO opérations (temps réel)",
        "category": "signals",
        "pk": "operation_id",
        "default_order": "publication_date DESC",
        "search_cols": ["denomination", "operation_type"],
        "preview_cols": [
            "publication_date",
            "denomination",
            "siren",
            "operation_type",
            "montant",
        ],
    },
    "gold.compliance_red_flags": {
        "label": "Compliance red flags",
        "category": "risk",
        "pk": "flag_id",
        "default_order": "detected_at DESC",
        "search_cols": ["denomination", "flag_type"],
        "preview_cols": [
            "detected_at",
            "denomination",
            "siren",
            "flag_type",
            "severity",
            "source",
        ],
    },
    "gold.juridictions_master": {
        "label": "Juridictions (Master)",
        "category": "legal",
        "pk": "decision_id",
        "default_order": "decision_date DESC",
        "search_cols": ["denomination", "siren", "juridiction"],
        "preview_cols": [
            "decision_date",
            "denomination",
            "siren",
            "juridiction",
            "type_procedure",
            "montant",
        ],
    },
    "gold.benchmarks_sectoriels": {
        "label": "Benchmarks sectoriels",
        "category": "analytics",
        "pk": "naf",
        "default_order": "n_entreprises DESC",
        "search_cols": ["naf", "naf_libelle"],
        "preview_cols": [
            "naf",
            "naf_libelle",
            "n_entreprises",
            "ca_median",
            "ebitda_median_pct",
            "score_ma_median",
        ],
    },
    "gold.veille_reglementaire": {
        "label": "Veille réglementaire",
        "category": "regulatory",
        "pk": "doc_id",
        "default_order": "published_at DESC",
        "search_cols": ["title", "type_doc", "naf_impact"],
        "preview_cols": [
            "published_at",
            "type_doc",
            "title",
            "naf_impact",
            "source",
        ],
    },
    "gold.persons_contacts_master": {
        "label": "Contacts dirigeants",
        "category": "osint",
        "pk": "person_id",
        "default_order": "confidence DESC NULLS LAST",
        "search_cols": ["nom", "prenom", "email", "phone"],
        "preview_cols": [
            "person_id",
            "nom",
            "prenom",
            "email",
            "phone",
            "confidence",
            "source",
        ],
    },
    "gold.parcelles_cibles": {
        "label": "Parcelles foncières",
        "category": "patrimoine",
        "pk": "parcelle_id",
        "default_order": "valeur_estimee DESC NULLS LAST",
        "search_cols": ["denomination", "commune"],
        "preview_cols": [
            "parcelle_id",
            "denomination",
            "siren",
            "commune",
            "surface_m2",
            "valeur_estimee",
        ],
    },
    "gold.persons_master_universal": {
        "label": "Persons (Universal)",
        "category": "osint",
        "pk": "person_id",
        "default_order": "score_decideur DESC NULLS LAST",
        "search_cols": ["nom", "prenom"],
        "preview_cols": [
            "person_id",
            "nom",
            "prenom",
            "n_mandats",
            "age",
            "score_decideur",
        ],
    },
    "silver.press_mentions_matched": {
        "label": "Presse (mentions matchées)",
        "category": "press",
        "pk": "article_id",
        "default_order": "published_at DESC",
        "search_cols": ["title", "denomination", "siren", "source"],
        "preview_cols": [
            "published_at",
            "source",
            "title",
            "denomination",
            "siren",
            "ma_signal_type",
        ],
    },
    # Silvers materialisés — exposés en attendant que la couche gold soit
    # complètement construite. Donnent accès aux 29M companies + 6M comptes
    # + 8M dirigeants côté UI.
    "silver.insee_unites_legales": {
        "label": "INSEE — Unités légales (29M)",
        "category": "core",
        "pk": "siren",
        "default_order": "date_creation DESC NULLS LAST",
        "search_cols": ["denomination", "siren"],
        "preview_cols": [
            "siren",
            "denomination",
            "naf",
            "tranche_effectif_unite_legale",
            "date_creation",
            "etat_administratif",
        ],
    },
    "silver.insee_etablissements": {
        "label": "INSEE — Établissements (43M)",
        "category": "core",
        "pk": "siret",
        "default_order": "date_creation DESC NULLS LAST",
        "search_cols": ["siret", "siren", "denomination_etablissement"],
        "preview_cols": [
            "siret",
            "siren",
            "denomination_etablissement",
            "code_postal",
            "libelle_commune",
            "etat_administratif_etablissement",
        ],
    },
    "silver.inpi_comptes": {
        "label": "INPI — Comptes annuels (6M)",
        "category": "core",
        "pk": "siren",
        "default_order": "exercice DESC",
        "search_cols": ["siren", "denomination"],
        "preview_cols": [
            "siren",
            "denomination",
            "exercice",
            "chiffre_affaires",
            "resultat_net",
            "effectif_moyen",
        ],
    },
    "silver.inpi_dirigeants": {
        "label": "INPI — Dirigeants (8M)",
        "category": "core",
        "pk": "person_uid",
        "default_order": "date_naissance DESC NULLS LAST",
        "search_cols": ["nom", "prenom", "siren"],
        "preview_cols": [
            "siren",
            "nom",
            "prenom",
            "qualite",
            "date_naissance",
            "nationalite",
        ],
    },
    "silver.dirigeant_sci_patrimoine": {
        "label": "Dirigeants SCI patrimoine (3.5M)",
        "category": "patrimoine",
        "pk": "person_uid",
        "default_order": "total_capital_sci DESC NULLS LAST",
        "search_cols": ["nom", "prenom"],
        "preview_cols": [
            "person_uid",
            "nom",
            "prenom",
            "n_sci",
            "total_capital_sci",
            "has_holding_patrimoniale",
        ],
    },
    "silver.dvf_transactions": {
        "label": "DVF — Transactions immo (15M)",
        "category": "patrimoine",
        "pk": "id_mutation",
        "default_order": "date_mutation DESC",
        "search_cols": ["commune", "code_postal"],
        "preview_cols": [
            "date_mutation",
            "commune",
            "code_postal",
            "nature_mutation",
            "valeur_fonciere",
            "surface_reelle_bati",
        ],
    },
    "silver.bodacc_annonces": {
        "label": "BODACC annonces (76k)",
        "category": "signals",
        "pk": "annonce_id",
        "default_order": "dateparution DESC",
        "search_cols": ["denomination", "siren", "type_annonce"],
        "preview_cols": [
            "dateparution",
            "denomination",
            "siren",
            "type_annonce",
            "tribunal",
        ],
    },
    "silver.judilibre_decisions": {
        "label": "Judilibre — Décisions (15k)",
        "category": "legal",
        "pk": "decision_id",
        "default_order": "decision_date DESC",
        "search_cols": ["denomination", "juridiction"],
        "preview_cols": [
            "decision_date",
            "juridiction",
            "type_decision",
            "denomination",
            "siren",
        ],
    },
    "silver.opensanctions": {
        "label": "OpenSanctions (280k)",
        "category": "risk",
        "pk": "entity_id",
        "default_order": "score DESC NULLS LAST",
        "search_cols": ["caption", "name"],
        "preview_cols": [
            "entity_id",
            "caption",
            "schema",
            "topics",
            "datasets",
            "score",
        ],
    },
    "silver.gleif_lei": {
        "label": "GLEIF — LEI (10k)",
        "category": "core",
        "pk": "lei",
        "default_order": "registration_date DESC NULLS LAST",
        "search_cols": ["legal_name", "lei", "siren"],
        "preview_cols": [
            "lei",
            "legal_name",
            "siren",
            "country",
            "entity_status",
            "registration_date",
        ],
    },
    "silver.osint_companies_enriched": {
        "label": "OSINT companies (3k)",
        "category": "osint",
        "pk": "siren",
        "default_order": "score_enrichment DESC NULLS LAST",
        "search_cols": ["denomination", "siren"],
        "preview_cols": [
            "siren",
            "denomination",
            "has_wikidata",
            "has_publications",
            "has_github",
            "score_enrichment",
        ],
    },
    "silver.osint_persons_enriched": {
        "label": "OSINT persons (2k)",
        "category": "osint",
        "pk": "person_uid",
        "default_order": "score_visibility DESC NULLS LAST",
        "search_cols": ["nom", "prenom"],
        "preview_cols": [
            "person_uid",
            "nom",
            "prenom",
            "has_wikidata",
            "has_orcid",
            "has_github",
            "score_visibility",
        ],
    },
}

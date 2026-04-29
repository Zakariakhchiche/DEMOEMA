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
        command_timeout=30,
        # statement_cache_size=0 désactive le cache de prepared statements
        # qui timeout aléatoirement sur "prepare" hangs (silver.press_mentions
        # vide mais prepare reste bloqué). Trade-off : un peu plus lent mais
        # stable. Voir https://github.com/MagicStack/asyncpg/issues/325
        statement_cache_size=0,
        server_settings={
            "application_name": "edrcf-backend",
            "statement_timeout": "30000",
        },
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
        "search_cols": ["denomination_unite", "siren", "sigle"],
        "preview_cols": [
            "siren",
            "denomination_unite",
            "code_ape",
            "categorie_juridique",
            "tranche_effectifs",
            "date_creation",
            "etat_administratif",
        ],
    },
    "silver.inpi_comptes": {
        "label": "INPI — Comptes annuels (6M)",
        "category": "core",
        "pk": "depot_id",
        "default_order": "date_cloture DESC",
        "search_cols": ["siren", "denomination"],
        "preview_cols": [
            "siren",
            "denomination",
            "date_cloture",
            "ca_net",
            "resultat_net",
            "capitaux_propres",
            "effectif_moyen",
        ],
    },
    "silver.inpi_dirigeants": {
        "label": "INPI — Dirigeants (8M)",
        "category": "core",
        "pk": "nom",
        "default_order": "n_mandats_actifs DESC NULLS LAST",
        "search_cols": ["nom", "prenom"],
        "preview_cols": [
            "nom",
            "prenom",
            "date_naissance",
            "age_2026",
            "n_mandats_actifs",
            "n_mandats_total",
            "n_sci",
            "total_capital_sci",
            "is_multi_mandat",
        ],
    },
    "silver.dirigeant_sci_patrimoine": {
        "label": "Dirigeants SCI patrimoine (3.5M)",
        "category": "patrimoine",
        "pk": "nom",
        "default_order": "total_capital_sci DESC NULLS LAST",
        "search_cols": ["nom", "prenom"],
        "preview_cols": [
            "nom",
            "prenom",
            "date_naissance",
            "n_sci",
            "total_capital_sci",
            "n_total_mandats",
        ],
    },
    "silver.dvf_transactions": {
        "label": "DVF — Transactions immo (15M)",
        "category": "patrimoine",
        "pk": "id_mutation",
        "default_order": "date_mutation DESC NULLS LAST",
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
        "default_order": "date_parution DESC",
        "search_cols": ["siren", "tribunal", "ville"],
        "preview_cols": [
            "date_parution",
            "siren",
            "typeavis_lib",
            "familleavis_lib",
            "tribunal",
            "ville",
            "departement",
        ],
    },
    "silver.judilibre_decisions": {
        "label": "Judilibre — Décisions (15k)",
        "category": "legal",
        "pk": "decision_id",
        "default_order": "decision_date DESC",
        "search_cols": ["siren", "juridiction"],
        "preview_cols": [
            "decision_date",
            "juridiction",
            "siren",
        ],
    },
    "silver.hatvp_lobbying": {
        "label": "HATVP Lobbyistes",
        "category": "risk",
        "pk": "representant_id",
        "default_order": "date_inscription DESC NULLS LAST",
        "search_cols": ["denomination", "siren", "secteur_activite", "adresse_ville"],
        "preview_cols": [
            "siren",
            "denomination",
            "secteur_activite",
            "date_inscription",
            "adresse_ville",
            "chiffre_affaires_lobbying",
            "has_active_lobbying",
        ],
    },
    "silver.sanctions": {
        "label": "Sanctions unifiées",
        "category": "risk",
        "pk": "sanction_uid",
        "default_order": "date_decision DESC NULLS LAST",
        "search_cols": ["entreprise", "siren", "motif"],
        "preview_cols": [
            "source",
            "siren",
            "entreprise",
            "date_decision",
            "type_decision",
            "severity",
            "montant_amende",
        ],
    },
    "silver.opensanctions": {
        "label": "OpenSanctions (280k)",
        "category": "risk",
        "pk": "entity_id",
        "default_order": "last_change DESC NULLS LAST",
        "search_cols": ["caption", "name", "name_lower"],
        "preview_cols": [
            "entity_id",
            "caption",
            "schema",
            "topics",
            "countries",
            "sanctions_programs",
        ],
    },
    "silver.gleif_lei": {
        "label": "GLEIF — LEI (10k)",
        "category": "core",
        "pk": "lei",
        "default_order": "lei",
        "search_cols": ["lei"],
        "preview_cols": [
            "lei",
        ],
    },
    "silver.osint_companies_enriched": {
        "label": "OSINT companies (3k)",
        "category": "osint",
        "pk": "siren",
        "default_order": "siren",
        "search_cols": ["siren"],
        "preview_cols": [
            "siren",
        ],
    },
    "silver.osint_persons_enriched": {
        "label": "OSINT persons (2k)",
        "category": "osint",
        "pk": "person_uid",
        "default_order": "n_total_social DESC NULLS LAST",
        "search_cols": ["nom"],
        "preview_cols": [
            "nom",
            "prenoms",
            "date_naissance",
            "siren_main",
            "denomination_main_company",
            "n_total_social",
            "has_linkedin",
            "has_github",
        ],
    },
}

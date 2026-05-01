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
        # Schema v3 PRO : colonnes legacy (score_ma/siege_dept/naf_libelle/ca_dernier/statut)
        # ont été renommées par le codegen LLM. Sans alignement, l'Explorer renvoie
        # 500 UndefinedColumnError.
        "default_order": "pro_ma_score DESC NULLS LAST",
        "search_cols": ["denomination", "siren", "code_ape", "adresse_dept"],
        "preview_cols": [
            "siren",
            "denomination",
            "code_ape",
            "adresse_dept",
            "ca_latest",
            "pro_ma_score",
            "insee_etat_administratif",
        ],
    },
    "gold.dirigeants_master": {
        "label": "Dirigeants (Master)",
        "category": "core",
        # Schema v3 PRO — yaml spec : grain `1 row par person_uid`,
        # score = pro_ma_score, mandats = n_mandats_actifs, age = age_2026.
        "pk": "person_uid",
        "default_order": "pro_ma_score DESC NULLS LAST",
        "search_cols": ["nom", "prenom"],
        "preview_cols": [
            "person_uid",
            "nom",
            "prenom",
            "n_mandats_actifs",
            "age_2026",
            "pro_ma_score",
        ],
    },
    "gold.cibles_ma_top": {
        "label": "Top cibles M&A",
        "category": "ma",
        "pk": "siren",
        # Schema v3 PRO — voir entreprises_master ci-dessus.
        "default_order": "deal_score_raw DESC NULLS LAST",
        "search_cols": ["denomination", "siren", "code_ape"],
        "preview_cols": [
            "siren",
            "denomination",
            "code_ape",
            "adresse_dept",
            "ca_latest",
            "deal_score_raw",
            "tier",
        ],
    },
    "gold.signaux_ma_feed": {
        "label": "Signaux M&A (feed)",
        "category": "signals",
        # Audit Explorer 2026-05-01 : colonnes alignées sur le vrai schema
        # (date_event vs event_date, event_type vs signal_type, event_id vs signal_id).
        "pk": "event_id",
        "default_order": "date_event DESC",
        "search_cols": ["denomination", "siren", "event_type"],
        "preview_cols": [
            "date_event",
            "event_type",
            "denomination",
            "siren",
            "code_ape",
            "adresse_dept",
            "score_total",
            "tier",
            "source",
        ],
    },
    "gold.network_mandats": {
        "label": "Réseau mandats (co-mandataires)",
        "category": "network",
        # Audit Explorer 2026-05-01 : grain réel = paire (person_uid_a, person_uid_b)
        # avec n_sirens_communs (pas person_id/edge_id/weight).
        "pk": "person_uid_a",
        "default_order": "n_sirens_communs DESC NULLS LAST",
        "search_cols": ["nom_a", "nom_b", "prenom_a", "prenom_b"],
        "preview_cols": [
            "nom_a",
            "prenom_a",
            "nom_b",
            "prenom_b",
            "n_sirens_communs",
        ],
    },
    "gold.balo_operations_realtime": {
        "label": "BALO opérations (temps réel)",
        "category": "signals",
        # Audit Explorer 2026-05-01 : announcement_id (pas operation_id),
        # date_publication (pas publication_date), pas de col 'montant'.
        "pk": "announcement_id",
        "default_order": "date_publication DESC NULLS LAST",
        "search_cols": ["denomination", "siren", "operation_type"],
        "preview_cols": [
            "date_publication",
            "operation_type",
            "denomination",
            "siren",
            "code_ape",
            "adresse_dept",
            "ca_latest",
            "score_total",
            "tier",
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
        # Audit Explorer 2026-05-01 : date_decision (pas decision_date),
        # pas de cols 'denomination', 'type_procedure', 'montant'.
        "pk": "decision_id",
        "default_order": "date_decision DESC NULLS LAST",
        "search_cols": ["juridiction", "titre", "searchable_text"],
        "preview_cols": [
            "date_decision",
            "juridiction_type",
            "juridiction",
            "chamber",
            "titre",
            "decision_id",
        ],
    },
    "gold.benchmarks_sectoriels": {
        "label": "Benchmarks sectoriels",
        "category": "analytics",
        # Audit Explorer 2026-05-01 : code_ape (pas 'naf'/'naf_libelle'),
        # ca_avg/median/p25/p75 (pas ebitda_median_pct/score_ma_median).
        "pk": "code_ape",
        "default_order": "n_entreprises DESC NULLS LAST",
        "search_cols": ["code_ape"],
        "preview_cols": [
            "code_ape",
            "n_entreprises",
            "n_with_ca",
            "ca_avg",
            "ca_median",
            "ca_p25",
            "ca_p75",
        ],
    },
    "gold.veille_reglementaire": {
        "label": "Veille réglementaire",
        "category": "regulatory",
        # Audit Explorer 2026-05-01 : texte_uid (pas doc_id), date_publication
        # (pas published_at), title/secteur_nom/impact_estime (pas type_doc/naf_impact).
        "pk": "texte_uid",
        "default_order": "date_publication DESC NULLS LAST",
        "search_cols": ["title", "secteur_nom", "source_db"],
        "preview_cols": [
            "date_publication",
            "source_db",
            "title",
            "secteur_code",
            "secteur_nom",
            "impact_estime",
        ],
    },
    "gold.persons_contacts_master": {
        "label": "Contacts dirigeants",
        "category": "osint",
        # Audit Explorer 2026-05-01 : person_uid (pas person_id), top_email/top_phone
        # (pas email/phone seul), pas de col 'confidence' ni 'source'.
        "pk": "person_uid",
        "default_order": "pro_ma_score DESC NULLS LAST",
        "search_cols": ["nom", "prenom", "top_email"],
        "preview_cols": [
            "person_uid",
            "nom",
            "prenom",
            "n_mandats_actifs",
            "top_email",
            "top_phone",
            "has_email",
            "has_phone",
            "pro_ma_score",
        ],
    },
    "gold.parcelles_cibles": {
        "label": "Parcelles foncières (par cible)",
        "category": "patrimoine",
        # Audit Explorer 2026-05-01 : grain = 1 row par siren cible (pas par parcelle).
        # Cols réelles : siren/n_parcelles/surface_totale_m2/valeur_immo_estimee_eur.
        "pk": "siren",
        "default_order": "valeur_immo_estimee_eur DESC NULLS LAST",
        "search_cols": ["denomination", "adresse_commune"],
        "preview_cols": [
            "siren",
            "denomination",
            "adresse_dept",
            "adresse_commune",
            "n_sci_dirigeants",
            "n_parcelles",
            "surface_totale_m2",
            "valeur_immo_estimee_eur",
            "score_total",
            "tier",
        ],
    },
    "gold.persons_master_universal": {
        "label": "Persons (Universal)",
        "category": "osint",
        # Audit Explorer 2026-05-01 : pas de col 'resolution_confidence' (n'existe pas).
        # Vrais champs : person_uid + n_mandats_actifs + n_companies + ca_total + pro_ma_score.
        "pk": "person_uid",
        "default_order": "pro_ma_score DESC NULLS LAST",
        "search_cols": ["nom", "prenom"],
        "preview_cols": [
            "person_uid",
            "nom",
            "prenom",
            "age_2026",
            "n_mandats_actifs",
            "n_companies",
            "ca_total",
            "pro_ma_score",
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
        # Audit Explorer 2026-05-01 : 'commune' n'existe pas → 'nom_commune'.
        "pk": "id_mutation",
        "default_order": "date_mutation DESC NULLS LAST",
        "search_cols": ["nom_commune", "code_postal", "code_commune"],
        "preview_cols": [
            "date_mutation",
            "nom_commune",
            "code_postal",
            "nature_mutation",
            "valeur_fonciere",
            "surface_reelle_bati",
            "type_local",
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
        # Audit Explorer 2026-05-01 : date_decision (pas decision_date),
        # ajout titre/numero_affaire pour utilité.
        "pk": "decision_id",
        "default_order": "date_decision DESC NULLS LAST",
        "search_cols": ["juridiction", "titre", "numero_affaire"],
        "preview_cols": [
            "date_decision",
            "juridiction_source",
            "juridiction",
            "chamber",
            "numero_affaire",
            "titre",
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

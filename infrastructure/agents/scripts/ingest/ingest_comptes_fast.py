#!/usr/bin/env python3
"""Optimized INPI RNE comptes annuels ingester — COPY-based, per-file worker.

Designed to be called in parallel by a driver (xargs -P N). Each invocation
processes ONE JSON file, independently.

Flow:
    1. Parse JSON file fully into memory (~75 MB, safe)
    2. Build in-memory buffers: depot rows, identite rows, liasse CSV stream
    3. One transaction:
       - executemany INSERT ... ON CONFLICT on depots + identite (10-12k rows each)
       - COPY FROM STDIN for liasses (500k-1M rows)
    4. Commit + exit with stats

Usage:
    ingest_comptes_fast.py <file.json>
    Env: DSN=postgresql://...   (required)
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation

import psycopg


def _d(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date().isoformat()
    except Exception:
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d").date().isoformat()
        except Exception:
            return None


def _ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def _n(v):
    if v is None or v == "":
        return None
    try:
        return str(Decimal(str(v).lstrip("0") or "0"))
    except (InvalidOperation, ValueError):
        return None


def _int(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


DEPOT_SQL = """
INSERT INTO bronze.inpi_comptes_depots
  (depot_id, siren, denomination, date_depot, date_cloture,
   num_chrono, confidentiality, type_bilan, deleted,
   updated_at_src, payload)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (depot_id) DO UPDATE SET
  payload = EXCLUDED.payload,
  ingested_at = now(),
  deleted = EXCLUDED.deleted
"""

IDENTITE_SQL = """
INSERT INTO bronze.inpi_comptes_identite
  (depot_id, siren, date_cloture, date_cloture_n_moins_1,
   code_greffe, num_depot, num_gestion, code_activite,
   duree_exercice_n, duree_exercice_n_moins_1,
   code_saisie, code_type_bilan, code_devise, code_origine_devise,
   code_confidentialite, adresse)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (depot_id) DO NOTHING
"""

COPY_LIASSES_SQL = (
    "COPY bronze.inpi_comptes_liasses "
    "(depot_id, siren, date_cloture, page_num, code, m1, m2, m3, m4) "
    "FROM STDIN WITH (FORMAT CSV, NULL '', DELIMITER E'\\t')"
)


def process_file(path: str, dsn: str) -> dict:
    t0 = time.time()
    with open(path, "rb") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected JSON array")
    t_parse = time.time() - t0

    depot_rows: list[tuple] = []
    identite_rows: list[tuple] = []
    liasse_buf = io.StringIO()
    liasse_writer = csv.writer(liasse_buf, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    seen_liasses: set[tuple] = set()
    n_liasses_built = 0

    for rec in data:
        depot_id = rec.get("id")
        if not depot_id:
            continue
        depot_id = str(depot_id)[:128]
        siren_raw = rec.get("siren")
        siren = (str(siren_raw).zfill(9)[:9]) if siren_raw else None

        bilan_root = (rec.get("bilanSaisi") or {}).get("bilan") or {}
        identite = bilan_root.get("identite") or {}
        date_cloture = _d(identite.get("dateClotureExercice") or rec.get("dateCloture"))

        depot_rows.append((
            depot_id, siren, rec.get("denomination"),
            _d(rec.get("dateDepot")), date_cloture,
            rec.get("numChrono"), rec.get("confidentiality"),
            rec.get("typeBilan") or identite.get("codeTypeBilan"),
            bool(rec.get("deleted")),
            _ts(rec.get("updatedAt")),
            psycopg.types.json.Jsonb(rec),
        ))

        if identite:
            identite_rows.append((
                depot_id, siren,
                _d(identite.get("dateClotureExercice")),
                _d(identite.get("dateClotureExerciceNMoins1")),
                identite.get("codeGreffe"),
                identite.get("numDepot"),
                identite.get("numGestion"),
                identite.get("codeActivite"),
                _int(identite.get("dureeExerciceN")),
                _int(identite.get("dureeExerciceNMoins1")),
                identite.get("codeSaisie"),
                identite.get("codeTypeBilan"),
                identite.get("codeDevise"),
                identite.get("codeOrigineDevise"),
                identite.get("codeConfidentialite"),
                identite.get("adresse"),
            ))

        detail = bilan_root.get("detail") or {}
        for page in detail.get("pages") or []:
            if not isinstance(page, dict):
                continue
            page_num = _int(page.get("numero")) or 0
            for liasse in page.get("liasses") or []:
                if not isinstance(liasse, dict):
                    continue
                code = liasse.get("code")
                if not code:
                    continue
                code = str(code)[:8]
                key = (depot_id, page_num, code)
                if key in seen_liasses:
                    continue
                seen_liasses.add(key)
                liasse_writer.writerow([
                    depot_id,
                    siren or "",
                    date_cloture or "",
                    page_num,
                    code,
                    _n(liasse.get("m1")) or "",
                    _n(liasse.get("m2")) or "",
                    _n(liasse.get("m3")) or "",
                    _n(liasse.get("m4")) or "",
                ])
                n_liasses_built += 1

    t_build = time.time() - t0 - t_parse
    t_db0 = time.time()

    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            # 1) Depots
            cur.executemany(DEPOT_SQL, depot_rows)
            # 2) Identite
            cur.executemany(IDENTITE_SQL, identite_rows)
            # 3) Liasses via COPY (dedup against existing via staging if non-empty run)
            liasse_buf.seek(0)
            # Use staging to allow ON CONFLICT DO NOTHING semantics without TRUNCATE
            cur.execute(
                "CREATE TEMP TABLE _stage_liasses (LIKE bronze.inpi_comptes_liasses INCLUDING DEFAULTS) ON COMMIT DROP"
            )
            with cur.copy(
                "COPY _stage_liasses (depot_id, siren, date_cloture, page_num, code, m1, m2, m3, m4) "
                "FROM STDIN WITH (FORMAT CSV, NULL '', DELIMITER E'\\t')"
            ) as cp:
                # Write in 4MB chunks to stay memory-friendly
                chunk = 4 * 1024 * 1024
                buf_val = liasse_buf.getvalue()
                for i in range(0, len(buf_val), chunk):
                    cp.write(buf_val[i:i + chunk])
            cur.execute(
                "INSERT INTO bronze.inpi_comptes_liasses "
                "(depot_id, siren, date_cloture, page_num, code, m1, m2, m3, m4) "
                "SELECT depot_id, siren, date_cloture, page_num, code, m1, m2, m3, m4 "
                "FROM _stage_liasses "
                "ON CONFLICT (depot_id, page_num, code) DO NOTHING"
            )
            liasses_inserted = cur.rowcount or 0
        conn.commit()

    t_db = time.time() - t_db0
    total = time.time() - t0
    return {
        "file": os.path.basename(path),
        "depots": len(depot_rows),
        "identites": len(identite_rows),
        "liasses_built": n_liasses_built,
        "liasses_inserted": liasses_inserted,
        "t_parse_s": round(t_parse, 2),
        "t_build_s": round(t_build, 2),
        "t_db_s": round(t_db, 2),
        "t_total_s": round(total, 2),
        "records_per_s": round(len(depot_rows) / total, 1) if total > 0 else 0,
    }


def main():
    if len(sys.argv) < 2:
        print("usage: ingest_comptes_fast.py <file.json>", file=sys.stderr)
        sys.exit(2)
    dsn = os.environ.get("DSN")
    if not dsn:
        print("DSN env var required", file=sys.stderr)
        sys.exit(2)
    stats = process_file(sys.argv[1], dsn)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()

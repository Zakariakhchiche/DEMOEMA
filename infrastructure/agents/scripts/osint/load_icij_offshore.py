#!/usr/bin/env python3
"""ICIJ Offshore Leaks — loader des dumps CSV vers bronze.icij_offshore_raw.

ICIJ ne fournit PAS d'API REST. Le dump complet (Panama Papers + Paradise +
Pandora + Bahamas + Offshore Leaks) doit être téléchargé MANUELLEMENT depuis
https://offshoreleaks.icij.org/pages/database (acceptation disclaimer requis).

Une fois le ZIP downloadé, dézippe-le sur le VPS dans /root/icij_dumps/ :
    /root/icij_dumps/nodes-officers.csv      (~600K personnes physiques)
    /root/icij_dumps/nodes-entities.csv      (~800K shell companies)
    /root/icij_dumps/nodes-addresses.csv     (~750K adresses)
    /root/icij_dumps/nodes-intermediaries.csv (~27K cabinets fiscaux)
    /root/icij_dumps/relationships.csv       (qui contrôle quoi)

Ce script :
1. Vérifie la présence des CSV.
2. Charge officers + entities dans bronze.icij_offshore_raw (table existante)
   avec node_type='OFFICER' ou 'ENTITY' encodé dans la colonne `role`.
3. Idempotent : ON CONFLICT (node_id) DO UPDATE.

Usage :
    DSN=postgres://... python3 load_icij_offshore.py [--dump-dir /root/icij_dumps]
    DSN=postgres://... python3 load_icij_offshore.py --check  # juste verify

Suite : créer la silver MV silver.icij_offshore_match qui matche
(officer.name) vs (dirigeant.nom + prenom) — voir setup_icij_silver_mv.sql.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

DEFAULT_DUMP_DIR = Path("/root/icij_dumps")
EXPECTED_FILES = {
    "officers": "nodes-officers.csv",
    "entities": "nodes-entities.csv",
    "addresses": "nodes-addresses.csv",
    "intermediaries": "nodes-intermediaries.csv",
    "relationships": "relationships.csv",
}

UPSERT_SQL = """
INSERT INTO bronze.icij_offshore_raw
  (node_id, name, country, source_leak, role, payload, ingested_at)
VALUES (%s, %s, %s, %s, %s, %s, NOW())
ON CONFLICT (node_id) DO UPDATE SET
  name = EXCLUDED.name,
  country = EXCLUDED.country,
  source_leak = EXCLUDED.source_leak,
  role = EXCLUDED.role,
  payload = EXCLUDED.payload,
  ingested_at = NOW()
"""

BATCH_SIZE = 5000


def check_dumps(dump_dir: Path) -> tuple[bool, list[str]]:
    """Verify dump files exist. Returns (all_present, missing_list)."""
    missing = []
    for key, fname in EXPECTED_FILES.items():
        fpath = dump_dir / fname
        if not fpath.exists():
            missing.append(fname)
    return len(missing) == 0, missing


def _truncate(s: str | None, max_len: int) -> str | None:
    """Truncate string to fit DB column."""
    if not s:
        return None
    return s[:max_len]


def _load_csv(cur, csv_path: Path, node_type: str) -> int:
    """Load one CSV file into bronze.icij_offshore_raw. Returns row count.

    node_type ∈ {'OFFICER', 'ENTITY', 'ADDRESS', 'INTERMEDIARY'}
    """
    print(f"[ICIJ] Loading {csv_path.name} as {node_type}...", file=sys.stderr)
    n_rows = 0
    batch = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_id = row.get("node_id") or row.get("id") or ""
            if not node_id:
                continue
            name = row.get("name") or row.get("address") or ""
            country = row.get("countries") or row.get("country_codes") or ""
            source_leak = row.get("sourceID") or row.get("source") or ""
            role = node_type
            batch.append((
                _truncate(node_id, 64),
                _truncate(name, 512),
                _truncate(country, 128),
                _truncate(source_leak, 64),
                _truncate(role, 128),
                Jsonb(row),
            ))
            if len(batch) >= BATCH_SIZE:
                cur.executemany(UPSERT_SQL, batch)
                n_rows += len(batch)
                batch.clear()
                if n_rows % 50000 == 0:
                    print(f"  [{node_type}] {n_rows} rows loaded", file=sys.stderr)
        if batch:
            cur.executemany(UPSERT_SQL, batch)
            n_rows += len(batch)
    print(f"[ICIJ] {csv_path.name} done: {n_rows} rows", file=sys.stderr)
    return n_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=DEFAULT_DUMP_DIR)
    ap.add_argument("--check", action="store_true",
                    help="Just verify files presence, no load")
    args = ap.parse_args()

    if not args.dump_dir.exists():
        print(f"ERROR: dump dir {args.dump_dir} does not exist.", file=sys.stderr)
        print("Create it with: mkdir -p /root/icij_dumps", file=sys.stderr)
        print("Then download dumps from:", file=sys.stderr)
        print("  https://offshoreleaks.icij.org/pages/database", file=sys.stderr)
        sys.exit(2)

    ok, missing = check_dumps(args.dump_dir)
    if not ok:
        print(f"Missing files in {args.dump_dir}:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print("\nDownload from https://offshoreleaks.icij.org/pages/database", file=sys.stderr)
        print("(unzip and place in /root/icij_dumps/)", file=sys.stderr)
        sys.exit(2)

    if args.check:
        print(f"OK: all {len(EXPECTED_FILES)} files present in {args.dump_dir}")
        sys.exit(0)

    dsn = os.environ.get("DSN")
    if not dsn:
        print("ERROR: DSN env var required", file=sys.stderr)
        sys.exit(2)

    total = 0
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            # Load OFFICERS first (priority for M&A : individus)
            total += _load_csv(cur, args.dump_dir / EXPECTED_FILES["officers"], "OFFICER")
            conn.commit()
            # Then ENTITIES (shell companies)
            total += _load_csv(cur, args.dump_dir / EXPECTED_FILES["entities"], "ENTITY")
            conn.commit()
            # Skip addresses + intermediaries pour l'instant (moins critique M&A)

    print(json.dumps({"loaded_total": total, "source": "icij_offshore"}))


if __name__ == "__main__":
    main()

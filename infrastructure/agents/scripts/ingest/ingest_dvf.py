#!/usr/bin/env python3
"""Ingest DVF national (Demandes de Valeurs Foncières) from Etalab.

Downloads https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/full.csv.gz per year,
streams CSV and bulk-COPY into bronze.dvf_transactions_raw.

Usage: ingest_dvf.py [--years 2021,2022,2023,2024,2025]
Env: DSN
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, io, json, os, sys, time
import urllib.request
from datetime import datetime
import psycopg


DVF_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/full.csv.gz"

# Column order matches DVF CSV (40 columns)
CSV_COLS = [
    "id_mutation", "date_mutation", "numero_disposition", "nature_mutation", "valeur_fonciere",
    "adresse_numero", "adresse_suffixe", "adresse_nom_voie", "adresse_code_voie", "code_postal",
    "code_commune", "nom_commune", "code_departement", "ancien_code_commune", "ancien_nom_commune",
    "id_parcelle", "ancien_id_parcelle", "numero_volume",
    "lot1_numero", "lot1_surface_carrez", "lot2_numero", "lot2_surface_carrez",
    "lot3_numero", "lot3_surface_carrez", "lot4_numero", "lot4_surface_carrez",
    "lot5_numero", "lot5_surface_carrez", "nombre_lots",
    "code_type_local", "type_local", "surface_reelle_bati", "nombre_pieces_principales",
    "code_nature_culture", "nature_culture", "code_nature_culture_speciale", "nature_culture_speciale",
    "surface_terrain", "longitude", "latitude",
]

TABLE_COLS = ["tx_uid"] + CSV_COLS + ["year"]

COPY_SQL = (
    "COPY _stg ({cols}) FROM STDIN WITH (FORMAT CSV, NULL '', DELIMITER E'\\t')"
    .format(cols=", ".join(TABLE_COLS))
)


def _uid(id_mutation, parcelle, lot1, num_disposition) -> str:
    parts = [str(id_mutation or ""), str(parcelle or ""), str(lot1 or ""), str(num_disposition or "")]
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:40]


def _clean(v: str | None) -> str:
    """Strip CR/LF/tabs from fields; keep empty strings as-is (→ NULL via COPY)."""
    if v is None:
        return ""
    return v.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def stream_year(year: int, cur, conn, out_buf: io.StringIO) -> dict:
    url = DVF_URL.format(year=year)
    t0 = time.time()
    # Download directly to memory stream + gunzip
    print(f"[{year}] downloading {url}", file=sys.stderr, flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "DEMOEMA-DVF/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
    print(f"[{year}] got {len(raw)//1024//1024}MB compressed, gunzipping", file=sys.stderr, flush=True)
    text = gzip.decompress(raw).decode("utf-8")
    print(f"[{year}] gunzipped {len(text)//1024//1024}MB text", file=sys.stderr, flush=True)

    reader = csv.DictReader(io.StringIO(text))
    writer = csv.writer(out_buf, delimiter="\t", quoting=csv.QUOTE_MINIMAL,
                        doublequote=True, lineterminator="\n")

    n_rows = 0
    cur.execute("CREATE TEMP TABLE _stg (LIKE bronze.dvf_transactions_raw INCLUDING DEFAULTS) ON COMMIT DROP")

    def flush():
        nonlocal out_buf
        data = out_buf.getvalue()
        if not data:
            return
        with cur.copy(COPY_SQL) as cp:
            chunk_size = 4 * 1024 * 1024
            for i in range(0, len(data), chunk_size):
                cp.write(data[i:i + chunk_size])
        out_buf.seek(0)
        out_buf.truncate()

    FLUSH_EVERY = 200000
    in_buf = 0
    for row in reader:
        uid = _uid(row.get("id_mutation"), row.get("id_parcelle"),
                   row.get("lot1_numero"), row.get("numero_disposition"))
        writer.writerow(
            [uid] +
            [_clean(row.get(c)) for c in CSV_COLS] +
            [str(year)]
        )
        n_rows += 1
        in_buf += 1
        if in_buf >= FLUSH_EVERY:
            flush()
            in_buf = 0

    flush()

    # INSERT from stage -> target with ON CONFLICT DO NOTHING
    print(f"[{year}] copied {n_rows} rows to stage, inserting to bronze", file=sys.stderr, flush=True)
    cur.execute(
        "INSERT INTO bronze.dvf_transactions_raw ({cols}) SELECT {cols} FROM _stg ON CONFLICT (tx_uid) DO NOTHING"
        .format(cols=", ".join(TABLE_COLS))
    )
    inserted = cur.rowcount or 0
    cur.execute("DROP TABLE _stg")
    conn.commit()

    return {"year": year, "rows_read": n_rows, "inserted": inserted,
            "duration_s": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2021,2022,2023,2024,2025")
    args = ap.parse_args()
    years = [int(y) for y in args.years.split(",")]

    dsn = os.environ["DSN"]
    results = []
    out_buf = io.StringIO()

    with psycopg.connect(dsn, autocommit=False) as conn:
        for y in years:
            with conn.cursor() as cur:
                try:
                    r = stream_year(y, cur, conn, out_buf)
                    results.append(r)
                    print(f"[{y}] OK → {r}", file=sys.stderr, flush=True)
                except Exception as e:
                    print(f"[{y}] FAIL: {type(e).__name__}: {e}", file=sys.stderr)
                    conn.rollback()
                    results.append({"year": y, "error": str(e)})

    print(json.dumps({"results": results}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Patch observations: re-parse formalites JSON files extracting observations.rcs/rnm
and insert into bronze.inpi_formalites_observations."""
from __future__ import annotations
import csv, hashlib, io, json, os, sys, time
from datetime import datetime
import psycopg

COLS = "observation_uid, formality_id, siren, date_observation, type_observation, libelle, payload"


def _d(s):
    if not s:
        return ""
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date().isoformat()
    except Exception:
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d").date().isoformat()
        except Exception:
            return ""


def _uid(*parts):
    return hashlib.sha1("|".join(str(p or "") for p in parts).encode()).hexdigest()[:40]


def extract(rec):
    """Return list of tuples for observations extracted from one formality record."""
    formality = rec.get("formality") or {}
    content = formality.get("content") or {}
    # Try each subtree
    rows = []
    formality_id = str(rec.get("id") or "")[:128]
    siren = (str(rec.get("siren") or "").zfill(9)[:9]) or None
    if not formality_id:
        return rows
    for subtree_name in ("personneMorale", "personnePhysique", "exploitation"):
        block = content.get(subtree_name) or {}
        if not isinstance(block, dict):
            continue
        observations = block.get("observations")
        # Structure: observations = {rcs: [...], rnm: [...]} (dict, not list)
        if not isinstance(observations, dict):
            continue
        for origin in ("rcs", "rnm"):
            entries = observations.get(origin) or []
            if not isinstance(entries, list):
                continue
            for j, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                uid = _uid(formality_id, "obs", subtree_name, origin, j,
                           entry.get("numObservation") or "")
                rows.append((
                    uid, formality_id, siren,
                    _d(entry.get("dateAjout") or entry.get("dateGreffe")),
                    f"{origin}:{entry.get('etatObs') or ''}",
                    (entry.get("texte") or "").replace("\n", " ").replace("\r", " ").strip(),
                    json.dumps({**entry, "_origin": origin, "_subtree": subtree_name},
                                ensure_ascii=False, default=str),
                ))
    return rows


def write_csv(buf, row):
    w = csv.writer(buf, delimiter="\t", quoting=csv.QUOTE_MINIMAL, doublequote=True,
                   lineterminator="\n")
    w.writerow(["" if v is None else v for v in row])


def process_file(path, dsn):
    t0 = time.time()
    with open(path, "rb") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return {"file": os.path.basename(path), "built": 0, "inserted": 0, "err": "not array"}
    buf = io.StringIO()
    built = 0
    for rec in data:
        if not isinstance(rec, dict):
            continue
        for row in extract(rec):
            write_csv(buf, row)
            built += 1
    if built == 0:
        return {"file": os.path.basename(path), "built": 0, "inserted": 0,
                "t": round(time.time() - t0, 2)}
    with psycopg.connect(dsn, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute(
            "CREATE TEMP TABLE _stg (LIKE bronze.inpi_formalites_observations INCLUDING DEFAULTS) ON COMMIT DROP"
        )
        with cur.copy(
            f"COPY _stg ({COLS}) FROM STDIN WITH (FORMAT CSV, NULL '', DELIMITER E'\\t')"
        ) as cp:
            payload = buf.getvalue()
            chunk = 4 * 1024 * 1024
            for i in range(0, len(payload), chunk):
                cp.write(payload[i:i + chunk])
        cur.execute(
            f"INSERT INTO bronze.inpi_formalites_observations ({COLS}) "
            f"SELECT {COLS} FROM _stg ON CONFLICT (observation_uid) DO NOTHING"
        )
        inserted = cur.rowcount or 0
        conn.commit()
    return {"file": os.path.basename(path), "built": built, "inserted": inserted,
            "t": round(time.time() - t0, 2)}


def main():
    path = sys.argv[1]
    dsn = os.environ["DSN"]
    print(json.dumps(process_file(path, dsn)))


if __name__ == "__main__":
    main()

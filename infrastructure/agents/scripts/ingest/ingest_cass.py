#!/usr/bin/env python3
"""Ingest CASS (Cour de cassation) decisions from DILA tar.gz archives.

Usage: ingest_cass.py <dir_with_tar_gz>   (env: DSN)
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import tarfile
import time
from datetime import datetime

import psycopg
from lxml import etree


def _txt(node, xpath: str) -> str | None:
    el = node.find(xpath)
    if el is None:
        return None
    text = "".join(el.itertext()).strip() or None
    return text


def _date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _week_from_name(path: str):
    m = re.search(r"(?:CASS|CAPP|JADE|CONSTIT)_(\d{8})", os.path.basename(path))
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%d").date()
    except Exception:
        return None


def _chamber_from_path(path: str) -> str | None:
    """DILA folder layout encodes chamber: /civile/ /criminelle/ /commerciale/ etc."""
    for kw in ("civile", "criminelle", "commerciale", "sociale", "penale", "mixte"):
        if f"/{kw}/" in path.lower():
            return kw
    return None


INSERT_SQL_TMPL = """
INSERT INTO {table}
  (decision_id, juridiction, chamber, date_decision, theme, numero_affaire,
   solution, titre, formation, nature, publie_bull, date_dec_att, formation_att,
   url_source, contenu, archive_week, payload, ingested_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (decision_id) DO UPDATE SET
  archive_week = EXCLUDED.archive_week,
  payload = EXCLUDED.payload,
  ingested_at = now()
"""


def _find_any(root, xpaths):
    for x in xpaths:
        el = root.find(x)
        if el is not None:
            return el
    return None


def parse_xml(raw: bytes, archive_week, file_path: str) -> tuple | None:
    try:
        root = etree.fromstring(raw)
    except etree.XMLSyntaxError:
        return None

    meta_commun = root.find(".//META_COMMUN") or root
    meta_juri = root.find(".//META_JURI") or root
    meta_juri_judi = _find_any(root, [
        ".//META_JURI_JUDI", ".//META_JURI_ADMIN", ".//META_JURI_CONSTIT",
    ]) or root

    decision_id = _txt(meta_commun, "ID")
    if not decision_id:
        return None
    decision_id = decision_id[:128]

    numero_affaire = _txt(meta_juri_judi, "NUMEROS_AFFAIRES/NUMERO_AFFAIRE") or _txt(meta_juri, "NUMERO")
    publi_bull_el = meta_juri_judi.find("PUBLI_BULL")
    publie_bull = None
    if publi_bull_el is not None:
        publie_bull = publi_bull_el.get("publie") == "oui"

    texte_el = root.find(".//TEXTE")
    contenu = None
    if texte_el is not None:
        contenu = "".join(texte_el.itertext()).strip() or None
        # Truncate extremely long decisions to keep rows reasonable (full text in payload)
        if contenu and len(contenu) > 200_000:
            contenu = contenu[:200_000] + "...[truncated]"

    url_source = _txt(meta_commun, "URL")
    titre = _txt(meta_juri, "TITRE")
    theme_el = meta_juri.find("TITRE")  # closest thing to a theme in DILA XML
    theme = titre  # reuse title as theme for now
    nature = _txt(meta_commun, "NATURE")
    if nature:
        nature = nature[:32]

    payload = {
        "meta_commun": {c.tag: ("".join(c.itertext()) or None) for c in meta_commun} if meta_commun is not root else {},
        "meta_juri": {c.tag: ("".join(c.itertext()) or None) for c in meta_juri} if meta_juri is not root else {},
        "meta_juri_judi": {c.tag: ("".join(c.itertext()) or None) for c in meta_juri_judi} if meta_juri_judi is not root else {},
        "source_file": file_path,
    }

    return (
        decision_id,
        _txt(meta_juri, "JURIDICTION"),
        _chamber_from_path(file_path),
        _date(_txt(meta_juri, "DATE_DEC")),
        theme,
        numero_affaire[:64] if numero_affaire else None,
        _txt(meta_juri, "SOLUTION"),
        titre,
        _txt(meta_juri_judi, "FORMATION"),
        nature,
        publie_bull,
        _date(_txt(meta_juri_judi, "DATE_DEC_ATT")),
        _txt(meta_juri_judi, "FORM_DEC_ATT"),
        url_source,
        contenu,
        archive_week,
        psycopg.types.json.Jsonb(payload),
    )


def main():
    if len(sys.argv) < 3:
        print("usage: ingest_cass.py <dir> <source:CASS|CAPP|JADE|CONSTIT> [--table name]",
              file=sys.stderr)
        sys.exit(2)
    archive_dir = sys.argv[1]
    source = sys.argv[2].upper()
    table = None
    if "--table" in sys.argv:
        table = sys.argv[sys.argv.index("--table") + 1]
    if not table:
        table_map = {
            "CASS": "bronze.judilibre_decisions_raw",
            "CAPP": "bronze.juri_capp_raw",
            "JADE": "bronze.juri_jade_raw",
            "CONSTIT": "bronze.juri_constit_raw",
        }
        table = table_map.get(source)
        if not table:
            print(f"unknown source {source}", file=sys.stderr)
            sys.exit(2)
    INSERT_SQL = INSERT_SQL_TMPL.format(table=table)
    dsn = os.environ.get("DSN")
    if not dsn:
        print("DSN required", file=sys.stderr)
        sys.exit(2)

    archives = sorted(glob.glob(os.path.join(archive_dir, f"{source}_*.tar.gz")))
    print(f"found {len(archives)} {source} archives → {table}", file=sys.stderr)

    total_ok = 0
    total_fail = 0
    total_files = 0
    t0 = time.time()

    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            for ai, archive in enumerate(archives, 1):
                week = _week_from_name(archive)
                t_arch = time.time()
                ok = 0
                fail = 0
                batch = []
                try:
                    with tarfile.open(archive, "r:gz") as tf:
                        for member in tf:
                            if not member.isfile() or not member.name.endswith(".xml"):
                                continue
                            total_files += 1
                            try:
                                f = tf.extractfile(member)
                                if f is None:
                                    fail += 1
                                    continue
                                raw = f.read()
                                row = parse_xml(raw, week, member.name)
                                if row:
                                    batch.append(row)
                                    ok += 1
                                else:
                                    fail += 1
                            except Exception:
                                fail += 1
                            if len(batch) >= 500:
                                cur.executemany(INSERT_SQL, batch)
                                batch.clear()
                                conn.commit()
                        if batch:
                            cur.executemany(INSERT_SQL, batch)
                            batch.clear()
                            conn.commit()
                except Exception as e:
                    print(f"archive {archive}: {type(e).__name__}: {e}", file=sys.stderr)
                total_ok += ok
                total_fail += fail
                print(f"[{ai}/{len(archives)}] {os.path.basename(archive)} "
                      f"week={week} ok={ok} fail={fail} took={round(time.time()-t_arch,1)}s",
                      file=sys.stderr, flush=True)

    print(json.dumps({
        "archives": len(archives),
        "xml_files": total_files,
        "inserted_ok": total_ok,
        "failed": total_fail,
        "duration_s": round(time.time() - t0, 1),
    }))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Ingest CNIL deliberations from DILA tar.gz archives."""
from __future__ import annotations
import glob, os, re, sys, tarfile, time, json
from datetime import datetime
import psycopg
from lxml import etree


def _txt(node, xpath):
    if node is None:
        return None
    el = node.find(xpath)
    if el is None:
        return None
    return ("".join(el.itertext()).strip() or None)


def _date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _week(p):
    m = re.search(r"CNIL_(\d{8})", os.path.basename(p))
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%d").date()
    except Exception:
        return None


INSERT_SQL = """
INSERT INTO bronze.cnil_deliberations_raw
  (decision_id, numero, titre, titre_full, nature, nature_delib,
   date_texte, origine_publi, nor, url_source, contenu, archive_week, payload, ingested_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (decision_id) DO UPDATE SET
  archive_week = EXCLUDED.archive_week,
  payload = EXCLUDED.payload,
  ingested_at = now()
"""


def parse(raw, week, path):
    try:
        root = etree.fromstring(raw)
    except etree.XMLSyntaxError:
        return None
    mc = root.find(".//META_COMMUN")
    mcnil = root.find(".//META_CNIL")
    if mc is None:
        return None
    decision_id = _txt(mc, "ID")
    if not decision_id:
        return None
    texte_el = root.find(".//TEXTE")
    contenu = "".join(texte_el.itertext()).strip() if texte_el is not None else None
    if contenu and len(contenu) > 200_000:
        contenu = contenu[:200_000] + "...[truncated]"
    payload = {
        "source_file": path,
        "meta_commun": {c.tag: ("".join(c.itertext()) or None) for c in (mc if mc is not None else [])},
        "meta_cnil": {c.tag: ("".join(c.itertext()) or None) for c in (mcnil if mcnil is not None else [])},
    }
    nature_delib = _txt(mcnil, "NATURE_DELIB") if mcnil is not None else None
    return (
        decision_id[:128],
        _txt(mcnil, "NUMERO") if mcnil is not None else None,
        _txt(mcnil, "TITRE") if mcnil is not None else None,
        _txt(mcnil, "TITREFULL") if mcnil is not None else None,
        _txt(mc, "NATURE"),
        nature_delib,
        _date(_txt(mcnil, "DATE_TEXTE") if mcnil is not None else None),
        _txt(mcnil, "ORIGINE_PUBLI") if mcnil is not None else None,
        _txt(mcnil, "NOR") if mcnil is not None else None,
        _txt(mc, "URL"),
        contenu,
        week,
        psycopg.types.json.Jsonb(payload),
    )


def main():
    archives = sorted(glob.glob(os.path.join(sys.argv[1], "CNIL_*.tar.gz")))
    dsn = os.environ["DSN"]
    total_ok = total_fail = total_files = 0
    t0 = time.time()
    with psycopg.connect(dsn, autocommit=False) as conn, conn.cursor() as cur:
        for ai, arch in enumerate(archives, 1):
            week = _week(arch)
            ok = fail = 0
            batch = []
            try:
                with tarfile.open(arch, "r:gz") as tf:
                    for m in tf:
                        if not m.isfile() or not m.name.endswith(".xml"):
                            continue
                        total_files += 1
                        try:
                            raw = tf.extractfile(m).read()
                            row = parse(raw, week, m.name)
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
                print(f"archive {arch}: {e}", file=sys.stderr)
            total_ok += ok
            total_fail += fail
            print(f"[{ai}/{len(archives)}] {os.path.basename(arch)} week={week} ok={ok} fail={fail}",
                  file=sys.stderr, flush=True)
    print(json.dumps({"archives": len(archives), "xml_files": total_files,
                      "ok": total_ok, "fail": total_fail,
                      "duration_s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()

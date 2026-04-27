"""Vérification complétude bronze vs upstream.

À tourner sur le VPS DEMOEMA après une migration ou un backfill, pour vérifier
que chaque source a bien chargé la totalité de l'upstream (et pas juste un
subset partiel) :

    docker exec demomea-agents-platform python -m verify_bronze_completeness

Sortie JSON sur stdout, plus rapport tabulaire sur stderr. Exit code :
  0  → toutes les sources sont OK ou n'ont pas de count_upstream
  1  → au moins une source est < 90% de son upstream
  2  → erreur d'exécution

Catégories par source :
  ✅ ok              : count_upstream dispo + ratio >= 0.9
  ⚠️  partial        : count_upstream dispo + ratio < 0.9
  ❌ empty          : bronze table = 0 row (jamais ingéré)
  ℹ️  no_upstream    : pas de count_upstream() défini → pas vérifiable auto
  ❌ table_missing  : bronze table n'existe pas (spec orpheline)

Pour les sources `no_upstream`, l'opérateur doit vérifier manuellement
ou ajouter une fonction `async def count_upstream()` dans le module source.
"""
from __future__ import annotations

import asyncio
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import psycopg
import yaml

from config import settings

INGESTION_DIR = Path(__file__).parent / "ingestion"
SPECS_DIR = INGESTION_DIR / "specs"
SOURCES_DIR = INGESTION_DIR / "sources"

PARTIAL_THRESHOLD = 0.90  # < 90% du upstream → flagged "partial"


def _bronze_table_for(spec: dict, source_id: str) -> str:
    """Convention DEMOEMA : `bronze_table` dans spec, sinon `bronze.<sid>_raw`."""
    return spec.get("bronze_table") or f"bronze.{source_id}_raw"


def _count_local(qualified: str) -> int | None:
    """count(*) exact sur la bronze table (lent sur big tables mais on n'a pas
    le choix pour la complétude). Renvoie None si table absente."""
    if not settings.database_url or "." not in qualified:
        return None
    schema, table = qualified.split(".", 1)
    try:
        with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname=%s AND c.relname=%s AND c.relkind='r' LIMIT 1",
                (schema, table),
            )
            if cur.fetchone() is None:
                return None  # table absente
            cur.execute(f"SELECT count(*) FROM {schema}.{table}")
            return int(cur.fetchone()[0])
    except Exception:
        return None


async def _count_upstream_for(source_id: str) -> int | None:
    """Importe le module source et appelle `count_upstream()` si défini."""
    py = SOURCES_DIR / f"{source_id}.py"
    if not py.exists():
        return None
    try:
        mod = importlib.import_module(f"ingestion.sources.{source_id}")
        fn = getattr(mod, "count_upstream", None)
        if fn is None:
            return None
        result = await fn() if asyncio.iscoroutinefunction(fn) else fn()
        return int(result) if isinstance(result, (int, float)) and result >= 0 else None
    except Exception:
        return None


async def verify_all() -> list[dict[str, Any]]:
    """Itère les specs, classe chaque source. Retourne une liste de dicts."""
    if not SPECS_DIR.exists():
        return []
    out: list[dict[str, Any]] = []
    for spec_path in sorted(SPECS_DIR.glob("*.yaml")):
        if spec_path.name.startswith("_"):
            continue
        try:
            spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        sid = spec.get("source_id")
        if not sid:
            continue
        bronze_table = _bronze_table_for(spec, sid)
        local = _count_local(bronze_table)
        if local is None:
            out.append({
                "source_id": sid, "bronze_table": bronze_table,
                "local": None, "upstream": None,
                "ratio": None, "status": "table_missing",
            })
            continue
        upstream = await _count_upstream_for(sid)
        if upstream is None:
            status = "empty" if local == 0 else "no_upstream"
            out.append({
                "source_id": sid, "bronze_table": bronze_table,
                "local": local, "upstream": None,
                "ratio": None, "status": status,
            })
            continue
        ratio = (local / upstream) if upstream > 0 else None
        if local == 0:
            status = "empty"
        elif ratio is not None and ratio < PARTIAL_THRESHOLD:
            status = "partial"
        else:
            status = "ok"
        out.append({
            "source_id": sid, "bronze_table": bronze_table,
            "local": local, "upstream": upstream,
            "ratio": round(ratio, 4) if ratio is not None else None,
            "status": status,
        })
    return out


def _print_report(results: list[dict[str, Any]]) -> int:
    """Imprime un rapport tabulaire sur stderr. Retourne le code de sortie."""
    by_status: dict[str, list[dict]] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    print("\n" + "=" * 90, file=sys.stderr)
    print("VÉRIFICATION COMPLÉTUDE BRONZE vs UPSTREAM", file=sys.stderr)
    print("=" * 90, file=sys.stderr)

    icon = {
        "ok": "✅", "partial": "⚠️ ", "empty": "❌",
        "no_upstream": "ℹ️ ", "table_missing": "❌",
    }

    for status in ("ok", "partial", "empty", "no_upstream", "table_missing"):
        rows = by_status.get(status, [])
        if not rows:
            continue
        print(f"\n{icon[status]} {status.upper()} ({len(rows)}) :", file=sys.stderr)
        for r in rows:
            local = f"{r['local']:>15,}" if r['local'] is not None else " " * 15
            upstream = f"{r['upstream']:>15,}" if r['upstream'] is not None else " " * 15
            ratio = f"{r['ratio']*100:>6.1f}%" if r['ratio'] is not None else "  ----"
            print(f"   {r['source_id']:<35s} local={local} upstream={upstream}  ratio={ratio}",
                  file=sys.stderr)

    n_ok = len(by_status.get("ok", []))
    n_partial = len(by_status.get("partial", []))
    n_empty = len(by_status.get("empty", []))
    n_no_up = len(by_status.get("no_upstream", []))
    n_missing = len(by_status.get("table_missing", []))
    total = len(results)

    print("\n" + "-" * 90, file=sys.stderr)
    print(f"Total : {total}  |  ok={n_ok}  partial={n_partial}  "
          f"empty={n_empty}  no_upstream={n_no_up}  table_missing={n_missing}",
          file=sys.stderr)
    print("=" * 90 + "\n", file=sys.stderr)

    if n_partial > 0 or n_empty > 0 or n_missing > 0:
        return 1
    return 0


async def main() -> int:
    results = await verify_all()
    # JSON sur stdout (parsable par CI)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return _print_report(results)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

"""Détection auto du format d'une ressource data.

Cascade 4 signaux :
  1. `metadata_format` (venu de data.gouv resource.format) — priorité haute
  2. Extension URL
  3. Content-Type HTTP (HEAD)
  4. Magic bytes (Range GET 256 premiers bytes)

Retourne {format, signal, confidence, size_bytes?, content_type?}.
Format possibles : rest_json, csv, jsonl, zip, gzip, parquet, geojson, xml,
xlsx, shapefile, unknown.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

log = logging.getLogger("demoema.format_detect")

EXT_MAP = {
    ".csv": "csv", ".tsv": "csv",
    ".json": "rest_json", ".jsonl": "jsonl", ".ndjson": "jsonl",
    ".jsonl.gz": "jsonl", ".ndjson.gz": "jsonl",
    ".xml": "xml_single", ".rdf": "xml_single",
    ".xml.gz": "xml_single",
    ".zip": "zip",
    ".tar.gz": "tar_gz_xml", ".tgz": "tar_gz_xml", ".tar": "tar_xml",
    ".parquet": "parquet", ".pq": "parquet",
    ".shp": "shapefile", ".geojson": "geojson",
    ".xlsx": "xlsx", ".xls": "xls",
    ".csv.gz": "csv_gz",
}

CT_MAP = [
    ("application/json", "rest_json"),
    ("text/csv", "csv"),
    ("application/csv", "csv"),
    ("application/x-ndjson", "jsonl"),
    ("application/vnd.apache.parquet", "parquet"),
    ("application/parquet", "parquet"),
    ("application/zip", "zip"),
    ("application/x-zip", "zip"),
    ("application/geo+json", "geojson"),
    ("application/x-shapefile", "shapefile"),
    ("application/vnd.ms-excel", "xlsx"),
    ("application/vnd.openxmlformats", "xlsx"),
    ("application/xml", "xml"),
    ("text/xml", "xml"),
]

METADATA_NORMALIZE = {
    "csv": "csv", "tsv": "csv",
    "json": "rest_json",
    "jsonl": "jsonl", "ndjson": "jsonl",
    "zip": "zip",
    "tar.gz": "tar_gz_xml", "tgz": "tar_gz_xml", "tar": "tar_xml",
    "parquet": "parquet",
    "geojson": "geojson",
    "shp": "shapefile", "shapefile": "shapefile",
    "xml": "xml_single",
    "xlsx": "xlsx", "xls": "xls",
}


def _from_extension(url: str) -> Optional[str]:
    u = url.lower().split("?", 1)[0].split("#", 1)[0]
    # Check .csv.gz avant .gz seul
    for ext in sorted(EXT_MAP, key=len, reverse=True):
        if u.endswith(ext):
            return EXT_MAP[ext]
    return None


def _from_content_type(ct: str) -> Optional[str]:
    if not ct:
        return None
    low = ct.lower()
    for needle, fmt in CT_MAP:
        if needle in low:
            return fmt
    return None


def _from_magic(first_bytes: bytes) -> Optional[str]:
    if not first_bytes:
        return None
    if first_bytes.startswith(b"PK\x03\x04"):
        return "zip"
    if first_bytes.startswith(b"\x1f\x8b"):
        return "gzip"
    if first_bytes.startswith(b"PAR1") or first_bytes.endswith(b"PAR1"):
        return "parquet"
    try:
        text = first_bytes.decode("utf-8", errors="replace").lstrip()
    except Exception:
        return None
    if text.startswith("{") or text.startswith("["):
        # Distinguer JSON array vs JSONL
        if text.count("\n") > 1 and text[:300].count("{") > 3:
            return "jsonl"
        return "rest_json"
    if text.startswith("<?xml"):
        return "xml"
    if "," in text[:500] and "\n" in text[:500]:
        return "csv"
    if "\t" in text[:500] and "\n" in text[:500]:
        return "csv"  # TSV
    return None


async def detect_format(url: str, metadata_format: str = "") -> dict:
    """Detection en cascade. Retourne dict avec clés {format, signal, ...}."""
    result: dict = {"format": "unknown", "signal": "none"}

    # 1. Metadata (fourni par data.gouv)
    if metadata_format:
        norm = METADATA_NORMALIZE.get(metadata_format.lower().strip())
        if norm:
            return {"format": norm, "signal": "metadata",
                    "metadata_raw": metadata_format}

    # 2. Extension
    ext_fmt = _from_extension(url)
    if ext_fmt:
        return {"format": ext_fmt, "signal": "extension"}

    # 3. HEAD
    ct, size = "", None
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            rh = await c.head(url)
            ct = rh.headers.get("content-type", "")
            size = rh.headers.get("content-length")
    except Exception as e:
        log.info("HEAD %s failed: %s", url, e)

    ct_fmt = _from_content_type(ct)
    if ct_fmt:
        return {"format": ct_fmt, "signal": "content-type",
                "content_type": ct, "size_bytes": size}

    # 4. Magic bytes via Range GET
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.get(url, headers={"Range": "bytes=0-512"})
            magic_fmt = _from_magic(r.content)
            if magic_fmt:
                return {"format": magic_fmt, "signal": "magic_bytes",
                        "content_type": ct, "size_bytes": size}
    except Exception as e:
        log.info("Range GET %s failed: %s", url, e)

    return result


# ──────────── Tool schema pour DeepSeek ────────────

DETECT_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "detect_format",
            "description": (
                "Auto-detect the format of a data resource URL via cascade "
                "(metadata → extension → HTTP Content-Type → magic bytes). "
                "Returns {format: rest_json|csv|jsonl|zip|parquet|geojson|xml|..., signal, size_bytes}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "metadata_format": {"type": "string",
                                         "description": "Optional hint from data.gouv resource.format"},
                },
                "required": ["url"],
            },
        },
    },
]

DETECT_DISPATCH = {
    "detect_format": detect_format,
}

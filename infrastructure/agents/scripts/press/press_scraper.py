#!/usr/bin/env python3
"""Press scraper — aggregate RSS from French business press.

Feeds: Les Echos, La Tribune, Usine Nouvelle, cfnews (M&A specialist).

Usage: press_scraper.py
Env: DSN
"""
from __future__ import annotations
import hashlib, json, os, re, sys, time
import urllib.request
from datetime import datetime
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
import psycopg
from psycopg.types.json import Jsonb


FEEDS = [
    # Premier-tier working feeds
    ("bfmbusiness", "https://www.bfmtv.com/rss/economie/"),
    ("lopinion", "https://www.lopinion.fr/rss"),
    ("maddyness", "https://www.maddyness.com/feed/"),
    ("zonebourse", "https://www.zonebourse.com/rss/actualites-bourse.xml"),
    # Google News keyword searches — reliably free + geo-matched
    ("gn_acquisition", "https://news.google.com/rss/search?q=%22acquisition%22+entreprise+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_rachat", "https://news.google.com/rss/search?q=rachat+entreprise+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_cession", "https://news.google.com/rss/search?q=cession+entreprise+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_levee", "https://news.google.com/rss/search?q=%22lev%C3%A9e+de+fonds%22+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_fusion", "https://news.google.com/rss/search?q=fusion+entreprise+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_ipo", "https://news.google.com/rss/search?q=introduction+bourse+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_succession", "https://news.google.com/rss/search?q=succession+dirigeant+PME+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_procolbo", "https://news.google.com/rss/search?q=%22redressement+judiciaire%22+OR+%22liquidation%22+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_ceo_change", "https://news.google.com/rss/search?q=%22nouveau+directeur+g%C3%A9n%C3%A9ral%22+OR+%22nouveau+PDG%22+france&hl=fr&gl=FR&ceid=FR:fr"),
    # Keep the older-tier as attempts (may work intermittently)
    ("lesechos", "https://services.lesechos.fr/rss/les-echos-entreprises.xml"),
]


def _uid(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:40]


def _strip_tags(s: str | None) -> str | None:
    if not s:
        return None
    return re.sub(r"<[^>]+>", "", s).strip() or None


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return parsedate_to_datetime(s)
    except Exception:
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
        return None


def fetch_rss(url: str, timeout: int = 20) -> list[dict]:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 DEMOEMA-Press-Agg/0.1",
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except Exception as e:
        print(f"fetch {url}: {type(e).__name__}: {e}", file=sys.stderr)
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"parse {url}: {e}", file=sys.stderr)
        return []

    items = []
    # RSS 2.0: .//item ; Atom: .//{*}entry
    for item in root.iter():
        tag = item.tag.split("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        def _t(name):
            el = None
            for c in item:
                if c.tag.split("}", 1)[-1] == name:
                    el = c
                    break
            return _strip_tags(el.text) if (el is not None and el.text) else None
        link = _t("link")
        if not link:
            # Atom entries have <link href="..."/> attribute
            for c in item:
                if c.tag.split("}", 1)[-1] == "link" and c.attrib.get("href"):
                    link = c.attrib["href"]
                    break
        if not link:
            continue
        items.append({
            "url": link,
            "title": _t("title"),
            "summary": _t("description") or _t("summary"),
            "content": _t("content") or _t("encoded"),
            "pub_date": _t("pubDate") or _t("published") or _t("updated"),
        })
    return items


UPSERT_SQL = """
INSERT INTO bronze.press_articles_raw
  (article_uid, url, title, published_at, source, summary, content, payload, ingested_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (article_uid) DO UPDATE SET
  title = EXCLUDED.title,
  summary = EXCLUDED.summary,
  content = COALESCE(EXCLUDED.content, bronze.press_articles_raw.content),
  payload = EXCLUDED.payload
"""


def main():
    dsn = os.environ["DSN"]
    t0 = time.time()
    total_fetched = 0
    total_inserted = 0
    per_source: dict[str, int] = {}

    with psycopg.connect(dsn, autocommit=False) as conn, conn.cursor() as cur:
        for source, url in FEEDS:
            items = fetch_rss(url)
            per_source[source] = len(items)
            total_fetched += len(items)
            rows = []
            for it in items:
                rows.append((
                    _uid(it["url"]),
                    it["url"],
                    it["title"],
                    _parse_date(it["pub_date"]),
                    source,
                    it["summary"],
                    it["content"],
                    Jsonb({"rss_item": it, "feed_url": url,
                           "scanned_at": datetime.utcnow().isoformat()}),
                ))
            if rows:
                cur.executemany(UPSERT_SQL, rows)
                total_inserted += cur.rowcount or 0
            conn.commit()
            print(f"[{source}] {len(items)} items", file=sys.stderr, flush=True)

    print(json.dumps({
        "fetched": total_fetched,
        "inserted_or_updated": total_inserted,
        "per_source": per_source,
        "duration_s": round(time.time() - t0, 1),
    }))


if __name__ == "__main__":
    main()

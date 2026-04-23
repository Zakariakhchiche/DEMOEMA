"""Press articles aggregator — RSS from French business press + Google News keyword searches.

Target bronze table: bronze.press_articles_raw
Signal M&A: acquisition / rachat / cession / fusion / IPO / succession / CEO changes
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

FEEDS = [
    ("bfmbusiness", "https://www.bfmtv.com/rss/economie/"),
    ("maddyness", "https://www.maddyness.com/feed/"),
    # Google News keyword queries — reliably free + FR-matched
    ("gn_acquisition", "https://news.google.com/rss/search?q=%22acquisition%22+entreprise+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_rachat", "https://news.google.com/rss/search?q=rachat+entreprise+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_cession", "https://news.google.com/rss/search?q=cession+entreprise+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_levee", "https://news.google.com/rss/search?q=%22lev%C3%A9e+de+fonds%22+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_fusion", "https://news.google.com/rss/search?q=fusion+entreprise+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_ipo", "https://news.google.com/rss/search?q=introduction+bourse+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_succession", "https://news.google.com/rss/search?q=succession+dirigeant+PME+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_procolbo", "https://news.google.com/rss/search?q=%22redressement+judiciaire%22+OR+%22liquidation%22+france&hl=fr&gl=FR&ceid=FR:fr"),
    ("gn_ceo_change", "https://news.google.com/rss/search?q=%22nouveau+directeur+g%C3%A9n%C3%A9ral%22+OR+%22nouveau+PDG%22+france&hl=fr&gl=FR&ceid=FR:fr"),
]


def _uid(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:40]


def _strip(s):
    return re.sub(r"<[^>]+>", "", s).strip() if s else None


def _parse_date(s):
    if not s:
        return None
    try:
        return parsedate_to_datetime(s)
    except Exception:
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
    return None


def _fetch_rss(url: str, timeout: int = 20) -> list[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DEMOEMA-Press/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except Exception as e:
        log.warning("rss fetch %s: %s", url, e)
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    items = []
    for item in root.iter():
        tag = item.tag.split("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        def _t(name):
            for c in item:
                if c.tag.split("}", 1)[-1] == name and c.text:
                    return _strip(c.text)
            return None
        link = _t("link")
        if not link:
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


async def fetch_press_articles_delta() -> dict:
    """Scheduled fetcher: aggregate all RSS feeds + upsert into bronze.press_articles_raw."""
    if not settings.database_url:
        return {"source": "press_articles", "rows": 0, "error": "no DB"}

    t0 = time.time()
    total_fetched = 0
    total_inserted = 0
    per_source: dict[str, int] = {}

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            for source, url in FEEDS:
                items = _fetch_rss(url)
                per_source[source] = len(items)
                total_fetched += len(items)
                if not items:
                    continue
                rows = [
                    (
                        _uid(it["url"]),
                        it["url"],
                        it["title"],
                        _parse_date(it["pub_date"]),
                        source,
                        it["summary"],
                        it["content"],
                        Jsonb({"rss_item": it, "feed_url": url}),
                    )
                    for it in items
                ]
                await cur.executemany(UPSERT_SQL, rows)
                total_inserted += cur.rowcount or 0
                await conn.commit()

    return {
        "source": "press_articles",
        "rows": total_inserted,
        "fetched": total_fetched,
        "per_source": per_source,
        "duration_s": round(time.time() - t0, 1),
    }

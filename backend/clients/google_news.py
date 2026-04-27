"""Client Google News RSS — fetch + détection signaux de presse.

Extrait de main.py:411-455. Utilise defusedxml (audit SEC-3) pour parser
le flux RSS sans risque XXE/billion-laughs.
"""
from __future__ import annotations

import urllib.parse

import httpx
from defusedxml import ElementTree as ET

PRESS_SIGNAL_KEYWORDS: dict[str, list[str]] = {
    "presse_cession": ["cession", "cede", "cède", "vend", "reprise", "acquis", "acquisition", "rachat", "vendu"],
    "presse_difficultes": ["liquidation", "redressement", "difficulte", "difficultes", "perte", "faillite", "dépôt de bilan"],
    "presse_levee_fonds": ["levée de fonds", "leve", "lèvent", "investissement", "financement", "capital-risque"],
    "presse_partenariat": ["partenariat", "alliance", "accord", "joint-venture", "rapprochement"],
}


async def get_google_news(company_name: str, max_results: int = 6) -> list[dict]:
    """Fetch recent news from Google News RSS for a company name."""
    query = urllib.parse.quote(f'"{company_name}"')
    url = f"https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"
    try:
        async with httpx.AsyncClient(timeout=6, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; EdRCF/6.0)"
            })
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if not channel:
            return []
        articles: list[dict] = []
        for item in channel.findall("item")[:max_results]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub_date = item.findtext("pubDate") or ""
            source = item.findtext("source") or ""
            title_lower = title.lower()
            detected = [
                sig for sig, kws in PRESS_SIGNAL_KEYWORDS.items()
                if any(kw in title_lower for kw in kws)
            ]
            articles.append({
                "title": title,
                "link": link,
                "date": pub_date,
                "source": source,
                "signals": detected,
            })
        return articles
    except Exception as e:
        print(f"[GoogleNews] Error for '{company_name}': {e}")
        return []

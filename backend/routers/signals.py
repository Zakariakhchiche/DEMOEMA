"""Routes signaux M&A — extraite de main.py:1145-1172."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from demo_data import SIGNAL_CATALOG

router = APIRouter(tags=["signals"])


@router.get("/api/signals")
def get_signals(severity: Optional[str] = Query(None)):
    """Flux de signaux agrégés sur toutes les targets, filtrable par sévérité."""
    import main  # lazy import
    signals_feed = []
    for t in main.enriched_targets:
        for sig in t["topSignals"]:
            if severity and sig["severity"] != severity:
                continue
            signals_feed.append({
                "id": f"{t['id']}-{sig['id']}",
                "type": sig["family"],
                "title": f"{sig['label']} — {t['name']}",
                "time": "Recent",
                "source": sig["source"],
                "source_url": sig["source_url"],
                "severity": sig["severity"],
                "location": f"{t['city']}, {t['region']}",
                "tags": [sig["family"], t["sector"]],
                "target_id": t["id"],
                "target_name": t["name"],
                "dimension": sig["dimension"],
                "points": sig["points"],
            })
    order = {"high": 0, "medium": 1, "low": 2}
    signals_feed.sort(key=lambda s: order.get(s["severity"], 3))
    return {"data": signals_feed, "total": len(signals_feed), "catalog": SIGNAL_CATALOG}

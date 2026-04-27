"""Client Infogreffe open data — fetch des actes RCS par SIREN.

Extrait de main.py:462-509. Audit SEC-4 : siren passé dans la query
OpenDataSoft `where` est validé en amont par validate_siren côté router,
donc pas de risque d'injection.
"""
from __future__ import annotations

import httpx

INFOGREFFE_DATASETS: list[str] = [
    "actes-rcs-insee",
    "kbis-et-actes",
    "actes-et-bilans",
]
INFOGREFFE_BASE = "https://opendata.datainfogreffe.fr/api/explore/v2.1/catalog/datasets"


async def get_infogreffe_actes(siren: str, max_results: int = 10) -> list[dict]:
    """Fetch recent actes RCS from Infogreffe open data by SIREN.

    Tries multiple dataset names gracefully (3s per dataset, ~9s total worst case).
    Le `siren` doit déjà avoir été validé par `domain.validators.validate_siren`
    côté caller — pas d'échappement supplémentaire ici.
    """
    for dataset in INFOGREFFE_DATASETS:
        url = f"{INFOGREFFE_BASE}/{dataset}/records"
        params = {
            "where": f'siren="{siren}"',
            "limit": max_results,
            "order_by": "date_depot desc",
        }
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("results") or data.get("records") or []
                if records:
                    actes: list[dict] = []
                    for r in records:
                        fields = r.get("fields") or r
                        actes.append({
                            "type": (fields.get("libelle_type_acte")
                                     or fields.get("type_acte")
                                     or fields.get("nature")
                                     or "Acte"),
                            "date": (fields.get("date_depot")
                                     or fields.get("date")
                                     or ""),
                            "description": (fields.get("libelle")
                                            or fields.get("description")
                                            or ""),
                            "siren": siren,
                        })
                    return actes
        except Exception as e:
            print(f"[Infogreffe] Dataset {dataset} error for SIREN {siren}: {e}")
            continue
    return []

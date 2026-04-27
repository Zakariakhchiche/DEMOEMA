"""TargetsStore — encapsule l'état des cibles M&A en cours.

Avant : 4 globals mutables dans main.py (`enriched_targets`, `raw_targets`,
`_next_idx`, `_targets_lock`) avec 10 occurrences de `global ...` éparpillées
dans les routes (audit ARCH-2). Désormais : une seule classe avec lock
asyncio + interfaces propres.

La compat est assurée : main.py expose toujours `enriched_targets` et
`raw_targets` comme attributs module-level qui pointent vers les listes
internes du store (les tests `reset_globals` continuent de marcher).
"""
from __future__ import annotations

import asyncio
from typing import Any


class TargetsStore:
    """Store en mémoire des targets enrichies + raw, thread-safe via asyncio.Lock.

    Pattern : un seul store par process, instancié au lifespan de FastAPI.
    Les routes le récupèrent via `Depends(get_store)` ou via l'attribut
    `app.state.targets_store`.
    """

    def __init__(self) -> None:
        self._enriched: list[dict[str, Any]] = []
        self._raw: list[dict[str, Any]] = []
        self._next_idx: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()

    # ─── Accesseurs lecture (pas de lock — l'unicité d'écriture suffit pour
    # éviter la corruption ; les snapshots non-cohérents inter-routes sont
    # acceptables vu la fréquence faible des mutations) ─────────────────────

    @property
    def enriched(self) -> list[dict[str, Any]]:
        return self._enriched

    @property
    def raw(self) -> list[dict[str, Any]]:
        return self._raw

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    # ─── Mutations ─────────────────────────────────────────────────────

    async def replace_all(
        self,
        raw_targets: list[dict[str, Any]],
        enriched_targets: list[dict[str, Any]],
    ) -> None:
        """Remplace tout le contenu du store (utilisé par lifespan + refresh)."""
        async with self._lock:
            self._raw = list(raw_targets)
            self._enriched = list(enriched_targets)
            self._next_idx = max(
                (t.get("idx", 0) for t in self._enriched), default=0
            ) + 1

    async def append(
        self,
        raw_target: dict[str, Any],
        enriched_target: dict[str, Any],
    ) -> int:
        """Ajoute une nouvelle target. Retourne l'idx assigné."""
        async with self._lock:
            self._raw.append(raw_target)
            self._enriched.append(enriched_target)
            idx = self._next_idx
            self._next_idx += 1
            return idx

    async def replace_enriched(self, enriched_targets: list[dict[str, Any]]) -> None:
        """Re-scoring : remplace uniquement les targets enrichies, pas les raw."""
        async with self._lock:
            self._enriched = list(enriched_targets)

    @property
    def next_idx(self) -> int:
        return self._next_idx


# Singleton process-wide. Initialisé vide au boot ; le lifespan FastAPI le
# remplit. À terme, l'instance peut être attachée à app.state pour faciliter
# l'injection via Depends.
_store_singleton: TargetsStore | None = None


def get_store() -> TargetsStore:
    """Accesseur singleton — lazy init pour éviter les soucis d'event loop
    à l'import time."""
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = TargetsStore()
    return _store_singleton

"""Cache PARTAGÉ entre workers (Redis) avec fallback gracieux.

Pourquoi : le backend tourne en multi-worker (uvicorn --workers 8). Le cache
in-memory est par-process → une requête populaire doit être recalculée 8 fois.
Redis = cache partagé : calculée une fois, servie à tous les workers.

SÉCURITÉ / "ne rien casser" :
  - C'est un CACHE, pas une base. Aucune persistance (--save ""), perte = 0 donnée
    (l'app retombe sur Postgres).
  - TOUTE erreur Redis (indispo, timeout, sérialisation) → fallback silencieux
    (on retourne None côté get, no-op côté set) + cooldown 30s pour ne PAS
    pénaliser la latence quand Redis est down. L'app fonctionne exactement comme
    avant (cache in-memory) si Redis disparaît.

Client redis-py synchrone : opérations locales <1ms, négligeable vs une requête
DB de 0,5-10s évitée.
"""
from __future__ import annotations

import json
import os
import time

_REDIS_URL = os.environ.get("REDIS_URL", "")
_client = None
_cooldown_until = 0.0  # epoch : pas de tentative Redis avant cette date (après échec)


def _client_or_none():
    global _client, _cooldown_until
    if not _REDIS_URL:
        return None
    if time.time() < _cooldown_until:
        return None
    if _client is None:
        try:
            import redis  # redis-py
            _client = redis.Redis.from_url(
                _REDIS_URL,
                socket_connect_timeout=0.3,
                socket_timeout=0.3,
                retry_on_timeout=False,
            )
            _client.ping()
        except Exception:
            _client = None
            _cooldown_until = time.time() + 30.0
            return None
    return _client


def _trip(exc_cooldown: float = 30.0):
    """Coupe le client + cooldown après une erreur (évite la pénalité latence)."""
    global _client, _cooldown_until
    _client = None
    _cooldown_until = time.time() + exc_cooldown


def cache_get(key: str):
    c = _client_or_none()
    if c is None:
        return None
    try:
        v = c.get(key)
        return json.loads(v) if v is not None else None
    except Exception:
        _trip()
        return None


def cache_set(key: str, payload, ttl_s: float) -> None:
    c = _client_or_none()
    if c is None:
        return
    try:
        c.set(key, json.dumps(payload, default=str), ex=max(1, int(ttl_s)))
    except Exception:
        _trip()


def is_available() -> bool:
    return _client_or_none() is not None

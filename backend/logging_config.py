"""Structured JSON logging + Prometheus metrics.

Promtail parses JSON fields → Loki labels (level, logger).
Prometheus scrapes /metrics exposed by prometheus-fastapi-instrumentator.
"""
from __future__ import annotations

import logging
import os
import sys

from pythonjsonlogger import jsonlogger


def configure_logging() -> None:
    """Replace uvicorn/fastapi/root loggers with JSON structured output."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(module)s %(funcName)s %(lineno)d",
        datefmt="%Y-%m-%d %H:%M:%S,%03d",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.propagate = False
        lg.setLevel(log_level)


def install_prometheus_metrics(app) -> None:
    """Mount /metrics endpoint + instrument all routes (latency, status codes)."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=False,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/healthz", "/docs", "/openapi.json"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    except Exception as e:
        logging.getLogger(__name__).warning("Prometheus instrumentation skipped: %s", e)

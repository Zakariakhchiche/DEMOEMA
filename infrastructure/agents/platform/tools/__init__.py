"""Tool registry — mapping name → callable + JSON schema."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .docs import read_docs, search_codebase
from .postgres import postgres_query_ro
from .atlassian import atlassian_api
from .slack import slack_notify
from .http import httpx_get, test_endpoint

ToolFunc = Callable[..., Any]


REGISTRY: dict[str, dict[str, Any]] = {
    "read_docs": {
        "func": read_docs,
        "schema": {
            "type": "function",
            "function": {
                "name": "read_docs",
                "description": "Lit un fichier markdown du dossier docs/ du projet DEMOEMA. Retourne le contenu complet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Nom du fichier ex : 'ARCHITECTURE_DATA_V2.md' ou 'ETAT_REEL_2026-04-20.md'",
                        }
                    },
                    "required": ["filename"],
                },
            },
        },
    },
    "search_codebase": {
        "func": search_codebase,
        "schema": {
            "type": "function",
            "function": {
                "name": "search_codebase",
                "description": "Recherche regex dans le repo DEMOEMA (docs + infrastructure). Retourne jusqu'à 50 lignes matchantes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Pattern regex"},
                        "glob": {"type": "string", "description": "Glob filter optionnel ex '*.md' ou '*.yml'", "default": ""},
                    },
                    "required": ["pattern"],
                },
            },
        },
    },
    "postgres_query_ro": {
        "func": postgres_query_ro,
        "schema": {
            "type": "function",
            "function": {
                "name": "postgres_query_ro",
                "description": "Exécute une requête SELECT read-only sur Postgres DEMOEMA. Rôle demoema_ro, max 1000 lignes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SELECT uniquement. Pas de INSERT/UPDATE/DELETE/ALTER"},
                    },
                    "required": ["sql"],
                },
            },
        },
    },
    "httpx_get": {
        "func": httpx_get,
        "schema": {
            "type": "function",
            "function": {
                "name": "httpx_get",
                "description": "HTTP GET vers une URL publique. Timeout 30s.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                    },
                    "required": ["url"],
                },
            },
        },
    },
    "test_endpoint": {
        "func": test_endpoint,
        "schema": {
            "type": "function",
            "function": {
                "name": "test_endpoint",
                "description": "VALIDE un endpoint API avant d'écrire le fetcher. Retourne works/status/content_type/sample_record_keys. **APPELLE CE TOOL AVANT DE GÉNÉRER DU CODE** pour vérifier que l'URL existe et connaître le format de réponse.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL complète à tester"},
                        "method": {"type": "string", "enum": ["GET", "HEAD", "POST"], "default": "GET"},
                        "params": {"type": "object", "description": "Query params optionnels", "default": {}},
                    },
                    "required": ["url"],
                },
            },
        },
    },
    "atlassian_api": {
        "func": atlassian_api,
        "schema": {
            "type": "function",
            "function": {
                "name": "atlassian_api",
                "description": "Appel API Confluence/Jira (auth via ATLASSIAN_API_TOKEN).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                        "path": {"type": "string", "description": "Ex '/rest/api/3/issue/SCRUM-66'"},
                        "body": {"type": "object", "description": "Body JSON pour POST/PUT", "default": {}},
                    },
                    "required": ["method", "path"],
                },
            },
        },
    },
    "slack_notify": {
        "func": slack_notify,
        "schema": {
            "type": "function",
            "function": {
                "name": "slack_notify",
                "description": "Envoie un message Slack via webhook (niveau info/warning/critical).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "enum": ["info", "warning", "critical"]},
                        "message": {"type": "string"},
                    },
                    "required": ["level", "message"],
                },
            },
        },
    },
}


def get_tool_schemas(tool_names: list[str]) -> list[dict]:
    return [REGISTRY[n]["schema"] for n in tool_names if n in REGISTRY]


async def execute_tool(name: str, arguments: dict) -> dict:
    if name not in REGISTRY:
        return {"error": f"tool inconnu : {name}"}
    func = REGISTRY[name]["func"]
    try:
        result = await func(**arguments)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

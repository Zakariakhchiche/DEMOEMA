"""Browser tools pour l'agent openclaw.

Un seul navigateur headless Chromium partagé par run d'agent.
Session persistante en mémoire (storage_state par source_id → cookies gardés
entre tool calls d'un même run).

Tool contract : toutes les fonctions async, input JSON serializable, output str.
Le LLM (DeepSeek) voit le résultat de chaque tool dans l'observation suivante.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger("demoema.browser")

# Lazy import — playwright est lourd, seulement quand l'agent est invoqué
_browser = None
_context = None
_page = None

SCREENSHOT_DIR = Path("/tmp/openclaw_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

MAX_TEXT_OBS = 4000  # tronquer les textes renvoyés au LLM


async def _ensure_browser():
    """Initialise Chromium headless avec patches stealth (bypass bot-detection simple).
    Masque navigator.webdriver, WebGL vendor, plugins fake, etc."""
    global _browser, _context, _page
    if _page is not None:
        return
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    _browser = await pw.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
        ],
    )
    _context = await _browser.new_context(
        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
        viewport={"width": 1280, "height": 800},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        extra_http_headers={
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Linux"',
        },
    )
    _page = await _context.new_page()

    # Stealth patches manuels (survit si tf-playwright-stealth indispo)
    await _page.add_init_script("""
        // Masquer navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

        // Plugins fake list
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                {name: 'Native Client', filename: 'internal-nacl-plugin'},
            ],
        });

        // Languages
        Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR', 'fr', 'en']});

        // chrome.runtime existant
        window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}};

        // Permissions query (Notification)
        const origQuery = window.navigator.permissions && window.navigator.permissions.query;
        if (origQuery) {
            window.navigator.permissions.query = (params) => (
                params.name === 'notifications'
                    ? Promise.resolve({state: Notification.permission})
                    : origQuery(params)
            );
        }

        // WebGL vendor spoofing
        try {
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(p) {
                if (p === 37445) return 'Intel Inc.';
                if (p === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.apply(this, arguments);
            };
        } catch(e){}
    """)

    # tf-playwright-stealth fait aussi le travail si dispo (complémentaire)
    try:
        from playwright_stealth import stealth_async
        await stealth_async(_page)
        log.info("tf-playwright-stealth appliqué sur la page")
    except ImportError:
        log.debug("tf-playwright-stealth non installé — patches manuels seulement")
    except Exception as e:
        log.warning("stealth_async failed: %s", e)


async def close_browser() -> None:
    global _browser, _context, _page
    try:
        if _context: await _context.close()
        if _browser: await _browser.close()
    except Exception:
        pass
    _browser = _context = _page = None


# ──────────────── TOOLS EXPOSÉS AU LLM ────────────────

async def navigate(url: str, wait_until: str = "networkidle") -> str:
    """Charge une URL. Retourne le titre + URL finale + premiers chars du body."""
    await _ensure_browser()
    try:
        r = await _page.goto(url, wait_until=wait_until, timeout=30_000)
        title = await _page.title()
        final_url = _page.url
        body_text = await _page.evaluate("() => document.body ? document.body.innerText.slice(0, 800) : ''")
        return (f"OK status={r.status if r else '?'} title={title!r} "
                f"url={final_url!r}\n--- body preview ---\n{body_text}")
    except Exception as e:
        return f"ERR navigate: {type(e).__name__}: {e}"


async def click(selector: str) -> str:
    """Clique sur un élément (CSS selector). Attend la fin du network."""
    await _ensure_browser()
    try:
        await _page.click(selector, timeout=10_000)
        await _page.wait_for_load_state("networkidle", timeout=10_000)
        return f"OK clicked {selector} — now at {_page.url}"
    except Exception as e:
        return f"ERR click {selector}: {type(e).__name__}: {e}"


async def fill(selector: str, value: str, submit: bool = False) -> str:
    """Remplit un champ input/textarea. Si submit=true, appuie Enter ensuite."""
    await _ensure_browser()
    try:
        await _page.fill(selector, value, timeout=10_000)
        if submit:
            await _page.press(selector, "Enter")
            await _page.wait_for_load_state("networkidle", timeout=10_000)
        return f"OK filled {selector}" + (" + submitted" if submit else "")
    except Exception as e:
        return f"ERR fill {selector}: {type(e).__name__}: {e}"


async def get_text(selector: str = "body") -> str:
    """Retourne le texte visible d'un élément (tronqué à 4000 chars)."""
    await _ensure_browser()
    try:
        text = await _page.locator(selector).first.inner_text(timeout=5_000)
        if len(text) > MAX_TEXT_OBS:
            text = text[:MAX_TEXT_OBS] + f"\n... [truncated, total {len(text)} chars]"
        return text
    except Exception as e:
        return f"ERR get_text {selector}: {type(e).__name__}: {e}"


async def screenshot(filename: str | None = None) -> str:
    """Capture d'écran PNG. Retourne le chemin sur disque (pas l'image elle-même
    car DeepSeek text-only). À consulter hors-agent."""
    await _ensure_browser()
    try:
        name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename or "shot")
        if not name.endswith(".png"):
            name = name + ".png"
        path = SCREENSHOT_DIR / name
        await _page.screenshot(path=str(path), full_page=True)
        return f"OK screenshot saved {path}"
    except Exception as e:
        return f"ERR screenshot: {type(e).__name__}: {e}"


async def find_inputs() -> str:
    """Liste tous les inputs/selects visibles avec leur name/id/label.
    Utile pour que le LLM découvre les selectors à utiliser."""
    await _ensure_browser()
    try:
        elements = await _page.evaluate("""
            () => {
                const out = [];
                document.querySelectorAll('input, select, textarea, button').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return;
                    out.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || '',
                        name: el.name || '',
                        id: el.id || '',
                        placeholder: el.placeholder || '',
                        value: (el.value || '').slice(0, 40),
                        label: el.labels && el.labels[0] ? el.labels[0].innerText.slice(0, 60) : '',
                        text: (el.innerText || '').slice(0, 60),
                    });
                });
                return out;
            }
        """)
        if not elements:
            return "(aucun input visible)"
        lines = []
        for e in elements[:40]:
            lines.append(
                f"<{e['tag']} type={e['type']!r} name={e['name']!r} id={e['id']!r} "
                f"placeholder={e['placeholder']!r} label={e['label']!r} text={e['text']!r}>"
            )
        return "\n".join(lines) + (f"\n... ({len(elements)-40} more)" if len(elements) > 40 else "")
    except Exception as e:
        return f"ERR find_inputs: {type(e).__name__}: {e}"


async def eval_js(script: str) -> str:
    """Exécute du JS dans la page. RESTREINT à du read-only : scripts exec plus
    longs que 500 chars refusés, pas d'appel à fetch(). Retour = repr du résultat."""
    await _ensure_browser()
    if len(script) > 500:
        return "ERR eval_js: script > 500 chars refusé"
    if "fetch(" in script or "XMLHttpRequest" in script or "import(" in script:
        return "ERR eval_js: fetch/XHR/dynamic import interdits"
    try:
        result = await _page.evaluate(script)
        s = repr(result)
        if len(s) > MAX_TEXT_OBS:
            s = s[:MAX_TEXT_OBS] + "...[truncated]"
        return f"OK {s}"
    except Exception as e:
        return f"ERR eval_js: {type(e).__name__}: {e}"


# ──────────────── TOOLS REGISTRY POUR LLM ────────────────

TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Load a URL in the headless browser. Returns page title + URL + first 800 chars of body text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to load"},
                    "wait_until": {"type": "string", "enum": ["load", "domcontentloaded", "networkidle"], "default": "networkidle"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click an element by CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {"selector": {"type": "string"}},
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fill",
            "description": "Fill an input/textarea. Set submit=true to press Enter after.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "value": {"type": "string"},
                    "submit": {"type": "boolean", "default": False},
                },
                "required": ["selector", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_text",
            "description": "Get visible text of an element. Default selector=body.",
            "parameters": {
                "type": "object",
                "properties": {"selector": {"type": "string", "default": "body"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_inputs",
            "description": "List all visible inputs/buttons with their selectors. Use this to discover what to fill.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Save a screenshot PNG to /tmp/openclaw_screenshots/. Returns the path for user to review.",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eval_js",
            "description": "Run small read-only JS (no fetch/XHR) and return the result. Max 500 chars.",
            "parameters": {
                "type": "object",
                "properties": {"script": {"type": "string"}},
                "required": ["script"],
            },
        },
    },
]

TOOLS_DISPATCH = {
    "navigate": navigate,
    "click": click,
    "fill": fill,
    "get_text": get_text,
    "find_inputs": find_inputs,
    "screenshot": screenshot,
    "eval_js": eval_js,
}


async def dispatch(tool_name: str, args: dict) -> str:
    fn = TOOLS_DISPATCH.get(tool_name)
    if fn is None:
        return f"ERR unknown tool: {tool_name}"
    try:
        return await fn(**args)
    except TypeError as e:
        return f"ERR bad args for {tool_name}: {e}"
    except Exception as e:
        log.exception("tool %s crashed", tool_name)
        return f"ERR {tool_name}: {type(e).__name__}: {e}"

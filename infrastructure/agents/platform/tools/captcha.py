"""Client 2captcha.com — résolution de CAPTCHAs via API tierce.

Flow : createTask → poll getTaskResult (5-30s) → return token → inject dans page.
Types supportés : reCAPTCHA v2, reCAPTCHA v3, hCaptcha, Turnstile Cloudflare, image OCR.

Coût typique (2026) : ~$0.003 par captcha résolu.

Env var requise : TWOCAPTCHA_API_KEY
Docs API : https://2captcha.com/2captcha-api
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Optional

import httpx

log = logging.getLogger("demoema.captcha")

API_BASE = "https://api.2captcha.com"
POLL_INTERVAL = 5
MAX_POLL_ATTEMPTS = 30  # 30 × 5s = 2.5 min max par captcha


def _api_key() -> str:
    k = os.environ.get("TWOCAPTCHA_API_KEY", "").strip()
    if not k:
        raise ValueError("TWOCAPTCHA_API_KEY manquante dans .env")
    return k


async def _create_task(task_payload: dict) -> Optional[int]:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{API_BASE}/createTask", json={
            "clientKey": _api_key(),
            "task": task_payload,
        })
        r.raise_for_status()
        data = r.json()
    if data.get("errorId", 1) != 0:
        raise RuntimeError(f"2captcha createTask error: {data.get('errorDescription')}")
    return data.get("taskId")


async def _poll_result(task_id: int) -> dict:
    for i in range(MAX_POLL_ATTEMPTS):
        await asyncio.sleep(POLL_INTERVAL if i else 3)
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{API_BASE}/getTaskResult", json={
                "clientKey": _api_key(),
                "taskId": task_id,
            })
            r.raise_for_status()
            data = r.json()
        if data.get("errorId", 1) != 0:
            raise RuntimeError(f"2captcha pollError: {data.get('errorDescription')}")
        if data.get("status") == "ready":
            return data.get("solution") or {}
    raise TimeoutError("2captcha timeout après 2.5 min")


# ──────────── Tools exposés à openclaw ────────────

async def detect_captcha() -> str:
    """Détecte la présence d'un CAPTCHA dans la page ouverte. Retourne son type + site_key.
    Nécessite un browser déjà sur une page (après navigate)."""
    try:
        from tools import browser
        await browser._ensure_browser()
        info = await browser._page.evaluate("""
            () => {
                // reCAPTCHA v2
                const rc2 = document.querySelector('.g-recaptcha, [data-sitekey]');
                if (rc2) {
                    const sk = rc2.getAttribute('data-sitekey');
                    if (sk) return {type: 'recaptcha_v2', sitekey: sk, url: location.href};
                }
                // reCAPTCHA iframe (même sans .g-recaptcha)
                const ifr = document.querySelector('iframe[src*="recaptcha/api2"]');
                if (ifr) {
                    const m = ifr.src.match(/[?&]k=([^&]+)/);
                    if (m) return {type: 'recaptcha_v2', sitekey: m[1], url: location.href};
                }
                // hCaptcha
                const hc = document.querySelector('[data-hcaptcha-sitekey], .h-captcha');
                if (hc) {
                    const sk = hc.getAttribute('data-hcaptcha-sitekey') || hc.getAttribute('data-sitekey');
                    if (sk) return {type: 'hcaptcha', sitekey: sk, url: location.href};
                }
                // Cloudflare Turnstile
                const ts = document.querySelector('.cf-turnstile, [data-sitekey][data-callback]');
                if (ts) {
                    const sk = ts.getAttribute('data-sitekey');
                    if (sk) return {type: 'turnstile', sitekey: sk, url: location.href};
                }
                return null;
            }
        """)
        if info:
            return (f"OK detected {info['type']} sitekey={info['sitekey']!r} "
                    f"url={info['url']!r}")
        return "NONE (pas de captcha détecté dans la page)"
    except Exception as e:
        return f"ERR detect_captcha: {type(e).__name__}: {e}"


async def solve_captcha(captcha_type: str, sitekey: str, page_url: str) -> str:
    """Résout un CAPTCHA via 2captcha (tous types sauf image).
    Retourne le token à injecter dans la page via inject_captcha_token.

    captcha_type : recaptcha_v2 | recaptcha_v3 | hcaptcha | turnstile
    """
    try:
        if captcha_type == "recaptcha_v2":
            task = {"type": "RecaptchaV2TaskProxyless",
                    "websiteURL": page_url, "websiteKey": sitekey}
        elif captcha_type == "recaptcha_v3":
            task = {"type": "RecaptchaV3TaskProxyless",
                    "websiteURL": page_url, "websiteKey": sitekey,
                    "minScore": 0.7, "pageAction": "verify"}
        elif captcha_type == "hcaptcha":
            task = {"type": "HCaptchaTaskProxyless",
                    "websiteURL": page_url, "websiteKey": sitekey}
        elif captcha_type == "turnstile":
            task = {"type": "TurnstileTaskProxyless",
                    "websiteURL": page_url, "websiteKey": sitekey}
        else:
            return f"ERR type inconnu: {captcha_type!r}"

        task_id = await _create_task(task)
        log.info("[captcha] task %s %s sitekey=%s", task_id, captcha_type, sitekey[:12])
        solution = await _poll_result(task_id)

        # Token key dépend du type
        token_key_map = {
            "recaptcha_v2": "gRecaptchaResponse",
            "recaptcha_v3": "gRecaptchaResponse",
            "hcaptcha":     "gRecaptchaResponse",
            "turnstile":    "token",
        }
        token = solution.get(token_key_map[captcha_type]) or solution.get("token")
        if not token:
            return f"ERR no token in solution: {solution}"
        return f"OK token={token}"
    except Exception as e:
        return f"ERR solve_captcha: {type(e).__name__}: {e}"


async def inject_captcha_token(captcha_type: str, token: str) -> str:
    """Inject le token reçu dans le form de la page courante.
    À appeler après solve_captcha. Ensuite submit le form (click sur bouton).
    """
    try:
        from tools import browser
        await browser._ensure_browser()
        if captcha_type in ("recaptcha_v2", "recaptcha_v3", "hcaptcha"):
            script = """
                (tok) => {
                    const ta = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (ta) { ta.value = tok; ta.innerHTML = tok; ta.style.display = ''; }
                    const hc = document.querySelector('textarea[name="h-captcha-response"]');
                    if (hc) { hc.value = tok; hc.innerHTML = tok; }
                    // Trigger callback si défini
                    if (window.___grecaptcha_cfg && window.___grecaptcha_cfg.clients) {
                        try {
                            const keys = Object.keys(window.___grecaptcha_cfg.clients);
                            for (const k of keys) {
                                const c = window.___grecaptcha_cfg.clients[k];
                                Object.values(c).forEach(v => {
                                    if (v && typeof v === 'object') {
                                        Object.values(v).forEach(w => {
                                            if (w && w.callback && typeof w.callback === 'function') {
                                                try { w.callback(tok); } catch (e) {}
                                            }
                                        });
                                    }
                                });
                            }
                        } catch (e) {}
                    }
                    return true;
                }
            """
        elif captcha_type == "turnstile":
            script = """
                (tok) => {
                    const inp = document.querySelector('input[name="cf-turnstile-response"]');
                    if (inp) { inp.value = tok; return true; }
                    return false;
                }
            """
        else:
            return f"ERR type inconnu: {captcha_type!r}"
        ok = await browser._page.evaluate(script, token)
        return f"OK injected {captcha_type}" if ok else f"WARN injected but no target field found"
    except Exception as e:
        return f"ERR inject_captcha_token: {type(e).__name__}: {e}"


async def captcha_balance() -> str:
    """Check le solde du compte 2captcha (pour debug coûts)."""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{API_BASE}/getBalance", json={"clientKey": _api_key()})
            r.raise_for_status()
            data = r.json()
        if data.get("errorId", 1) != 0:
            return f"ERR {data.get('errorDescription')}"
        return f"OK balance=${data.get('balance', '?')} USD"
    except Exception as e:
        return f"ERR captcha_balance: {type(e).__name__}: {e}"


# ──────────── Tool schemas ────────────

CAPTCHA_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "detect_captcha",
            "description": "Detect if current page has a CAPTCHA (reCAPTCHA v2/v3, hCaptcha, Turnstile). Call after navigate. Returns type + sitekey + url.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "solve_captcha",
            "description": "Solve a CAPTCHA via 2captcha API (costs ~$0.003). Returns a token to inject. Takes 5-30 seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "captcha_type": {"type": "string", "enum": ["recaptcha_v2", "recaptcha_v3", "hcaptcha", "turnstile"]},
                    "sitekey": {"type": "string"},
                    "page_url": {"type": "string"},
                },
                "required": ["captcha_type", "sitekey", "page_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inject_captcha_token",
            "description": "Inject the solved CAPTCHA token into the current page's form. Call after solve_captcha. Then click the submit button.",
            "parameters": {
                "type": "object",
                "properties": {
                    "captcha_type": {"type": "string"},
                    "token": {"type": "string"},
                },
                "required": ["captcha_type", "token"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "captcha_balance",
            "description": "Check remaining balance on 2captcha account (USD).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

CAPTCHA_DISPATCH = {
    "detect_captcha": detect_captcha,
    "solve_captcha": solve_captcha,
    "inject_captcha_token": inject_captcha_token,
    "captcha_balance": captcha_balance,
}

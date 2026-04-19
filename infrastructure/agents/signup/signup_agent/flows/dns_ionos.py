"""Flow manuel-action : ajouter DNS record via panel IONOS (exemple de scope élargi).

Automatise : login IONOS → navigate DNS zone → add record → save.
Permet à l'agent de créer DNS entries (agents.demoema.fr, mail.demoema.fr MX, etc.)
sans intervention manuelle.

⚠️ IONOS peut avoir 2FA — le flow STOPPE et escalade si détecté.
"""
from __future__ import annotations

import logging
from pathlib import Path

from playwright.async_api import async_playwright

log = logging.getLogger("flows.dns_ionos")

IONOS_LOGIN = "https://my.ionos.fr/account/login"


async def run(profile, audit_dir: Path, write_credential, record_params: dict | None = None) -> dict:
    """Ajoute un DNS record sur IONOS panel.

    record_params = {
        'domain': 'demoema.fr',
        'type': 'A' | 'MX' | 'TXT' | 'CNAME',
        'name': 'agents' (subdomain or @),
        'value': '82.165.242.205',
        'priority': 10,  # pour MX
        'ttl': 3600
    }
    """
    if not record_params:
        return {"status": "error", "reason": "record_params required"}

    ionos_user = profile.__fields_set__.get("ionos_email", "")  # custom field
    ionos_password = ""  # chargé depuis env — jamais dans profile.yaml

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(locale="fr-FR")
        page = await context.new_page()

        await page.goto(IONOS_LOGIN, wait_until="networkidle")
        await page.screenshot(path=str(audit_dir / "01_login_page.png"))

        # IONOS auth is a classic form ; may trigger 2FA (SMS / TOTP)
        try:
            await page.fill('input[name="username"], input[type="email"]', ionos_user)
            await page.fill('input[name="password"], input[type="password"]', ionos_password)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.screenshot(path=str(audit_dir / "02_post_login.png"))
        except Exception as e:
            await browser.close()
            return {"status": "login_form_error", "error": str(e)}

        # Detect 2FA
        if await page.locator('text=/Vérification.*2FA|2-step|SMS/i').count():
            await page.screenshot(path=str(audit_dir / "99_2FA_REQUIRED.png"))
            await browser.close()
            return {
                "status": "2fa_pending",
                "action_required": "founder_provide_2fa_code",
                "audit_dir": str(audit_dir),
            }

        # Navigate DNS zone for domain
        # ⚠️ UI IONOS change souvent, sélecteurs à confirmer par screenshot
        await page.goto(f"https://my.ionos.fr/domains/{record_params['domain']}/dns", wait_until="networkidle")
        await page.screenshot(path=str(audit_dir / "03_dns_zone.png"))

        # Click "Ajouter un enregistrement" ou équivalent
        add_btn = page.locator('button:has-text("Ajouter"), button:has-text("Add record")')
        if await add_btn.count() == 0:
            await browser.close()
            return {"status": "add_button_not_found", "audit_dir": str(audit_dir)}
        await add_btn.first.click()
        await page.screenshot(path=str(audit_dir / "04_add_form.png"))

        # Fill DNS form
        await page.select_option('select[name="type"]', value=record_params['type'])
        await page.fill('input[name="name"]', record_params['name'])
        await page.fill('input[name="value"]', record_params['value'])
        if record_params.get('priority'):
            await page.fill('input[name="priority"]', str(record_params['priority']))
        if record_params.get('ttl'):
            await page.fill('input[name="ttl"]', str(record_params['ttl']))

        await page.screenshot(path=str(audit_dir / "05_form_filled.png"))

        # Submit
        await page.click('button:has-text("Enregistrer"), button:has-text("Save")')
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=str(audit_dir / "06_saved.png"))

        await browser.close()
        return {
            "status": "dns_record_added",
            "record": record_params,
            "audit_dir": str(audit_dir),
        }

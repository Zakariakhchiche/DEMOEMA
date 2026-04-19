"""Flow signup INPI RNE — registre-national-entreprises.inpi.fr.

Signup gratuit, donne accès API RNE (registre national des entreprises) :
- Données entreprise consolidées (SIREN, dénomination, forme juridique, dirigeants)
- Actes + comptes annuels déposés

⚠️ UI INPI change régulièrement, sélecteurs à vérifier.
"""
from __future__ import annotations

import asyncio
import logging
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from imap_tools import MailBox, AND
from playwright.async_api import async_playwright

log = logging.getLogger("flows.inpi_rne")

SIGNUP_URL = "https://data.inpi.fr/register"
LOGIN_URL = "https://data.inpi.fr/login"


async def run(profile, audit_dir: Path, write_credential) -> dict:
    password = secrets.token_urlsafe(24)
    (audit_dir / "password.txt").write_text(password, encoding="utf-8")
    (audit_dir / "password.txt").chmod(0o600)

    start_time = datetime.now(tz=timezone.utc)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="fr-FR",
        )
        page = await context.new_page()

        await page.goto(SIGNUP_URL, wait_until="networkidle")
        await page.screenshot(path=str(audit_dir / "01_signup_page.png"))

        has_captcha = any(
            "recaptcha" in (f.url or "") or "hcaptcha" in (f.url or "") or "turnstile" in (f.url or "")
            for f in page.frames
        )
        if has_captcha:
            await page.screenshot(path=str(audit_dir / "99_CAPTCHA_DETECTED.png"))
            await browser.close()
            return {
                "status": "captcha_detected",
                "action_required": "founder_complete_manually",
                "audit_dir": str(audit_dir),
            }

        try:
            await page.fill('input[name="email"], input[type="email"]', profile.project_email)
            await page.fill('input[name="password"], input[type="password"]', password)
            for sel in ['input[name="firstName"]', 'input[name="prenom"]', 'input[name="firstname"]']:
                if await page.locator(sel).count():
                    await page.fill(sel, profile.contact_first_name)
                    break
            for sel in ['input[name="lastName"]', 'input[name="nom"]', 'input[name="lastname"]']:
                if await page.locator(sel).count():
                    await page.fill(sel, profile.contact_last_name)
                    break
            for sel in ['input[name="organization"]', 'input[name="company"]', 'input[name="societe"]']:
                if await page.locator(sel).count():
                    await page.fill(sel, profile.company_name)
                    break
            await page.screenshot(path=str(audit_dir / "02_form_filled.png"))
        except Exception as e:
            await page.screenshot(path=str(audit_dir / "99_form_fill_error.png"))
            await browser.close()
            return {"status": "form_fill_error", "error": str(e), "audit_dir": str(audit_dir)}

        if await page.locator('input[type="checkbox"]').count() > 0:
            await page.screenshot(path=str(audit_dir / "99_CGU_REQUIRED.png"))
            await browser.close()
            return {
                "status": "cgu_pending",
                "action_required": "founder_accepts_cgu",
                "audit_dir": str(audit_dir),
            }

        submit = page.locator('button[type="submit"], button:has-text("Créer"), button:has-text("S\'inscrire")')
        if not await submit.count():
            await browser.close()
            return {"status": "submit_button_not_found", "audit_dir": str(audit_dir)}
        await submit.first.click()
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.screenshot(path=str(audit_dir / "03_submit_result.png"))

        await asyncio.sleep(15)
        verif_link = None
        try:
            with MailBox(profile.project_email_imap_host, port=profile.project_email_imap_port).login(
                profile.project_email_user, profile.project_email_password, initial_folder="INBOX"
            ) as mailbox:
                for msg in mailbox.fetch(
                    AND(from_="inpi.fr", date_gte=start_time.date()),
                    reverse=True,
                    limit=5,
                ):
                    urls = re.findall(r"https?://[^\s\"'<>]+", msg.text or msg.html or "")
                    for u in urls:
                        if "inpi.fr" in u and ("verify" in u or "confirm" in u or "activate" in u):
                            verif_link = u
                            break
                    if verif_link:
                        break
        except Exception as e:
            log.warning("IMAP lookup échoué : %s", e)

        if not verif_link:
            await browser.close()
            return {
                "status": "email_verification_pending",
                "action_required": "founder_click_verif_email",
                "audit_dir": str(audit_dir),
            }

        await page.goto(verif_link, wait_until="networkidle")
        await page.screenshot(path=str(audit_dir / "04_email_verified.png"))

        await browser.close()
        return {
            "status": "account_created_pending_app_creation",
            "action_required": "founder_finish_app_creation",
            "audit_dir": str(audit_dir),
            "next_steps": [
                "1. Login sur https://data.inpi.fr (audit/password.txt)",
                "2. Récupérer token API (souvent dispo directement une fois connecté)",
                "3. Ajouter au VPS : INPI_USERNAME=... / INPI_PASSWORD=...",
            ],
        }

"""Flow signup INSEE SIRENE V3 — api.insee.fr

Source #2 ARCHITECTURE_DATA_V2. Gratuit, 30 req/min en standard.
Portail : https://portail-api.insee.fr/
"""
from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

from imap_tools import MailBox, AND
from playwright.async_api import async_playwright

log = logging.getLogger("flows.insee")

PORTAL_URL = "https://portail-api.insee.fr/"
SIGNUP_URL = "https://portail-api.insee.fr/signup"
APPS_URL = "https://portail-api.insee.fr/apps"


async def run(profile, audit_dir: Path, write_credential) -> dict:
    """Orchestre le signup INSEE + création app + extraction creds."""
    password = secrets.token_urlsafe(24)
    (audit_dir / "password.txt").write_text(password, encoding="utf-8")
    (audit_dir / "password.txt").chmod(0o600)

    start_time = datetime.now(tz=timezone.utc)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="fr-FR",
        )
        page = await context.new_page()

        # Step 1 : Navigate signup page
        log.info("Navigate %s", SIGNUP_URL)
        await page.goto(SIGNUP_URL, wait_until="networkidle")
        await page.screenshot(path=str(audit_dir / "01_signup_page.png"))

        # Step 2 : Check for CAPTCHA
        captcha_frames = page.frames
        has_captcha = any(
            "recaptcha" in (f.url or "") or "hcaptcha" in (f.url or "") or "turnstile" in (f.url or "")
            for f in captcha_frames
        )
        if has_captcha:
            await page.screenshot(path=str(audit_dir / "99_CAPTCHA_DETECTED.png"))
            log.warning("CAPTCHA détecté — escalade founder")
            await browser.close()
            return {
                "status": "captcha_detected",
                "action_required": "founder_complete_manually",
                "audit_dir": str(audit_dir),
            }

        # Step 3 : Fill signup form (selectors à adapter — INSEE peut changer)
        # Sélecteurs génériques : par label ou placeholder
        try:
            await page.fill('input[name="email"], input[type="email"]', profile.project_email)
            await page.fill('input[name="password"], input[type="password"]', password)
            # Nom / prénom si form les demande
            for sel_first in ['input[name="firstname"]', 'input[name="firstName"]', 'input[name="prenom"]']:
                if await page.locator(sel_first).count():
                    await page.fill(sel_first, profile.contact_first_name)
                    break
            for sel_last in ['input[name="lastname"]', 'input[name="lastName"]', 'input[name="nom"]']:
                if await page.locator(sel_last).count():
                    await page.fill(sel_last, profile.contact_last_name)
                    break
            # Organization
            for sel_org in ['input[name="organization"]', 'input[name="company"]', 'input[name="societe"]']:
                if await page.locator(sel_org).count():
                    await page.fill(sel_org, profile.company_name)
                    break
            await page.screenshot(path=str(audit_dir / "02_form_filled.png"))
        except Exception as e:
            log.error("Échec fill form : %s", e)
            await page.screenshot(path=str(audit_dir / "99_form_fill_error.png"))
            await browser.close()
            return {"status": "form_fill_error", "error": str(e), "audit_dir": str(audit_dir)}

        # Step 4 : CGU checkbox — ON NE COCHE PAS AUTO
        cgu_checkbox = await page.locator('input[type="checkbox"]').count()
        if cgu_checkbox > 0:
            log.warning("CGU checkbox détectée — escalade founder (ne coche PAS auto)")
            await page.screenshot(path=str(audit_dir / "99_CGU_REQUIRED.png"))
            await browser.close()
            return {
                "status": "cgu_pending",
                "action_required": "founder_accepts_cgu",
                "audit_dir": str(audit_dir),
                "note": "Form pré-rempli, email + password dans audit/. Founder doit cocher CGU + submit manuel.",
            }

        # Step 5 : Submit
        submit_btn = page.locator('button[type="submit"], button:has-text("Créer"), button:has-text("Sign up")')
        if await submit_btn.count():
            await submit_btn.first.click()
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.screenshot(path=str(audit_dir / "03_submit_result.png"))
        else:
            await browser.close()
            return {"status": "submit_button_not_found", "audit_dir": str(audit_dir)}

        # Step 6 : Verification email
        log.info("Attente email de vérification...")
        await asyncio.sleep(15)
        verification_link = None
        try:
            with MailBox(profile.project_email_imap_host, port=profile.project_email_imap_port).login(
                profile.project_email_user, profile.project_email_password, initial_folder="INBOX"
            ) as mailbox:
                for msg in mailbox.fetch(
                    AND(from_="insee.fr", date_gte=start_time.date()),
                    reverse=True,
                    limit=5,
                ):
                    # Recherche lien dans body
                    import re
                    urls = re.findall(r"https?://[^\s\"'<>]+", msg.text or msg.html or "")
                    for u in urls:
                        if "insee" in u and ("verify" in u or "confirm" in u or "activate" in u):
                            verification_link = u
                            break
                    if verification_link:
                        break
        except Exception as e:
            log.warning("IMAP lookup échoué : %s", e)

        if verification_link:
            await page.goto(verification_link, wait_until="networkidle")
            await page.screenshot(path=str(audit_dir / "04_email_verified.png"))
        else:
            await browser.close()
            return {
                "status": "email_verification_pending",
                "action_required": "founder_click_verif_email",
                "audit_dir": str(audit_dir),
            }

        # Step 7 : Login + navigate apps
        await page.goto(APPS_URL, wait_until="networkidle")
        await page.screenshot(path=str(audit_dir / "05_apps_page.png"))

        # NOTE : Le reste du flow (création app + extraction CLIENT_ID/SECRET)
        # dépend beaucoup de l'UI INSEE exact — à ajuster après exploration manuelle.
        # Pour MVP, on stoppe ici et on notifie le founder qui termine manuellement.
        await browser.close()

        return {
            "status": "account_created_pending_app_creation",
            "action_required": "founder_finish_app_creation",
            "audit_dir": str(audit_dir),
            "next_steps": [
                "1. Login sur https://portail-api.insee.fr avec email/password (dans audit/password.txt)",
                "2. Créer une application 'DEMOEMA-ingestion'",
                "3. Souscrire au produit 'Sirene V3'",
                "4. Copier CLIENT_ID + CLIENT_SECRET",
                "5. SSH root@VPS : cat >> /root/DEMOEMA-agents/.env <<EOF\nINSEE_CLIENT_ID=...\nINSEE_CLIENT_SECRET=...\nEOF",
            ],
        }

# Security Policy — DEMOEMA

## Reporting a Vulnerability

If you discover a security vulnerability in DEMOEMA, please report it responsibly.

**Contact** : `davyly1@gmail.com`
**Subject prefix** : `[SECURITY]`
**Response SLA** : initial acknowledgement within 5 business days.

Please include:
- A clear description of the vulnerability.
- Steps to reproduce (PoC if possible).
- Potential impact assessment.
- Suggested mitigation if any.

**Do not disclose publicly** (no GitHub issue, no tweet, no blog post) until we have had reasonable time to investigate and release a fix. We follow a 90-day coordinated disclosure timeline unless a shorter timeline is agreed.

## Scope

In scope:
- Web application `demoema.fr` and subdomains (`api.*`, `studio.*`).
- FastAPI backend, Next.js frontend, agents platform.
- Authentication, authorization, data access.
- Any exposed endpoint under `/api/**`.

Out of scope:
- Denial of service via volumetric attacks.
- Social engineering of staff.
- Physical attacks on IONOS infrastructure.
- Vulnerabilities in third-party dependencies that have not been patched upstream (please report them upstream first).

## Supported Versions

Only the `develop` branch (production) is actively maintained for security fixes. Older branches are archival only.

## Hardening posture

See `docs/SECURITY_MEASURES.md` (created in Lot L9) for the inventory of technical and organizational measures (RGPD art. 32 compliance).

## Secret rotation

Secrets are encrypted at rest using SOPS + age (see `docs/SECRETS_OPERATIONS.md`). Rotation policy: every 90 days for external provider tokens, immediately upon suspected compromise.

## Hall of fame

Researchers who report valid vulnerabilities may, with their consent, be credited in `docs/SECURITY_RESEARCHERS.md`.

# DEMOEMA — Incidents Log

Journal des incidents prod, secrets compromis, rollbacks, outages. **Append-only**.

Chaque incident :
- **ID** : `INC-YYYY-NNNN` incrémental.
- **Date début / fin** (UTC).
- **Sévérité** : P0 (prod down) / P1 (dégradé) / P2 (interne seulement).
- **Titre court**.
- **Impact** (utilisateurs, data, business).
- **Root cause**.
- **Remédiation immédiate**.
- **Post-mortem / prévention** (lot brief à compléter ou nouveau ticket Jira).

---

## Incidents

### INC-2026-0001 — Hash bcrypt admin Caddy exposé sur GitHub public
- **Date début** : commit initial du Caddyfile (à dater via `git log --follow Caddyfile`).
- **Date détection** : 2026-04-23 (audit brief v1).
- **Date résolution** : _en cours_ (L0 du brief).
- **Sévérité** : P1.
- **Titre** : `basic_auth { admin $2a$14$XT84OloZ/9o... }` dans Caddyfile:22 sur repo public `github.com/Zakariakhchiche/DEMOEMA`.
- **Impact** : si le password admin est trivial, accès potentiel à Supabase Studio prod (`studio.demoema.fr`).
- **Root cause** : hash bcrypt hardcodé dans un fichier commité, au lieu de variable env `{env.STUDIO_ADMIN_PASSWORD_HASH}`.
- **Remédiation** : (a) rotation du password (Zak à faire, Q16), (b) migrer vers `{env.STUDIO_ADMIN_PASSWORD_HASH}` (L0), (c) déplacer le secret dans SOPS (L0 anticipé de L11.1).
- **Prévention** : pre-commit hook gitleaks (L0), règle `demoema-caddy-bcrypt` dans `.gitleaks.toml`.

### INC-2026-0002 — Token Pappers MCP exposé sur GitHub public
- **Date début** : commit initial de `.mcp.json` (à dater via `git log --follow .mcp.json`).
- **Date détection** : 2026-04-23 (audit brief + migration doc Pappers).
- **Date résolution** : _en cours_ (révocation côté Pappers par Zak + `git rm .mcp.json` ce soir).
- **Sévérité** : P1 (risque consommation quota payant).
- **Titre** : token `1205c93f92d9d021ff5c9aa40d23dff6e71e33fc81badf2b` dans `.mcp.json` sur repo public.
- **Impact** : quiconque ayant cloné le repo peut consommer le quota Pappers (potentiellement payant) de Zak.
- **Root cause** : fichier de config MCP Claude Code IDE (non utilisé par le backend prod) commité sans être masqué ni ignoré.
- **Remédiation** : (a) **Zak** révoque le token sur pappers.fr (Q22 + étape A du doc migration), (b) `git rm .mcp.json` + ajouter au `.gitignore` (fait ce soir), (c) tracer ici.
- **Prévention** : règle gitleaks `demoema-pappers-mcp-token`, `.mcp.json` dans `.gitignore` + `secrets/` dans `.gitattributes` export-ignore.
- **Note historique** : le token reste visible dans `git log -p` (historique Git non réécrit par choix — voir §2 doc migration Pappers). Une fois révoqué côté Pappers, le token est inerte.

---

## Template pour futurs incidents

```markdown
### INC-YYYY-NNNN — <titre court>
- **Date début** : YYYY-MM-DD HH:MM UTC
- **Date détection** : YYYY-MM-DD HH:MM UTC
- **Date résolution** : YYYY-MM-DD HH:MM UTC
- **Sévérité** : P0 / P1 / P2
- **Titre** : description 1 ligne
- **Impact** : (users, data, $)
- **Root cause** : cause technique
- **Remédiation** : actions immédiates
- **Prévention** : modifs code/process pour éviter récidive
```

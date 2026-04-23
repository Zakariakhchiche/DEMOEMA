# DEMOEMA — Journal des décisions techniques

Chaque décision technique (ADR — Architecture Decision Record) est tracée ici. Format ADR simplifié.

Pour les décisions **produit/stratégiques**, voir `docs/DECISIONS_VALIDEES.md` (miroir Confluence).

---

## ADR-001 — Migration Pappers → API gouv (décision de sortir de Pappers)

**Date** : 2026-04-23
**Statut** : accepté
**Décideur** : Zak

### Contexte

Le code backend utilise les fonctions nommées `get_pappers_*` et `search_pappers`, mais en réalité elles appellent toutes **`recherche-entreprises.api.gouv.fr`** et **`annuaire-entreprises.data.gouv.fr`** via des alias internes `_papperclip_*` (cf. `docs/` externe `DEMOEMA_PAPPERS_MIGRATION.md` — archivé).

Le token Pappers MCP était commité dans `.mcp.json` du repo public GitHub — risque d'exploitation du quota.

L'API Pappers payante n'apporte pas de valeur incrémentale par rapport aux API gouv pour les cas d'usage M&A FR (dirigeants, BODACC, procédures, CA). L'INPI RNE couvre les bilans financiers détaillés.

### Décision

**Pappers n'est plus utilisé.** Les API gouv restent la source de vérité. Action immédiate :
1. Révocation du token Pappers côté pappers.fr (action Zak, à son réveil).
2. Suppression de `.mcp.json` du repo, ajout à `.gitignore`.
3. Retrait du feature flag mort `PAPPERS_MCP_URL` dans `backend/main.py`.
4. Cleanup des 8 occurrences `https://www.pappers.fr` dans `backend/demo_data.py` → `https://annuaire-entreprises.data.gouv.fr`.

### Conséquences

- ✅ Pas de régression fonctionnelle (les API gouv étaient déjà la source réelle).
- ✅ Économie ~500-2000€/mois (pas de contrat Pappers futur).
- ✅ Token public révoqué → plus de risque de consommation frauduleuse.
- 🟡 Les noms `get_pappers_*` restent trompeurs tant que le renommage cosmétique (L5.5) n'est pas fait. À faire en Lot L5 du brief.
- 🟡 Frontend continue d'appeler `/api/pappers/*` — garder alias backend 6 mois pour compat (décision L5.4 du brief).

### Liens

- `docs/INCIDENTS.md` INC-2026-0002 (exposition token public).
- Brief v5 §17 Q22 (décision tranchée ici).
- Brief v5 §L5.5 (renommage cosmétique à programmer).

---

## ADR-002 — Supabase Auth choisi vs SCRUM-74 Authentik/Keycloak

**Date** : 2026-04-23
**Statut** : _proposé — en attente validation Zak (Q1 + Q26)_
**Décideur** : Zak

### Contexte

Epic Jira SCRUM-74 planifie "Auth standalone (Authentik / Keycloak)". Réalité prod 2026-04-20 : Supabase Auth (via GoTrue self-hosted) déjà déployée et fonctionnelle.

### Décision proposée

**Conserver Supabase Auth**, fermer SCRUM-74 comme "Done (via GoTrue)".

Justification : GoTrue est open-source, self-hosté sur VPS IONOS (donc indépendant d'Atlassian/Supabase Cloud — **l'intention de SCRUM-74 est satisfaite**). Supabase Auth apporte en plus : RLS Postgres gratuite (défense en profondeur), JWT via JWKS public (pas de secret partagé à rotater), SDK `@supabase/ssr` officiel pour Next.js 15, invitation user via Studio.

Migration Authentik/Keycloak possible en ~1 sprint si Zak change d'avis plus tard (GoTrue ↔ Authentik API similaire sur OAuth2/OIDC).

### Conséquences

- ✅ Pas de nouveau composant à déployer/maintenir.
- ✅ RLS Postgres = couche sécu supplémentaire.
- 🟡 Lock-in technique Supabase léger. Acceptable pour Y1-Y2.

### Liens

- Brief v5 §L2 (implémentation).
- Brief v5 §17 Q1, Q26.

---

## Template pour futurs ADR

```markdown
## ADR-NNN — Titre court

**Date** : YYYY-MM-DD
**Statut** : proposé / accepté / déprécié / remplacé par ADR-MMM
**Décideur** : Zak (ou autre contributeur)

### Contexte

Problème / besoin / contrainte.

### Décision

Choix pris, avec justification courte.

### Conséquences

- ✅ gains positifs
- 🟡 tradeoffs acceptés
- ❌ ce qu'on perd

### Liens

Refs code, tickets Jira, autres ADRs.
```

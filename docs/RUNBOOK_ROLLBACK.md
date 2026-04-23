# DEMOEMA — Rollback Runbook

Procédure pour remettre la prod sur un commit antérieur en cas d'incident.

---

## Quand rollback

Déclenchement automatique (watcher Sentry/Prometheus — L11.4, post-MVP) :
- **5xx rate > 5% pendant 2 minutes consécutives** sur `api.demoema.fr`.
- **Healthcheck KO 3× consécutifs** (backend `/healthz`, frontend `/api/health`).
- **Garde-fou** : pas plus d'1 rollback auto par 30 min (sinon escalade Slack pour décision humaine).

Déclenchement manuel :
- Bug critique reporté par un client ou découvert interne.
- Régression perf (LCP > 4s, latence API P95 > 2s).
- Data corruption détectée.
- Failure d'une migration DB non prévue.

**Ne PAS rollback** quand :
- Slow query isolé (investiguer, patch forward).
- Erreur d'un seul user / SIREN (bug data, pas code).
- UX glitch cosmétique.

---

## Procédure

### Étape 1 — Identifier le commit SHA sûr

```bash
# Ouvrir docs/DEPLOY_LOG.md et trouver le dernier deploy marqué stable (pas [ROLLED BACK], pas [HOTFIX]).
# Ou, en SSH sur VPS :
ssh -i ~/.ssh/id_ed25519 root@82.165.242.205
cd /root/DEMOEMA
git log --oneline -10
# Identifier le SHA court du dernier commit connu bon.
```

### Étape 2 — Lancer le rollback

Depuis la machine locale (Zak ou CI) :

```bash
./infrastructure/scripts/rollback.sh <SHA_COURT>
# Exemple : ./infrastructure/scripts/rollback.sh abc1234
```

Le script :
1. SSH sur le VPS.
2. `git fetch --all`.
3. `git reset --hard <SHA>`.
4. `docker compose up -d --build --remove-orphans`.
5. `docker compose ps` pour vérifier tous les services healthy.

### Étape 3 — Vérifier

```bash
curl -I https://api.demoema.fr/healthz
curl -I https://demoema.fr/
# Attendre 2 min puis vérifier les métriques :
# - 5xx rate < 1% ?
# - LCP stable ?
# - Pas de spike nouveaux errors Sentry ?
```

### Étape 4 — Tracer

1. Dans `docs/DEPLOY_LOG.md` : ajouter une ligne "ROLLBACK" avec timestamp + SHA source et SHA cible.
2. Marquer le deploy d'origine `[ROLLED BACK at YYYY-MM-DD HH:MM]`.
3. Ouvrir un incident dans `docs/INCIDENTS.md` : INC-YYYY-NNNN + root cause + remédiation à venir.
4. Notifier Slack `#demoema-ops` (ou email `davyly1@gmail.com` si Slack pas encore setup).

### Étape 5 — Post-mortem

- Avant de re-déployer la version problématique, écrire un blameless post-mortem dans l'incident.
- Identifier le root cause.
- Créer un ticket Jira pour corriger + ajouter un test qui aurait attrapé la régression.
- Documenter la leçon dans `docs/LESSONS_LEARNED.md` (à créer).

---

## Test du rollback — obligatoire avant première utilisation en prod

Un rollback qu'on n'a jamais testé **n'est pas un rollback**.

Procédure de test (à faire une fois, en preview/staging si dispo, ou en prod hors heures de pointe) :

1. Noter le SHA actuel prod (`S1`).
2. Faire un commit trivial sur `develop` (ex : mettre à jour une date dans `README.md`).
3. Attendre le déploiement auto via GitHub Actions.
4. Noter le nouveau SHA (`S2`).
5. Lancer `./infrastructure/scripts/rollback.sh S1`.
6. Vérifier que la prod est de retour sur `S1` (le README redevient l'ancienne version).
7. Re-faire un deploy pour revenir sur `S2`.

Une fois ce test passé, cocher la case "rollback testé" dans le brief v5 L0.

---

## Limitations connues

- Le rollback **ne revert pas les migrations DB**. Si le commit cible ajoute une colonne `NOT NULL`, le rollback laissera cette colonne (inoffensif). Si une migration destructive (DROP TABLE) a été appliquée, il faut une restauration backup (voir `docs/RUNBOOK_BACKUP_RESTORE.md`, à créer en L7).
- Le rollback **ne revert pas les writes applicatifs** (données ingérées entre S1 et S2 qui pourraient reposer sur du code supprimé). Les pipelines doivent être idempotents (L6).
- Le rollback **ne revert pas les secrets rotatés** (rotation gérée hors git, via SOPS).

En cas de doute sur la sûreté du rollback, appeler Zak (`davyly1@gmail.com`) avant de lancer.

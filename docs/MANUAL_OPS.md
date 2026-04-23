# DEMOEMA — Manual Ops Inventory

Inventaire des opérations **actuellement manuelles** (friction humaine récurrente). Le mandat "tout automatisé" (audit brief v5 §16 philosophie) impose que cette liste **décroisse** à chaque sprint. Si elle stagne ou augmente, on régresse.

Chaque entrée :
- **Opération** : ce qu'il faut faire.
- **Fréquence** : par semaine, mois, ou événement.
- **Auto-target** : numéro de lot du brief qui l'automatise.
- **Statut** : 🔴 manuel / 🟠 semi-auto / 🟢 auto.

---

## État initial — 2026-04-23

| # | Opération | Fréquence | Auto-target | Statut |
|---|---|---|---|---|
| 1 | Deploy prod (git pull + docker compose up sur VPS) | À chaque merge develop | L0 (CI deploy.sh) | 🔴 |
| 2 | Rollback en cas d'incident | Sur événement 5xx spike | L11.4 (auto-rollback watcher) | 🔴 |
| 3 | Rotation Caddy admin password | Quand suspicion leak | L0 / L11.1 (SOPS + PR auto 90j) | 🔴 |
| 4 | Refresh token INPI RNE | Quand 401 constaté | L6.3 + L11.10 (cron 4h proactif) | 🔴 |
| 5 | Relancer APScheduler après restart Docker | À chaque restart | L6.4 (SQLAlchemyJobStore persistent) | 🔴 |
| 6 | Surveiller logs Docker pour erreurs | Quotidien | L0 Sentry + L11.12 Grafana+Loki | 🔴 |
| 7 | Backup datalake (pg_dump sur VPS) | Quotidien | L7 cron + chiffrement gpg + IONOS Object | 🔴 |
| 8 | Vérifier restore backup mensuel | 1× / mois | L11.11 auto-restore test | 🔴 |
| 9 | Ajouter un user (invitation via Supabase Studio) | Sur événement | L2 + L11.5 onboarding auto email | 🔴 |
| 10 | Envoyer digest signaux quotidien | Quotidien | L11.6 digest cron | 🔴 |
| 11 | Alerter sur signal critique (procédure collective) | Sur événement | L11.7 alerte temps réel LISTEN/NOTIFY | 🔴 |
| 12 | Scanner nouvelles sources data.gouv | Hebdo | L11.9 source-hunter auto-discovery | 🔴 |
| 13 | Générer fetcher Python depuis spec YAML | Sur événement | L11.8 codegen GitHub Action hebdo | 🔴 |
| 14 | Tracking coûts LLM + infra | Mensuel | L11.12 Prometheus+Grafana cost | 🔴 |
| 15 | Surveillance expiration domaine / cert / plans hosting | Trimestriel | L11.13 cron WHOIS check | 🔴 |
| 16 | Appliquer migrations DB au deploy | À chaque deploy | L6.6 alembic au boot | 🔴 |
| 17 | Review PR Dependabot patch/minor | Hebdo | L11.2 auto-merge Dependabot | 🔴 |
| 18 | Vérification infos RGPD conformité | Annuel | L9 automatiser registre + DPO alertes | 🔴 |
| 19 | Génération rapport Cible pour client | Sur commande | L10 pipeline Stripe + WeasyPrint + S3 | 🔴 |
| 20 | Review dashboards Supabase Studio pour anomalies | Hebdo | L11.12 Grafana dashboards DEMOEMA | 🔴 |

**Total entrées manuelles initiales** : **20**
**Cible fin Tier 1 (juin 2026)** : ≤ 15 (items 1, 2, 3, 7, 9 auto)
**Cible fin Tier 2 (octobre 2026)** : ≤ 10
**Cible fin Tier 3 (post-Seed Y2)** : ≤ 3

---

## Historique des réductions

_(ajouter une ligne à chaque fois qu'un item passe 🔴 → 🟠 → 🟢)_

| Date | Item # | Avant | Après | Commit / PR |
|---|---:|---|---|---|

---

**Règle** : avant tout commit qui touche à l'opérationnel, mettre à jour cette table. Si un item passe 🟢, le marquer comme tel et déplacer dans "Historique des réductions".

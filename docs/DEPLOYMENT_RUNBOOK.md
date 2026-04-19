# DEPLOYMENT RUNBOOK — VPS IONOS (V4.2)

> Runbook opérationnel pour DEMOEMA sur VPS IONOS, déployé le 2026-04-20.
>
> Public : founder, Lead Data Eng (juillet 26), astreinte future.
>
> Référence infra : [`../infrastructure/README.md`](../infrastructure/README.md) · Architecture : [`ARCHITECTURE_TECHNIQUE.md`](./ARCHITECTURE_TECHNIQUE.md)

---

## 0. Contacts d'urgence

| Rôle | Personne | Contact |
|---|---|---|
| Founder | Zakaria Khchiche | `zkhchiche@hotmail.com` |
| Hébergeur | IONOS Business Support | 0970 808 911 / portail IONOS |
| DNS | (registrar à préciser) | — |
| DPO | (à contracter juillet 26) | — |
| Slack alerts | `#demoema-infra` | webhook dans `.env` |

---

## 1. Accès VPS

```bash
ssh deploy@demoema.fr          # user applicatif
ssh root@<ip_ionos>            # admin (root, bastion si possible)
```

Config SSH recommandée (`~/.ssh/config`) :
```
Host demoema-prod
    HostName demoema.fr
    User deploy
    IdentityFile ~/.ssh/demoema_ionos_ed25519
    ServerAliveInterval 30
```

**Clés SSH** : rotation semestrielle, clés révoquées dans `~deploy/.ssh/authorized_keys.revoked`.

---

## 2. Services systemd

| Service | Port | Log |
|---|---|---|
| `demoema-api` | 8000 | `journalctl -u demoema-api -f` |
| `demoema-web` | 3000 | `journalctl -u demoema-web -f` |
| `demoema-agents` | — | `journalctl -u demoema-agents -f` |
| `demoema-dagster` | 3001 | `journalctl -u demoema-dagster -f` |
| `nginx` | 80/443 | `journalctl -u nginx -f` + `/var/log/nginx/` |

### Commandes courantes

```bash
sudo systemctl status demoema-api
sudo systemctl restart demoema-api
sudo systemctl reload nginx               # pas de restart sauf changement structurel
sudo systemctl list-units --failed        # voir les failing
```

---

## 3. Services docker-compose

```bash
cd /opt/demoema/infrastructure
docker compose ps
docker compose logs -f postgres
docker compose logs -f ollama
docker compose restart redis
docker compose pull && docker compose up -d     # mise à jour images
```

**Containers** : `demoema-postgres`, `demoema-redis`, `demoema-ollama`, `demoema-minio`, `demoema-prometheus`, `demoema-loki`, `demoema-grafana`.

---

## 4. Déploiement applicatif

### CI automatique

Push sur `main` dans `backend/`, `frontend/`, `infrastructure/agents/` ou `infrastructure/dbt/` déclenche `.github/workflows/deploy-ionos.yml` → SSH + pull + restart + healthcheck + notif Slack si échec.

### Déploiement manuel

```bash
cd ~/DEMOEMA
./infrastructure/scripts/deploy.sh backend main
./infrastructure/scripts/deploy.sh frontend main
./infrastructure/scripts/deploy.sh agents main
./infrastructure/scripts/deploy.sh all v1.4.0    # tag git précis
```

Le script fait : git pull → install deps → migrations alembic (backend) → build (frontend) → systemctl restart → healthcheck.

---

## 5. Base de données Postgres

### Console
```bash
docker exec -it demoema-postgres psql -U demoema demoema
```

### Migrations

```bash
cd /opt/demoema/backend
.venv/bin/alembic current
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1       # rollback ONE migration si besoin
```

### Monitoring requêtes lentes

```sql
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY total_exec_time DESC
LIMIT 20;
```

### Index manquants (hint)

```sql
SELECT schemaname, relname, seq_scan, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan * 10 AND n_live_tup > 10000
ORDER BY seq_scan DESC;
```

---

## 6. Backups & restore

### Automatique

Cron `/etc/cron.d/demoema-backup` → `backup.sh` tous les jours à 03:00 :
- `pg_dump -Fc -Z 9` → `/opt/demoema/backups/postgres/`
- Redis BGSAVE → `dump.rdb.zst`
- MinIO mirror → `/opt/demoema/backups/minio/YYYY-MM-DD/`
- Rétention locale 30j
- Réplication chiffrée vers IONOS Object Storage (bucket `demoema-backups`)

### Vérification (hebdo)

```bash
ls -lh /opt/demoema/backups/postgres/ | tail -5
aws s3 ls s3://demoema-backups/postgres/ --endpoint-url $IONOS_S3_ENDPOINT | tail -5
```

### Restore (RTO cible 2h)

```bash
sudo -u demoema /opt/demoema/infrastructure/scripts/restore.sh 2026-04-19
# Confirm prompt : tape 'RESTORE 2026-04-19'
```

Le script coupe les services applicatifs, DROP DATABASE demoema, pg_restore, relance services.

---

## 7. Agents Ollama (Worker + Superviseur)

### Monitoring

```bash
journalctl -u demoema-agents -f
docker exec demoema-ollama ollama ps                    # modèles chargés en RAM
docker exec demoema-ollama ollama list                  # modèles disponibles
```

### Dashboard Grafana

`https://demoema.fr/grafana` → Dashboard **Agent Health** :
- Taux de succès par source (24h / 7j / 30j)
- Latence Worker p50/p95
- Alertes Superviseur en cours
- Fraîcheur des 20 sources critiques

### Requêtes audit

```sql
SELECT source_id, status, count(*)
FROM audit.agent_actions
WHERE created_at > now() - interval '24 hours'
GROUP BY source_id, status
ORDER BY source_id;

SELECT * FROM audit.alerts
WHERE resolved_at IS NULL
ORDER BY created_at DESC;

SELECT * FROM audit.source_freshness
WHERE status != 'ok';
```

### Restart agent

```bash
sudo systemctl restart demoema-agents
# ou via flag (utilisé par tool restart_worker du Superviseur)
touch /tmp/demoema-agents-restart.flag
```

---

## 8. TLS / certificats

```bash
sudo certbot certificates                                         # expiration
sudo certbot renew --dry-run                                      # test renew
sudo systemctl reload nginx                                       # après renew
```

Renouvellement auto : cron `/etc/cron.d/certbot` (installé par paquet).

Alerte Prometheus `cert_expire_days < 30` → Slack.

---

## 9. Troubleshooting

### API 502 Bad Gateway
1. `sudo systemctl status demoema-api` — est-ce que le service tourne ?
2. `journalctl -u demoema-api -n 100` — dernière erreur ?
3. `docker compose ps` — postgres + redis up ?
4. `curl -v http://127.0.0.1:8000/healthz` — API atteignable en local ?

### Copilot SSE ne streame pas
Vérifier nginx `proxy_buffering off` sur `/api/copilot/stream` (cf. `nginx/demoema.conf`). Headers `Content-Type: text/event-stream` + `Cache-Control: no-cache` côté FastAPI.

### Agent OOM
- `free -h` — voir mémoire disponible
- Baisser `OLLAMA_NUM_PARALLEL=1` dans docker-compose
- Fallback temporaire : mettre Superviseur sur Claude API (change `.env` + restart)

### Disque plein
```bash
df -h
du -sh /opt/demoema/backups/*
sudo journalctl --vacuum-time=7d
docker system prune -af --volumes        # ATTENTION : vérifier volumes nommés
```

### Postgres lent
- `VACUUM ANALYZE` — stats à jour ?
- `pg_stat_statements` — requêtes lentes ?
- `REINDEX` — fragmentation index ?
- Grafana dashboard "Postgres" — cache hit ratio, WAL, connexions

---

## 10. Check-list post-déploiement

Après chaque déploiement non trivial :
- [ ] `curl https://api.demoema.fr/healthz` → 200
- [ ] `curl https://demoema.fr/ -o /dev/null -w "%{http_code}"` → 200
- [ ] Test copilot (envoi requête + streaming reçu)
- [ ] Dashboard Grafana "Agent Health" : toutes sources vertes
- [ ] `SELECT count(*) FROM audit.alerts WHERE resolved_at IS NULL AND level='critical'` → 0
- [ ] Dernier `pg_dump` présent et >100 MB
- [ ] Slack `#demoema-infra` : pas d'alerte dans les 30 dernières min

---

## 11. Escalation

| Niveau | Trigger | Action |
|---|---|---|
| **P0** | Production down >5min | Founder immédiat (SMS) + rollback dernier deploy |
| **P1** | API 5xx >1% sur 10min | Slack + restart service + enquête |
| **P2** | Agent ingestion failed 1 source >12h | Slack channel + investigation jour ouvré |
| **P3** | Cert TLS <30j | Renouvellement planifié dans la semaine |

---

## 12. Historique des déploiements

| Date | Version | Notes |
|---|---|---|
| 2026-04-20 | V4.2 | Migration initiale Vercel+Supabase → VPS IONOS + dual-agent Ollama (SCRUM-66 + SCRUM-80) |

Mettre à jour ce tableau à chaque release majeure.

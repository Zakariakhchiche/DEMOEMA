# INGESTION DATA — Architecture dual-agent Ollama (V4.2)

> **Décision 2026-04-19** : sur le VPS IONOS, l'ingestion des 20+ APIs data publiques sera orchestrée par un **système dual-agent IA via Ollama** (modèles locaux, souveraineté FR/DE, coût marginal nul).
>
> Source : nouvelle exigence founder. Ticket Epic : SCRUM-67.

---

## 1. Pourquoi 2 agents ?

### Pourquoi pas du code Python "classique" ?
Pour les 20 sources data publiques (INSEE, INPI, BODACC, etc.), un script Python + Dagster suffit **à 80 %**. Mais 20 % du temps :
- L'API change subtilement (nouveau champ JSON, redirection, format différent)
- Un quota dépasse → faut décider : retry / backoff / fallback / alerter
- Un payload contient une donnée inattendue qu'il faut normaliser intelligemment
- Un appel échoue mais avec un message ambigu → faut interpréter

C'est sur ces **20 % de cas tordus** que les agents IA apportent de la valeur : raisonnement, adaptabilité, prise de décision contextuelle.

### Pourquoi 2 agents et pas 1 ?

**Séparation des responsabilités** = pattern éprouvé en multi-agent :
- **Worker** = exécution (action, throughput, déterminisme local)
- **Superviseur** = jugement (monitoring, anomalies, alertes, replanification)

Avantages :
1. Le Worker peut être **stateless** et facilement scalable (1 worker par source ou par batch)
2. Le Superviseur a une **vue globale** (cross-sources, tendances, SLO violation)
3. Si le Worker hallucine ou se trompe, le Superviseur attrape l'erreur (double-check)
4. Si le Superviseur tombe, le Worker continue à fonctionner (graceful degradation)
5. Modèles différents possibles : **Worker rapide/petit**, **Superviseur plus puissant** (jugement)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  VPS IONOS (Postgres + Dagster + Ollama + agents)           │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Dagster scheduler (lance les jobs ingestion)       │    │
│  └────────────┬────────────────────────────────────────┘    │
│               │                                              │
│               ▼                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AGENT WORKER (Ollama: Qwen2.5-Coder 14B)           │    │
│  │  ─────────────────────────────────────────────────   │    │
│  │  Pour chaque source assignée :                       │    │
│  │  1. Lit la spec API (YAML config)                    │    │
│  │  2. Décide stratégie (full / delta / retry)          │    │
│  │  3. Tool-calling Python : httpx, json parse, dbt run │    │
│  │  4. Normalise payload → silver Postgres              │    │
│  │  5. Si erreur ambiguë → escalade au Superviseur      │    │
│  │  6. Émet métriques : latence, volume, erreurs        │    │
│  └────────────┬────────────────────────────────────────┘    │
│               │ (events + metrics)                          │
│               ▼                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Redis Streams (event bus interne)                   │    │
│  └────────────┬────────────────────────────────────────┘    │
│               │                                              │
│               ▼                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AGENT SUPERVISEUR (Ollama: Llama 3.3 70B Q4 ou     │    │
│  │  Qwen2.5 32B selon RAM dispo)                        │    │
│  │  ─────────────────────────────────────────────────   │    │
│  │  • Surveille les flux Worker (métriques, erreurs)    │    │
│  │  • Détecte anomalies : drops volume, latence, échecs │    │
│  │  • Décide actions : restart / reconfig / alerte      │    │
│  │  • Tool-calling : Slack webhook, retrigger Dagster   │    │
│  │  • Génère rapport quotidien (synthèse fraîcheur)     │    │
│  │  • Alerte critique → email founder + Slack channel   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Postgres (Bronze + Silver + Gold + Marts)           │    │
│  │  + tables d'audit (audit.agent_actions, audit.alerts)│    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Choix des modèles Ollama

### Critères
- **Tool-calling natif** (function calling) — indispensable pour appeler httpx / Postgres
- **Faible latence** sur CPU (la plupart des VPS IONOS = CPU only sauf plan GPU)
- **Multilingue FR** (les payloads contiennent du français)
- **Open weights** + licence permissive

### Recommandations selon spec VPS IONOS

| Plan VPS IONOS | RAM | Worker recommandé | Superviseur recommandé |
|---|---|---|---|
| **VPS XS** (4 vCPU, 8 GB RAM) | 8 GB | Llama 3.2 3B Q4 (~2 GB) | Qwen2.5 7B Q4 (~5 GB) |
| **VPS S** (4 vCPU, 16 GB RAM) | 16 GB | Qwen2.5-Coder 7B Q4 (~5 GB) | Qwen2.5 14B Q4 (~9 GB) |
| **VPS M** (6 vCPU, 32 GB RAM) ⭐ recommandé | 32 GB | **Qwen2.5-Coder 14B Q4** (~9 GB) | **Qwen2.5 32B Q4** (~20 GB) |
| **VPS L** (8 vCPU, 64 GB RAM) | 64 GB | Qwen2.5-Coder 32B (~20 GB) | Llama 3.3 70B Q4 (~40 GB) |
| **VPS XL GPU** (RTX A4000 16GB) | GPU | Qwen2.5-Coder 14B FP16 | Llama 3.3 70B Q4 |

### Pourquoi Qwen2.5-Coder pour le Worker ?
- Excellent **tool-calling** + **JSON parsing**
- Très bon en FR (Alibaba a optimisé pour le multilingue)
- Latence acceptable sur CPU (10-30 tokens/s en Q4)
- Spécialisé code → idéal pour générer/valider scripts d'ingestion

### Pourquoi Qwen2.5 32B (ou Llama 3.3 70B) pour le Superviseur ?
- Meilleur **raisonnement complexe** (anomaly detection, decision making)
- Capacité de **synthèse multi-sources** (rapport quotidien)
- Vue globale = nécessite plus de contexte → modèle plus grand
- Latence moins critique (n'est pas dans le chemin critique)

### Si VPS sans GPU et lent
**Alternative pragmatique** :
- Worker = Qwen2.5-Coder 7B local (gratuit, rapide)
- **Superviseur = Claude API** (~10€/mois pour quelques rapports/jour) — meilleur jugement, pas besoin de tourner 24/7

---

## 4. Framework agents — choix techniques

### Options
| Framework | Pour | Contre |
|---|---|---|
| **CrewAI** (Python) | Multi-agent simple, native, bonne UX dev | Nouveau, écosystème en maturation |
| **LangGraph** (LangChain) | Très flexible, graphe d'états explicite | Verbose, courbe d'apprentissage |
| **Custom Python** | Contrôle total, dépendances minimales | Tout à coder soi-même |
| **Autogen** (Microsoft) | Multi-agent mature | Complexe, plus orienté chatbot |

### Recommandation : **CrewAI**
- Patterns Worker/Superviseur natifs (Crew, Agent, Task, Process)
- Tool-calling intégré
- Compatible Ollama directement (`langchain_ollama`)
- 10x moins de code qu'autocoder en Python pur

```python
# Pseudo-code architecture
from crewai import Agent, Task, Crew, Process
from langchain_ollama import ChatOllama

worker = Agent(
    role="Data Ingestion Worker",
    goal="Ingérer correctement les sources data publiques",
    llm=ChatOllama(model="qwen2.5-coder:14b", base_url="http://localhost:11434"),
    tools=[httpx_call, postgres_insert, dbt_run, parse_xml]
)

superviseur = Agent(
    role="Ingestion Supervisor",
    goal="Garantir SLO fraîcheur + qualité data",
    llm=ChatOllama(model="qwen2.5:32b", base_url="http://localhost:11434"),
    tools=[query_metrics, send_slack_alert, restart_worker, generate_report]
)

crew = Crew(
    agents=[worker, superviseur],
    tasks=[ingestion_task, supervision_task],
    process=Process.hierarchical,
    manager_llm=ChatOllama(model="qwen2.5:32b")
)
```

---

## 5. Sécurité, conformité, coûts

### Sécurité
- Ollama tourne **localement sur VPS IONOS** : aucune donnée envoyée à des tiers
- Tool-calling sécurisé : whitelist des fonctions Python, pas de `exec()` arbitraire
- Logs prompts/réponses dans `audit.agent_actions` (rétention 90j)

### Conformité AI Act
✅ **Statut "déployeur" préservé** : on **utilise** des modèles open weights (Qwen, Llama) sans les modifier ni les fine-tuner.
✅ **Pas de scoring de personnes physiques** : les agents traitent des entreprises uniquement.
✅ **Logs traçables** pour audit.

### Coûts
| Composant | Coût mensuel |
|---|---|
| VPS IONOS M (recommandé) | ~50-80 € |
| Modèles Ollama | 0 € (open weights) |
| Optionnel Claude API supervision | 10-30 € |
| **Total** | **~50-110 €/mois** |

vs alternative tout cloud (LLM API + serverless) : **300-500 €/mois** = économie 70 %.

---

## 6. Roadmap implémentation

| Sprint | Tâche | Owner |
|---|---|---|
| Q3 2026 S1 | Provisionner VPS IONOS + Ollama + 2-3 modèles | Lead Data Eng |
| Q3 2026 S2 | POC Worker sur 1 source simple (BODACC) | Lead Data Eng |
| Q3 2026 S3 | Ajouter Superviseur + Slack alerts | Lead Data Eng |
| Q3 2026 S4 | Étendre à 5 sources (top priorités) | Lead Data Eng + Backend |
| Q4 2026 | 10 sources orchestrées + dashboard métriques | Lead Data Eng |
| Y2 | Scaling + auto-tuning des paramètres | + ML Eng |

---

## 7. Tables Postgres associées

```sql
-- Audit des actions agents
CREATE TABLE audit.agent_actions (
  id            BIGSERIAL PRIMARY KEY,
  agent_role    VARCHAR NOT NULL,        -- 'worker' | 'superviseur'
  task_id       UUID,
  source_id     VARCHAR,                  -- ex 'S001 INSEE SIRENE'
  action        VARCHAR NOT NULL,         -- 'fetch','parse','insert','alert','restart'
  payload_in    JSONB,
  payload_out   JSONB,
  status        VARCHAR,                  -- 'success','retry','failed','escalated'
  duration_ms   INT,
  llm_model     VARCHAR,
  llm_tokens    INT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- Alertes générées
CREATE TABLE audit.alerts (
  id              BIGSERIAL PRIMARY KEY,
  level           VARCHAR CHECK (level IN ('info','warning','critical')),
  source_id       VARCHAR,
  message         TEXT,
  resolution      TEXT,
  notified_via    VARCHAR[],              -- ['slack','email']
  created_at      TIMESTAMPTZ DEFAULT now(),
  resolved_at     TIMESTAMPTZ
);

-- Métriques fraîcheur
CREATE TABLE audit.source_freshness (
  source_id       VARCHAR PRIMARY KEY,
  last_success_at TIMESTAMPTZ,
  rows_last_run   INT,
  expected_rows_p50 INT,
  sla_minutes     INT,
  status          VARCHAR                 -- 'ok','degraded','failed'
);
```

---

## 8. Points ouverts (à trancher)

1. **Quelle spec VPS IONOS** as-tu prise ? (XS / S / M / L / GPU) → détermine les modèles utilisables.
2. **Superviseur en local Ollama vs Claude API** ? Local = 0€ / variable. Claude = qualité supérieure / 10-30€/mois.
3. **Framework** : CrewAI (recommandé) ou Custom Python ?
4. **Slack workspace pour alertes** : créer dédié ou utiliser celui du founder ?
5. **Rétention logs `audit.agent_actions`** : 30j (RGPD léger) ou 90j (debug + compliance) ?

---

## 9. Comparaison vs approche actuelle (Vercel Cron + Python)

| Aspect | Actuel (Vercel Cron) | Cible (Dual-agent Ollama IONOS) |
|---|---|---|
| Sources gérables | ~5-10 max | 20-50 (scaling natif) |
| Adaptabilité | Code rigide | Agents s'adaptent aux changements |
| Détection anomalie | Manuel | Superviseur auto |
| Coût | Gratuit Vercel | ~80€/mois VPS |
| Souveraineté data | ❌ AWS | ✅ FR/DE |
| Reprise après échec | Manuel | Superviseur auto-restart |
| Reporting fraîcheur | ❌ | ✅ rapport quotidien |
| Vendor lock-in | Vercel | Aucun (open source + VPS) |

---

## 10. Liens

- Décision stack : [`DECISIONS_VALIDEES.md` §9 V4](./DECISIONS_VALIDEES.md)
- Architecture cible : [`ARCHITECTURE_TECHNIQUE.md` V4.1](./ARCHITECTURE_TECHNIQUE.md)
- Sources data : [`ARCHITECTURE_DATA_V2.md`](./ARCHITECTURE_DATA_V2.md)
- Lineage : [`DATACATALOG.md`](./DATACATALOG.md)
- Tickets Jira : Epic SCRUM-67 (à créer)

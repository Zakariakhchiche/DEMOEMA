# 🎨 Architecture Diagrams — DEMOEMA (Mermaid)

> **Diagrammes architecture du projet DEMOEMA** au 29/04/2026.
> Rendu : GitHub, Confluence (avec macro Mermaid), Notion, VS Code (extension Markdown Preview Mermaid).

---

## 1. Vue d'ensemble — Medallion architecture

Pipeline complet bronze → silver → gold → API → frontend, avec les volumes actuels.

```mermaid
flowchart TB
    subgraph SOURCES["📡 Sources externes (109+ sources cataloguées)"]
        INSEE[INSEE SIRENE<br/>43M étab]
        INPI[INPI RNE<br/>8M dirigeants]
        BODACC[BODACC OpenData<br/>30M annonces]
        DILA[DILA OpenData<br/>11 onglets juri+M&A]
        OSINT[OSINT Phase 1<br/>Wikidata/HAL/GitHub/crt.sh]
        OTHER[+90 autres sources]
    end

    subgraph BRONZE["🥉 BRONZE — Raw data (115 tables, 512 GB)"]
        B_INPI[bronze.inpi_*<br/>410M+ rows]
        B_BODACC[bronze.bodacc_*<br/>30M rows]
        B_DILA[bronze.juri_*<br/>+ amf_dila + balo + etc.]
        B_OSINT[bronze.osint_*<br/>+ wikidata + github + ...]
    end

    subgraph SILVER["🥈 SILVER — Cleaned + normalized (29 specs)"]
        S_BASE[silver.inpi_dirigeants 8.1M<br/>silver.insee_etablissements 43M<br/>silver.opensanctions 280K]
        S_MA[silver.dirigeants_360<br/>silver.entreprises_signals<br/>+ 11 silvers M&A]
        S_OSINT[silver.persons_resolved<br/>silver.persons_contacts_enriched]
    end

    subgraph GOLD["🥇 GOLD — Feature store (13 specs)"]
        G_MASTER[gold.entreprises_master<br/>gold.dirigeants_master<br/>gold.cibles_ma_top]
        G_FEED[gold.signaux_ma_feed<br/>gold.compliance_red_flags]
        G_CONTACTS[gold.persons_contacts_master]
        G_ENRICH[gold.juridictions_master<br/>gold.network_mandats<br/>+ 5 autres]
    end

    subgraph API["🔌 API FastAPI"]
        A_REST[REST endpoints<br/>/api/entreprises/*<br/>/api/dirigeants/*<br/>/api/contentieux/*]
        A_SSE[Server-Sent Events<br/>copilot streaming]
        A_AUTH[Auth Supabase JWT]
    end

    subgraph FRONT["💻 Frontend Next.js 15"]
        F_DASH[Dashboard]
        F_TARGETS[Intelligence Targets<br/>cibles_ma_top]
        F_SIGNALS[Feed Signaux<br/>signaux_ma_feed]
        F_GRAPH[Graphe Réseau<br/>network_mandats]
        F_COPILOT[Copilot IA]
    end

    SOURCES --> BRONZE
    BRONZE -->|silver_codegen LLM<br/>parallèle 4-wide| SILVER
    SILVER -->|gold_codegen LLM<br/>parallèle 4-wide| GOLD
    GOLD --> API
    API --> FRONT

    classDef bronze fill:#cd7f32,color:#fff
    classDef silver fill:#c0c0c0,color:#000
    classDef gold fill:#ffd700,color:#000
    classDef api fill:#3498db,color:#fff
    classDef front fill:#9b59b6,color:#fff

    class BRONZE bronze
    class SILVER silver
    class GOLD gold
    class API api
    class FRONT front
```

---

## 2. Codegen pipeline — Comment les fetchers/silvers/golds sont générés

L'agent `lead-data-engineer` (LLM Ollama Cloud + DeepSeek fallback) lit les specs YAML et génère le SQL/Python automatiquement.

```mermaid
flowchart LR
    subgraph INPUT["📝 Input"]
        SPEC[spec YAML<br/>silver_specs/X.yaml]
        REF[Reference fetcher<br/>_xxx_ref.py]
        SCHEMA[Schema introspection<br/>pg_attribute]
    end

    subgraph LLM["🤖 LLM lead-data-engineer"]
        OLLAMA[Ollama Cloud Pro<br/>kimi-k2.6 1M context]
        DEEPSEEK[DeepSeek fallback<br/>180s timeout]
    end

    subgraph VALIDATION["✅ Validation"]
        REGEX[Regex check<br/>banned patterns]
        AST[Python ast.parse]
        DRYRUN[Dry-run endpoint test]
    end

    subgraph APPLY["⚙️ Apply"]
        CREATE[CREATE TABLE/MV<br/>+ CREATE INDEX]
        UPSERT[INSERT ON CONFLICT<br/>idempotent]
        AUDIT[audit.silver_specs_versions<br/>UPDATE applied=true]
    end

    SPEC --> LLM
    REF --> LLM
    SCHEMA --> LLM
    LLM --> VALIDATION
    VALIDATION -->|valid| APPLY
    VALIDATION -->|invalid<br/>retry with feedback| LLM
    APPLY --> SOURCES_DICT[Register dans SOURCES dict<br/>hot-reload]

    style LLM fill:#fef3bd
    style VALIDATION fill:#d4edda
    style APPLY fill:#cce5ff
```

---

## 3. Parallélisation topologique silver bootstrap (commit 2932c77)

Silver bootstrap utilise Kahn topological sort pour exploiter les dépendances en parallèle 4-wide.

```mermaid
flowchart TB
    subgraph LEVEL0["Level 0 — silvers à sources bronze pures (parallèle 4-wide)"]
        L0_1[silver.bodacc_annonces]
        L0_2[silver.inpi_dirigeants]
        L0_3[silver.opensanctions]
        L0_4[silver.dvf_transactions]
        L0_5[silver.balo_operations]
        L0_6[silver.juridictions_unifiees]
        L0_DOTS[+ 13 autres specs]
    end

    subgraph LEVEL1["Level 1 — silver-of-silver (attend level 0)"]
        L1_1[silver.dirigeants_360]
        L1_2[silver.entreprises_signals]
        L1_3[silver.persons_resolved]
    end

    subgraph LEVEL2["Level 2 — silver-of-silver-of-silver"]
        L2_1[silver.persons_contacts_enriched]
    end

    subgraph SCHEDULER["asyncio.gather + Semaphore(silver_codegen_parallelism=4)"]
        SEM[Sémaphore cap 4 LLM concurrents<br/>par level]
    end

    LEVEL0 --> SEM
    SEM -.->|attend complétion level 0| LEVEL1
    LEVEL1 --> LEVEL2

    L0_1 --> L1_1
    L0_2 --> L1_1
    L0_3 --> L1_1
    L0_5 --> L1_2
    L0_6 --> L1_2
    L1_1 --> L2_1
    L1_3 --> L2_1

    style LEVEL0 fill:#e8f4f8
    style LEVEL1 fill:#fff3cd
    style LEVEL2 fill:#f8d7da
```

**Bénéfice** : 70 min séquentiel → ~30 min parallèle 4-wide sur fresh boot.

---

## 4. OSINT enrichment pipeline — comment les dirigeants sont enrichis

```mermaid
flowchart TB
    subgraph INPI["INPI RNE (source)"]
        INPI_DIR[silver.inpi_dirigeants<br/>8.1M dirigeants FR]
    end

    subgraph PHASE1["📥 Phase 1 OSINT (sources gratuites massives)"]
        WIKI[Wikidata SPARQL<br/>~100K humans+companies FR]
        HAL[HAL chercheurs<br/>~36K]
        OPENALEX[OpenAlex publications<br/>~250K]
        GH[GitHub users<br/>~30K founders FR]
        CRT[crt.sh certificates<br/>~200K domaines]
        ORCID[ORCID chercheurs<br/>~100K FR]
    end

    subgraph PHASEA["💌 Phase A Contacts (gratuit)"]
        RDAP[RDAP/WHOIS<br/>registrant_email+phone]
        HOLEHE[Holehe email validation]
        HATVP[HATVP élus<br/>459K déclarations]
    end

    subgraph PHASEB["🤖 Phase B Enrichissement direct (Maigret)"]
        MAIGRET[osint_orchestrator.py<br/>cron 02:00 batch 1000<br/>filter pro_ma_score>=50]
        OSINT_PERS[bronze.osint_persons<br/>3000+ sites scanned]
    end

    subgraph RESOLUTION["🔗 Person Resolution"]
        RESOLVED[silver.persons_resolved<br/>identifiers JSONB<br/>resolution_confidence HIGH/MED/LOW]
    end

    subgraph CONTACTS["📞 Contacts master"]
        CONTACTS_S[silver.persons_contacts_enriched<br/>emails JSONB + phones JSONB]
        CONTACTS_G[gold.persons_contacts_master<br/>+ pro_ma_score + n_mandats]
    end

    subgraph DIRMASTER["🥇 Dirigeants master final"]
        DIR_MASTER[gold.persons_master_universal<br/>360° dirigeant complet]
    end

    INPI_DIR --> RESOLUTION
    PHASE1 --> RESOLUTION
    PHASE1 --> CONTACTS_S
    PHASEA --> CONTACTS_S
    PHASEB --> RESOLUTION
    OSINT_PERS --> CONTACTS_S
    RESOLUTION --> DIR_MASTER
    CONTACTS_S --> CONTACTS_G
    CONTACTS_G --> DIR_MASTER

    style PHASE1 fill:#d4edda
    style PHASEA fill:#d1ecf1
    style PHASEB fill:#fff3cd
    style RESOLUTION fill:#f8d7da
    style DIRMASTER fill:#ffd700,color:#000
```

---

## 5. Architecture infrastructure (VPS + containers)

```mermaid
flowchart TB
    subgraph VPS["☁️ VPS IONOS Paris (82.165.57.191)<br/>16 vCPU / 62 GB RAM / 945 GB NVMe"]
        subgraph DOCKER["🐳 Docker network agents-net + shared-supabase"]
            CADDY[demomea-caddy<br/>TLS auto ACME<br/>ports 80+443]

            subgraph FRONTEND_BACK["Application services"]
                FRONT[demomea-frontend<br/>Next.js 15]
                BACK[demomea-backend<br/>FastAPI Python 3.11]
                AGENTS[demomea-agents-platform<br/>168 jobs APScheduler]
            end

            subgraph DATA["Data layer"]
                DB[demomea-datalake-db<br/>Postgres 16 alpine<br/>shared_buffers=16GB<br/>maintenance_work_mem=4GB]
                NEO4J[demomea-neo4j<br/>graphe dirigeants]
                REDIS[demomea-redis<br/>cache sessions]
            end
        end

        subgraph SUPABASE["🟢 Supabase self-hosted (15 containers)"]
            SUPA_DB[supabase-db Postgres 15]
            SUPA_AUTH[supabase-auth GoTrue JWT]
            SUPA_KONG[supabase-kong API gateway]
            SUPA_STUDIO[supabase-studio admin UI]
        end

        subgraph EXT_LLM["🤖 LLM externes"]
            OLLAMA_CLOUD[Ollama Cloud Pro<br/>kimi-k2.6 1M ctx]
            DEEPSEEK_API[DeepSeek API<br/>fallback]
        end
    end

    USER[👤 Users<br/>EdRCF advisors] -->|HTTPS| CADDY
    CADDY --> FRONT
    CADDY --> BACK
    CADDY --> SUPA_KONG
    BACK --> AGENTS
    BACK --> DB
    BACK --> SUPA_AUTH
    AGENTS --> DB
    AGENTS --> NEO4J
    AGENTS --> REDIS
    AGENTS -->|codegen LLM calls| OLLAMA_CLOUD
    AGENTS -->|fallback| DEEPSEEK_API

    style VPS fill:#f0f0f0
    style DOCKER fill:#e3f2fd
    style SUPABASE fill:#d4edda
    style EXT_LLM fill:#fff3cd
```

---

## 6. Refresh schedules — quand chaque layer se met à jour

Timeline des jobs APScheduler par 24h.

```mermaid
gantt
    title Refresh schedules DEMOEMA — 24h timeline
    dateFormat HH:mm
    axisFormat %H:%M

    section Bronze
    109 sources cron individuel        :08:00, 24h
    Bronze codegen tick (5 min)         :crit, 00:00, 24h
    Bronze maintainer (6h)              :02:00, 6h

    section Silver
    Silver bootstrap (au boot)          :milestone, 06:00, 0
    Silver maintainer (30 min)          :crit, 00:00, 24h
    Silver refresh dirigeants_360       :03:00, 1h
    Silver refresh entreprises_signals  :03:30, 1h

    section Gold
    Gold bootstrap retry (30 min)       :crit, 00:00, 24h
    Gold refresh entreprises_master     :03:00, 1h
    Gold refresh dirigeants_master      :03:30, 1h
    Gold refresh cibles_ma_top          :04:00, 1h
    Gold refresh signaux_ma_feed        :crit, 00:00, 24h

    section OSINT
    OSINT Maigret nightly batch 1000    :02:00, 4h
    OSINT Phase 1 sources (cron weekly) :milestone, 06:00, 0

    section Misc
    Neo4j rebuild                       :04:00, 1h
    Supervisor daily report             :08:00, 30m
    DILA backfill (hebdo)               :milestone, 06:00, 0
```

---

## 7. Sources DILA OpenData (couche 5)

```mermaid
flowchart LR
    subgraph DILA["📂 https://echanges.dila.gouv.fr/OPENDATA/"]
        D_BODACC[BODACC]
        D_CASS[CASS]
        D_CAPP[CAPP]
        D_JADE[JADE]
        D_CONSTIT[CONSTIT]
        D_AMF[AMF]
        D_BALO[BALO]
        D_LEGI[LEGI]
        D_JORF[JORF]
        D_KALI[KALI]
        D_DOLE[DOLE]
        D_BOCC[BOCC]
    end

    subgraph FETCHERS["fetchers tar_gz_xml (généré par codegen)"]
        F_PATTERN[_tar_gz_xml_ref.py reference<br/>asyncio.Semaphore=4 archives parallèles<br/>tarfile.open + lxml.etree.fromstring]
    end

    subgraph BRONZE_DILA["Bronze tables"]
        B_BODACC2[bodacc_annonces_raw 30M]
        B_CASS2[judilibre_decisions_raw 145K]
        B_JADE2[juri_jade_raw 14K]
        B_AMF2[amf_dila_raw 29K]
        B_LEGI2[legifrance_textes_raw 235K]
        B_JORF2[jorf_textes_raw 309K]
        B_KALI2[kali_ccn_raw 158K]
    end

    DILA --> FETCHERS
    FETCHERS --> BRONZE_DILA

    style DILA fill:#e3f2fd
    style FETCHERS fill:#fff3cd
    style BRONZE_DILA fill:#cd7f32,color:#fff
```

---

## 8. Scoring M&A composite — comment pro_ma_score est calculé

```mermaid
flowchart TB
    subgraph FEATURES["Features par dimension"]
        F_MANDATS[Mandats: n_mandats_actifs, sirens[]]
        F_PATRIMOINE[Patrimoine SCI: total_capital_sci]
        F_FINANCIER[Financier: ca_total, resultat_net]
        F_RESEAU[Réseau: n_co_mandataires]
        F_BODACC[Événements BODACC: cessions, difficultés]
        F_LEGAL[Légal: n_jugements]
        F_SANCTIONS[Sanctions: opensanctions match]
        F_PRESSE[Presse: n_press_mentions_90d]
        F_DIGITAL[Digital: digital_presence_score]
    end

    subgraph FORMULA["score = LEAST(100, ...)"]
        SCORE[pro_ma_score 0-100]
    end

    F_MANDATS -->|+10 si is_pro_ma| FORMULA
    F_PATRIMOINE -->|+20 si has_holding| FORMULA
    F_FINANCIER -->|+15 si CA > 100M| FORMULA
    F_RESEAU -->|+1 par co-mandataire max 10| FORMULA
    F_BODACC -->|+5 si cession récente<br/>-10 si difficultés récentes| FORMULA
    F_LEGAL -->|-5 si contentieux récent| FORMULA
    F_SANCTIONS -->|-20 si sanctionné| FORMULA
    F_PRESSE -->|+5 si press buzz| FORMULA
    F_DIGITAL -->|+5 si présence digitale| FORMULA

    SCORE --> CLASSIFY{pro_ma_score >=}

    CLASSIFY -->|70| TIER1[Tier 1<br/>cible HOT M&A]
    CLASSIFY -->|50| TIER2[Tier 2<br/>cible WARM]
    CLASSIFY -->|30| TIER3[Tier 3<br/>monitoring]

    style FEATURES fill:#e8f4f8
    style FORMULA fill:#fff3cd
    style TIER1 fill:#dc3545,color:#fff
    style TIER2 fill:#ffc107
    style TIER3 fill:#28a745,color:#fff
```

---

## 9. Migration VPS-to-VPS (post-mortem 28/04)

```mermaid
sequenceDiagram
    participant Old as Ancien VPS<br/>82.165.242.205<br/>12 vCPU / 24 GB
    participant Local as Local laptop
    participant New as Nouveau VPS<br/>82.165.57.191<br/>16 vCPU / 62 GB
    participant DB_New as Postgres datalake-db<br/>(target)

    Local->>New: bootstrap-vps.sh (provisioning)
    New->>New: Docker compose up<br/>(datalake-db + agents-platform)
    Local->>New: migrate-vps.sh phase=env<br/>(copie .env)
    Local->>New: migrate-vps.sh phase=datalake
    New->>Old: ssh + push migration_key
    New->>Old: docker exec pg_dump -Fc<br/>(custom format compressed)
    Note over Old,New: Pipe SSH direct<br/>(zéro transit local)
    Old-->>New: pg_dump stream
    New->>DB_New: docker exec pg_restore<br/>--clean --if-exists --jobs=1
    Note over DB_New: 700 GB → 512 GB<br/>(restore + indexes)
    DB_New->>DB_New: ANALYZE VERBOSE
    Local->>New: ALTER SYSTEM tuning<br/>(shared_buffers=16GB)
    New->>New: Restart datalake-db<br/>(activate shared_buffers)
    Local->>New: Run silver_bootstrap parallel
    Local->>New: Run gold_bootstrap (30min auto-retry)
```

Durée totale : ~25h (dont 17h pg_restore en arrière-plan).

---

## 10. Audit log + RGPD compliance

```mermaid
flowchart LR
    subgraph SOURCES_AUDIT["Audit sources"]
        AUDIT_INGEST[audit.source_ingest_runs<br/>chaque fetch logged]
        AUDIT_SILVER[audit.silver_specs_versions<br/>chaque codegen logged]
        AUDIT_FRESH[audit.silver_freshness<br/>last_refresh per silver]
    end

    subgraph RGPD["RGPD garde-fous"]
        ART6[Art. 6: intérêt légitime<br/>M&A advisory]
        ART17[Art. 17: droit à l'oubli<br/>endpoint /admin/rgpd/delete<br/>person_uid]
        ART30[Art. 30: registre traitement<br/>via sources_de_verite JSONB]
        ART32[Art. 32: sécurité<br/>JWT + TLS Caddy + RLS Postgres]
    end

    subgraph PURGE["Purge auto (TODO)"]
        PURGE_24M[Purge audit > 24 mois]
        PURGE_INACTIF[Purge dirigeants_360 inactifs]
    end

    SOURCES_AUDIT --> ART30
    RGPD --> PURGE
```

---

## 📚 Comment utiliser ces diagrammes

**GitHub** : rendu natif dans `.md` (auto, pas de plugin).

**Confluence** : utiliser la macro `Mermaid Diagrams for Confluence` ou copier le code dans un bloc code `mermaid`.

**Notion** : copier le code dans un bloc `code` avec language `mermaid`.

**VS Code** : extension `Markdown Preview Mermaid Support` (nom commun `bierner.markdown-mermaid`).

**Édition** : éditer le `.md` avec preview live via [mermaid.live](https://mermaid.live/) pour valider la syntaxe avant commit.

---

> Document tenu à jour à chaque évolution architecture majeure. Dernière maj : 29/04/2026 (commit `d623cd0` — pipeline 100% automatisé + diagrams Mermaid).

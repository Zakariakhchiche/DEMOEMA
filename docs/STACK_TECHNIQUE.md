# Stack Technique — EdRCF 6.0

## 1. Architecture actuelle

```
Frontend:  Next.js 14 + React + TypeScript + Tailwind CSS + react-force-graph-2d
Backend:   FastAPI + Python 3.11 + httpx (async) + Pydantic
Deploy:    Vercel (frontend + serverless backend)
Data:      Pappers MCP (a remplacer) + Google News RSS + Infogreffe Open Data
AI:        DeepSeek API (copilot)
```

## 2. Architecture cible

```
Frontend:  Next.js 14 + React + TypeScript + Tailwind CSS + react-force-graph-2d
Backend:   FastAPI + Python 3.11 + httpx (async) + Pydantic
           + data_sources.py (nouveau module unifie multi-API)
Deploy:    Vercel (frontend + serverless backend)
Data:      25 sources gratuites (voir ARCHITECTURE_DATA.md)
Graph:     Neo4j Community Edition (mandats croises dirigeants)
Cache:     Redis + fastapi-cache2 (cache reponses API)
AI:        DeepSeek API (copilot)
OSINT:     holehe + maigret + sherlock (enrichissement dirigeants)
```

## 3. Librairies Python recommandees

### Donnees entreprise

| Librairie | Version | Usage |
|-----------|---------|-------|
| pynsee | 0.2.5 | INSEE SIRENE API (officiel InseeFrLab) |
| httpx | 0.28+ | Client HTTP async (deja utilise) |
| email-validator | 2.3+ | Validation email avec DNS MX |

### Graphe & Reseau

| Librairie | Version | Usage |
|-----------|---------|-------|
| networkx | 3.6+ | Analyse graphe dirigeants en memoire |
| neo4j | 6.1+ | Driver Neo4j (graphe persistant) |
| neomodel | 6.1+ | OGM Neo4j (classes Person, Company, Mandate) |
| pyvis | 0.3+ | Visualisation reseau HTML interactive |
| followthemoney | 4.8+ | Modele entite investigation (standard OpenSanctions) |

### OSINT

| Librairie | Version | Usage |
|-----------|---------|-------|
| holehe | 1.61 | Verifier email sur 120+ sites |
| maigret | 0.6+ | Dossier personne par username (3000+ sites) |
| sherlock-project | 0.16+ | Recherche username (400+ reseaux sociaux) |

### Cache & Performance

| Librairie | Version | Usage |
|-----------|---------|-------|
| fastapi-cache2 | 0.2+ | Cache decorator pour endpoints FastAPI |
| redis | via fastapi-cache2 | Backend cache |

## 4. MCP Servers disponibles

### Officiels / Matures

| Serveur | URL | Donnees | Auth |
|---------|-----|---------|------|
| datagouv-mcp | github.com/datagouv/datagouv-mcp | 74K datasets data.gouv.fr | Aucune |
| Instance publique | mcp.data.gouv.fr/mcp | Idem | Aucune |

### Communautaires

| Serveur | URL | Donnees |
|---------|-----|---------|
| mcp-insee-entreprises | github.com/DavidScanu/mcp-insee-entreprises | SIRENE par SIREN/SIRET |
| mcp-gouv-fr | github.com/gghez/mcp-gouv-fr | SIREN/SIRET lookups |
| Firmia | github.com/bacoco/Firmia | Multi-API entreprise FR |
| mcp-recherche-entreprise | github.com/thomas-servais/mcp-recherche-entreprise | Recherche entreprises |

### Gap identifie

Aucun MCP server n'existe pour : INPI RNE, BODACC, BALO, BOAMP, Gels des Avoirs,
HATVP, DVF, Judilibre. C'est une opportunite pour EdRCF de construire et
potentiellement open-sourcer un MCP unifie.

## 5. Projets similaires (veille concurrentielle)

### Tier 1 — Tres similaires

| Projet | Stars | Stack | Similarite |
|--------|-------|-------|------------|
| Tawiza | 2 | FastAPI + Next.js + Ollama | Intelligence territoriale FR, meme stack |
| Signaux Faibles | 6 | Python ML + Go + Vue.js | Prediction defaillance (startup d'Etat) |
| Annuaire des Entreprises | 88 | Next.js + FastAPI + Elasticsearch | Reference data layer entreprise FR |
| CorpRecon | 0 | Python | OSINT cartographie mandats FR |

### Tier 2 — Partiellement similaires

| Projet | Stars | Description |
|--------|-------|-------------|
| Company Research Agent | 1.7K | Multi-agent AI due diligence (LangGraph) |
| Aleph (OCCRP) | 2.3K | Plateforme investigation, graphes entites |
| Twenty CRM | 44K | CRM open-source, pipeline deals (FR) |
| datagouv-mcp | 1.3K | MCP officiel data.gouv.fr |
| OpenSanctions | 712 | Base sanctions internationale |

### Conclusion

EdRCF est unique : aucun projet open-source ne combine intelligence entreprise FR
+ pipeline M&A + signaux + graphes dirigeants + copilot AI dans une seule plateforme.

## 6. Cout total de la stack

| Composant | Cout mensuel |
|-----------|-------------|
| Sources donnees (25 APIs) | 0 EUR (tout gratuit) |
| Neo4j Community | 0 EUR |
| Redis (local ou free tier) | 0 EUR |
| Vercel (deploy) | 0 EUR (free tier) |
| Dropcontact (email enrichment) | ~24 EUR |
| DeepSeek API (copilot) | ~10 EUR |
| **TOTAL** | **~34 EUR/mois** |

Optionnel :
- Kaspr (telephone direct) : +49 EUR/mois
- LinkedIn Sales Navigator : +99 EUR/mois
- Hunter.io (email) : +49 EUR/mois

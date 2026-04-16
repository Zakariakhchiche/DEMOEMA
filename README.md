# EdRCF 6.0 — AI Origination Intelligence

Plateforme d'intelligence M&A pour l'origination de cibles d'acquisition.
Backend FastAPI + Frontend Next.js, deploye sur Vercel.

## Architecture technique

```
frontend/          Next.js 14 (React, TypeScript, Tailwind CSS)
backend/           FastAPI (Python 3.11+, httpx async)
docs/              Documentation strategie data & signaux M&A
```

## Problematique

Le projet utilisait Pappers MCP comme source unique de donnees entreprise.
Pappers est devenu payant. Ce document decrit la strategie de migration
vers des sources 100% gratuites et l'enrichissement avec 16 couches de donnees.

## Documentation complete

| Document | Contenu |
|----------|---------|
| [docs/ARCHITECTURE_DATA.md](docs/ARCHITECTURE_DATA.md) | Architecture data complete, 25 sources gratuites, mapping Pappers |
| [docs/SIGNAUX_MA.md](docs/SIGNAUX_MA.md) | 103 signaux M&A, scoring sur 100 points, 12 dimensions |
| [docs/OSINT_DIRIGEANTS.md](docs/OSINT_DIRIGEANTS.md) | Cartographie relationnelle, OSINT, cadre RGPD |
| [docs/STACK_TECHNIQUE.md](docs/STACK_TECHNIQUE.md) | Librairies Python, MCP servers, projets similaires |

## Demarrage rapide

```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## Liens utiles

- API Recherche Entreprises : https://recherche-entreprises.api.gouv.fr
- INPI RNE : https://data.inpi.fr
- API BODACC : https://bodacc-datadila.opendatasoft.com
- INSEE SIRENE : https://portail-api.insee.fr
- GLEIF : https://api.gleif.org

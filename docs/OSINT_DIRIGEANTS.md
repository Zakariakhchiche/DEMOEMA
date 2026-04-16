# OSINT Dirigeants — Cartographie relationnelle

## 1. Objectif

Construire un profil complet de chaque dirigeant cible pour savoir :
- Qui il est (identite, age, mandats, parcours)
- Comment le contacter (email, telephone, adresse)
- Qui le connait (connexions communes, mandats croises)
- Ou le rencontrer (evenements, salons, conferences)

## 2. Sources de donnees par besoin

### 2.1 Identite & Mandats (GRATUIT)

| Donnee | Source | Methode |
|--------|--------|---------|
| Nom, role, age | INPI RNE | API /companies/{siren} -> representants |
| Tous ses mandats | INPI RNE bulk + cross-referencing | Telechargement SFTP + graph |
| Beneficiaires effectifs | INPI RNE | Acces restreint (interet legitime) |
| Historique mandats | API Recherche Entreprises | GET /search?q={nom}&type=dirigeant |

### 2.2 Contact (email, telephone)

| Donnee | Source | Cout | RGPD |
|--------|--------|------|------|
| Email pro (pattern) | Calcul {prenom}.{nom}@domaine.fr | Gratuit | OK |
| Email pro (verifie) | Dropcontact | ~24 EUR/mois | Conforme (FR) |
| Email pro (domaine) | Hunter.io | Freemium (25/mois gratuit) | Partiel |
| Telephone direct | Kaspr | ~49 EUR/mois | Partiel |
| Telephone entreprise | Annuaire Entreprises (gouv) | Gratuit | OK |
| Verification email | email-validator (Python) | Gratuit | OK |
| Verification SMTP | verify-email (Python) | Gratuit | OK |

Strategie email gratuite :
1. Trouver le domaine de l'entreprise (site web)
2. Appliquer le pattern le plus courant : {prenom}.{nom}@domaine.fr
3. Verifier avec email-validator (DNS MX check)

### 2.3 Cartographie relationnelle (GRATUIT)

#### Mandats croises (methode principale)

La methode la plus puissante pour trouver qui connait qui :

```
Si Dirigeant A et Dirigeant B siegent dans la meme societe -> ils se connaissent
Si A connait C et C connait B -> A et B sont a 2 degres de separation
```

Implementation :
1. Telecharger les donnees INPI RNE (dirigeants de toutes les entreprises FR)
2. Construire un graphe biparti : Personnes <-> Entreprises
3. Calculer les connexions communes (mandats partages)

Stack recommandee :
- Neo4j Community Edition (gratuit) pour le stockage graphe
- NetworkX (Python) pour l'analyse
- react-force-graph-2d (deja dans le frontend) pour la visualisation

Schema Neo4j :
```cypher
(:Person {name, birthDate})-[:MANDATE {role, startDate, endDate}]->(:Company {siren, name})
```

Requete connexions communes :
```cypher
MATCH (a:Person {name: "Cible"})-[:MANDATE]->(c:Company)<-[:MANDATE]-(b:Person)
WHERE a <> b
RETURN b.name, c.name, count(c) AS mandats_partages
ORDER BY mandats_partages DESC
```

Requete 2 degres de separation :
```cypher
MATCH (moi:Person {name: "Moi"})-[:MANDATE]->(:Company)<-[:MANDATE]-(pont:Person)
      -[:MANDATE]->(:Company)<-[:MANDATE]-(cible:Person {name: "Cible"})
WHERE moi <> pont AND pont <> cible AND moi <> cible
RETURN DISTINCT pont.name AS intermediaire
```

#### Autres sources de connexions

| Type de lien | Source | Cout | Fiabilite |
|--------------|--------|------|-----------|
| Co-actionnariat | INPI beneficiaires effectifs | Gratuit | Haute |
| Meme adresse siege | API Recherche Entreprises | Gratuit | Moyenne |
| Meme secteur + region | API Recherche Entreprises | Gratuit | Faible |
| Lobbying commun | HATVP registre | Gratuit | Moyenne |
| Liens familiaux | INPI RNE (meme nom + meme societe) | Gratuit | Moyenne |

### 2.4 Ou le rencontrer

| Source | Methode | Cout |
|--------|---------|------|
| Google Custom Search | "Prenom Nom" speaker OR intervenant OR conference | Gratuit (100 req/jour) |
| Eventbrite | API recherche evenements par secteur/region | Gratuit |
| Salons professionnels | salons-online.com, listes exposants | Gratuit |
| BPI France evenements | evenements.bpifrance.fr (speakers publics) | Gratuit |
| YouTube | site:youtube.com "Prenom Nom" interview | Gratuit |

### 2.5 Profil digital

| Outil | Usage | Cout |
|-------|-------|------|
| LinkedIn Sales Navigator | Profil pro, parcours, connexions | 99 EUR/mois |
| Google Custom Search API | Recherche structuree multi-sites | Gratuit (100/jour) |
| Sherlock (Python) | Recherche username sur 400+ reseaux | Gratuit |
| Maigret (Python) | Dossier complet par username (3000+ sites) | Gratuit |
| Holehe (Python) | Verifier si email inscrit sur 120+ sites | Gratuit |

### 2.6 Patrimoine immobilier

| Source | Donnee | Cout |
|--------|--------|------|
| DVF | Transactions immobilieres des SCI du dirigeant | Gratuit |
| Cadastre | Parcelles (personnes morales uniquement) | Gratuit |
| SPF (Service Publicite Fonciere) | Propriete immobiliere (demande formelle) | ~12-15 EUR/req |

Methode : Identifier les SCI dont le dirigeant est gerant (INPI RNE),
puis chercher les transactions DVF de ces SCI.

## 3. Cadre juridique RGPD

### Ce qui est LEGAL pour la prospection B2B en France

Base legale : interet legitime (Art. 6(1)(f) RGPD)
Ref CNIL : prospection B2B sans consentement prealable si :

1. Le message concerne la fonction professionnelle du destinataire
2. Le destinataire peut facilement se desinscrire
3. L'expediteur s'identifie clairement

### Obligations

- Documenter l'evaluation d'interet legitime (LIA)
- Informer au premier contact (Art. 14 RGPD) : identite, donnees detenues, source, droits
- Respecter le opt-out immediatement (30 jours max)
- Minimisation des donnees : ne collecter que le necessaire
- Retention max 3 ans d'inactivite (recommandation CNIL)
- Tenir un registre de traitement (Art. 30 RGPD)

### Ce qui est INTERDIT

- Scraper des donnees personnelles (non professionnelles) sans consentement
- Utiliser des emails personnels (gmail, orange.fr) pour demarchage B2B
- Appeler des numeros personnels inscrits sur Bloctel
- Profiler pour des finalites non professionnelles

### Architecture RGPD recommandee

- Liste de suppression (opt-outs) persistante
- Log source + date de chaque donnee collectee
- Expiration automatique (3 ans inactivite)
- Notice vie privee dans chaque premier contact
- Designation d'un referent RGPD

## 4. Stack technique recommandee

### Librairies Python

| Lib | PyPI | Usage | Stars |
|-----|------|-------|-------|
| pynsee | pip install pynsee[full] | INSEE SIRENE (officiel InseeFrLab) | 88 |
| networkx | pip install networkx | Analyse graphe dirigeants | 16.8K |
| neo4j | pip install neo4j | Driver Neo4j pour graphe persistant | 1K |
| pyvis | pip install pyvis | Visualisation reseau interactive | 1.2K |
| email-validator | pip install email-validator | Validation email (DNS MX) | 1.4K |
| holehe | pip install holehe | Email OSINT (120+ sites) | 10.7K |
| maigret | pip install maigret | Dossier personne (3000+ sites) | 19.5K |
| sherlock-project | pip install sherlock-project | Recherche username (400+ reseaux) | 81.2K |
| followthemoney | pip install followthemoney | Modele entite anti-corruption | 53 |
| httpx | pip install httpx | Client HTTP async pour FastAPI | 15.2K |
| fastapi-cache2 | pip install fastapi-cache2 | Cache Redis pour endpoints | 1.9K |

### MCP Servers existants

| MCP | GitHub | Usage |
|-----|--------|-------|
| datagouv-mcp | datagouv/datagouv-mcp (1.3K stars) | Officiel data.gouv.fr |
| mcp-insee-entreprises | DavidScanu/mcp-insee-entreprises | SIRENE lookup |
| Firmia | bacoco/Firmia | French company intelligence unifie |

### Projets similaires sur GitHub

| Projet | Stars | Description |
|--------|-------|-------------|
| Tawiza | 2 | Intelligence territoriale FR (FastAPI + Next.js, meme stack) |
| Signaux Faibles | 6 | Prediction defaillance entreprise (startup d'Etat) |
| Annuaire des Entreprises | 88 | Plateforme officielle recherche entreprises FR |
| CorpRecon | 0 | OSINT cartographie mandats entreprises FR |
| Company Research Agent | 1.7K | Multi-agent AI due diligence (US) |
| Aleph (OCCRP) | 2.3K | Plateforme investigation, graphes entites |
| Twenty CRM | 44K | CRM open-source (alternative Salesforce, FR) |

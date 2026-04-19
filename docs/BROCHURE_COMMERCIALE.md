# DEMOEMA — Brochure commerciale

> **Document de présentation destiné aux prospects (boutiques M&A, fonds PE, banques d'affaires).**
>
> Objectif : susciter l'intérêt suffisant pour obtenir un rendez-vous ou une inscription bêta.
>
> Version : 1.1 — Avril 2026
>
> Ce document est à convertir en PDF mis en page (Figma / Canva / InDesign) avant diffusion. Les sections "À personnaliser" doivent être remplies avant envoi à un prospect.
>
> ---
>
> 🚀 **MVP EN PRODUCTION — 7 modules live, 300+ cibles M&A déjà en base**
>
> DEMOEMA (EdRCF 6.0) est **déjà en production sur Vercel** depuis mars 2026. Les modules principaux sont opérationnels. Le développement actif continue pour le scaling (sweep INSEE 16M → 50 000 cibles) et les killer features (Alertes pré-cession, Who advises whom).
>
> **Signalétique utilisée** :
> - ✅ **En production aujourd'hui**
> - 🔧 **En développement actif** (Q2-Q3 2026)
> - ⏳ **Roadmap Y2 2027**
>
> La roadmap produit détaillée est disponible sur demande.

---

## 📌 Mode d'emploi

**Quand l'utiliser**
- Envoi en PDF après un premier échange LinkedIn ou email
- Remis en main propre lors d'une prospection terrain (salon CFNews, France Invest)
- Lien inclus dans l'email de re-contact des 2 boutiques existantes

**Durée de lecture cible** : 7-10 minutes

**Call-to-action final** : "Demandez votre accès bêta gratuit 6 mois" OU "Réservez une démo 30 min"

---

# PARTIE 1 — LE POSITIONNEMENT

## DEMOEMA en une phrase

> **La plateforme d'intelligence M&A pensée pour les boutiques qui ne peuvent pas se payer Bureau van Dijk et qui trouvent Pappers insuffisant.**

## En 3 phrases

1. **Nous connectons un associé M&A au bon décisionnaire au bon moment.**
2. Nous agrégeons 140 sources publiques françaises et européennes en une seule fiche intelligente et prédictive.
3. Nous remplaçons 5 outils disparates (Pappers + LinkedIn + Infogreffe + Excel + Capital IQ) par **une seule interface**, à un prix accessible aux boutiques mid-market.

## Pour qui ?

- ✅ **Boutiques M&A françaises** (5-50 personnes, 5-30 deals/an)
- ✅ **Fonds PE mid-market** (50-500M€ AUM)
- ✅ **Directions M&A de corporates**
- ✅ **Conseil en transmission / restructuring**
- ❌ Pas pour les banques d'affaires tier-1 (ils ont déjà Bureau van Dijk)
- ❌ Pas pour les particuliers (c'est un outil B2B pro)

---

# PARTIE 2 — LE CONSTAT

## 3 heures perdues chaque jour, pour chaque associé

Un associé M&A français passe en moyenne **3 heures par jour** à :
- Ouvrir Pappers pour vérifier une fiche SIREN
- Aller sur LinkedIn pour trouver le dirigeant
- Passer sur Infogreffe pour les actes officiels
- Fouiller la presse pour les signaux
- Recoupler tout ça dans un Excel

**Multiplié par 10 collaborateurs dans une boutique = 30 heures/jour perdues.**

À un tarif chargé moyen de **150€/heure**, c'est **4 500€/jour** ou **~1 M€/an** de coût caché par boutique de 10 personnes.

## Les outils actuels ont tous des trous

| Outil | Ce qu'il fait | Ce qu'il ne fait pas |
|---|---|---|
| **Pappers** | Fiches SIREN, recherche basique | Pas de graphe dirigeants, pas d'intelligence prédictive, pas d'historique advisors |
| **Infogreffe Pro** | Actes officiels, statuts | Pas de scoring, pas d'analyse |
| **LinkedIn Sales Nav** | Profils dirigeants | Pas de données financières, pas de structure capital |
| **Bureau van Dijk / Diane** | Profondeur historique | 15-50k€/user/an, UX des années 2000 |
| **Pitchbook / Capital IQ** | Deals + valorisations mondiales | 25-80k€/user/an, US-centric, aveugle sur l'ETI FR |
| **Excel + réseau** | Ce qui fait vraiment le métier | Ne scale pas, erreurs humaines, pas de mémoire collective |

## Le vrai pain, en une phrase

> *"Je ne cherche pas plus de données. Je cherche moins de bruit, le bon contact, et le bon moment."*
>
> — Verbatim d'un associé de boutique M&A parisienne, mars 2026

---

# PARTIE 3 — NOTRE SOLUTION

## Ce que DEMOEMA vous apporte

### ✅ Dashboard Intelligence M&A — **EN PRODUCTION**
- Métriques temps réel de votre pipeline M&A
- Filtres sectoriels multi-critères
- Vue agrégée : cibles par score, dimension, sévérité signal
- Disponible dès aujourd'hui sur Vercel

### ✅ Intelligence Targets — **EN PRODUCTION (300+ cibles)**
- **200-300 cibles M&A qualifiées** par scoring propriétaire
- Export CSV 19 colonnes (entité, SIREN, secteur, région, CA, EBITDA, score, priorité, fenêtre M&A, dirigeant, relation…)
- Import NAF on-demand (62 profils sectoriels)
- Scoring /100 basé sur 103 signaux M&A propriétaires

### ✅ Feed Signaux M&A — **EN PRODUCTION (103 signaux)**
- **103 signaux M&A propriétaires** scorés
- Filtres par **5 dimensions** : Patrimoniaux / Stratégiques / Financiers / Gouvernance / Marché
- Filtres par sévérité : critique / majeur / mineur
- Rapport .txt exportable

### ✅ Graphe Réseau Intelligence — **EN PRODUCTION**
- Cartographie **ForceGraph2D** interactive (glassmorphism)
- Nœuds : cibles M&A (vert, score) + dirigeants (amber) + équipe EDR (indigo) + filiales (violet)
- Détection automatique **mandats croisés** (orange pulsant)
- Alertes visuelles : dirigeants 60+ (rouge), holding (double ring)
- 15M+ personnes physiques, 30M+ mandats

### ✅ Copilot IA — **EN PRODUCTION (streaming SSE)**
- Assistant conversationnel **Claude** en streaming SSE word-by-word
- Recherche SIREN intelligente
- **PDF report** exportable
- Multi-turn avec contexte persistant
- Fallback `/api/copilot/query` si streaming indisponible

### ✅ PWA Mobile — **EN PRODUCTION**
- Application installable iOS/Android
- Manifest + Service Worker + offline fallback
- **Notifications push** natives
- Splash screen Lottie radar
- Check périodique signaux (5 min)

### 🔧 Sweep INSEE 16M — **EN DÉVELOPPEMENT (Q2-Q3 2026)**
Objectif : passer de 300 à **50 000 cibles qualifiées**.
- `sirene_bulk.py` (committé 17/04) : pipeline SIRENE 16M entités en 20 min
- Filtres PME/ETI actives sur 62 NAF cibles
- Endpoints `/api/admin/rebuild-index` + `/api/admin/enrich-batch`
- Schéma Supabase `sirene_index` avec scoring /100 pré-API

### 🔧 Killer features Y1-Y2 — **EN DÉVELOPPEMENT**

#### ⭐ Alertes signaux pré-cession (Q3 2026)
Détection proactive : changement mandataires, nomination CFO 55+, délégations AG, dirigeant vers PE.
Email hebdo "3 entreprises de votre secteur montrent des signaux cette semaine".

#### ⭐ Who advises whom (Q4 2026)
Historique 3 000+ deals FR indexés 2020-2026 via NLP sur sites boutiques M&A + communiqués AMF.
"Cette cible a été conseillée par Cabinet X en 2023 → appelle X".

---

### Détails par module (ci-dessous)

### ✅ **EN PROD** — Fiche entreprise unifiée à 360°

Pour **5 millions d'entreprises françaises** actives, une fiche unique qui agrège progressivement :

- **Identité** : SIREN, dénominations, historique, sièges
- **Finance** : CA, EBITDA, ratios, évolution sur 5 ans (via INPI comptes annuels)
- **Gouvernance** : dirigeants, mandataires, ancienneté, réseau de mandats
- **Actionnariat** : structure capital, groupe (RBE sous réserve évolution CJUE)
- **Juridique** : procédures collectives, BODACC, contentieux (Judilibre)
- **Marché** : marchés publics gagnés (DECP), brevets (INPI), recherche
- **Digital** : domaine, stack web détectée, présence online
- **Immobilier** : implantations physiques, DPE, valeur des actifs
- **Presse** : derniers articles, mentions, signaux
- **Sanctions** : vérification OFAC, UE, ONU, DGTrésor

**Chaque information affichée est sourcée** avec lien vers la donnée d'origine.

*Livraison progressive : couches identité + finance + juridique + sanctions dès Q3 2026. Couches digital + immobilier + presse Q4 2026.*

### 2️⃣ 🏗️ **Q3 2026** — Le graphe dirigeants visuel

Un **graphe interactif** des dirigeants et leurs mandats croisés :
- Visualisation des liens directs et indirects (jusqu'à 3 degrés)
- **5M+ personnes physiques, 15M+ mandats** (données INSEE + INPI RNE)
- Détection automatique des clusters d'influence
- Identification des "golden connectors" (dirigeants qui lient plusieurs écosystèmes)

**Cas d'usage** : vous identifiez une cible. En 3 clics, vous voyez **quels dirigeants la connaissent personnellement** et **quel acquéreur naturel** partage des administrateurs avec elle.

*Livraison : V0 graphe simple Q3 2026 (table Postgres + viz force-graph). Graphe Neo4j avancé Y3 (2028).*

### 3️⃣ 🏗️ **Q3 2026** — ⭐ Alertes signaux pré-cession (killer feature #1)

DEMOEMA monitore en permanence les signaux publics annonciateurs d'une cession à venir :

- 🔔 **Changement de mandataires sociaux** (BODACC) — signal prédictif fort de cession sous 12-18 mois
- 🔔 **Nomination d'un CFO externe** à un dirigeant 55+ sans successeur → préparation transmission
- 🔔 **Recrutement d'un Deputy CEO / COO** après 2 ans de stabilité → préparation post-cession
- 🔔 **Nouvelle délégation de pouvoir en AG** → préparation gouvernance deal
- 🔔 **Dirigeant qui rejoint un fonds PE** comme operating partner → signal pré-deal
- 🔔 **Modification clause agrément statuts** → préparation entrée capital tiers

Vous recevez chaque lundi matin **"3 entreprises de votre secteur montrent des signaux pré-cession cette semaine"**.

*Détection rule-based sur BODACC + INPI RNE. Pas de scoring IA opaque : chaque alerte est explicable et sourcée.*

### 4️⃣ 🔨 **Q4 2026** — ⭐ Who advises whom — historique des advisors (killer feature #2)

Pour chaque deal M&A annoncé publiquement (CFNews, Les Échos, La Tribune, communiqués AMF), nous extrayons et structurons :

- La cible et l'acquéreur
- **Les advisors côté vendeur** (boutiques M&A, banques d'affaires)
- **Les advisors côté acheteur**
- La valorisation (quand annoncée publiquement)
- Les secteurs, multiples si publiés

**Cas d'usage** : vous regardez une cible → vous voyez "Cette entreprise a été conseillée par [Cabinet X] lors de son LBO 2022" → vous appelez X pour une intro sur le prochain deal.

**Objectif V1 (décembre 2026)** : 3 000+ deals FR indexés (période 2020-2026).
**Objectif V2 (fin 2027)** : 10 000+ deals FR + extension UK/DE.

*NLP : CamemBERT fine-tuné sur 500 communiqués labellisés — pas de LLM hallucinant, extraction déterministe.*

### 5️⃣ ⏳ **Y2 2027** — Le copilot IA (assistant conversationnel)

Un copilot spécialisé M&A, qui saura :
- Générer un **teaser de cible** en 30 secondes
- Produire une **buyer list qualifiée** (10 acquéreurs potentiels avec rationale)
- Résumer 10 articles presse en 1 paragraphe factuel
- Proposer un **premier diagnostic financier** sur comptes déposés

**Transparence IA intégrée** :
- Chaque réponse cite ses sources
- Mode "sans IA" disponible si vous préférez l'interface classique
- Audit log complet pour traçabilité
- Conforme Règlement UE 2024/1689 (AI Act)
- Pas de fine-tuning = statut déployeur (pas fournisseur GPAI)

*Livraison : copilot démo interne Q2 2027, public Q3 2027 sur Pro et Enterprise.*

### 6️⃣ 🏗️ **Q3-Q4 2026** — Les exports qui matchent votre workflow

- 🏗️ **Q3** : **Excel natif** avec templates M&A (Teaser, Buyer list, Longlist, DD brief) — 4 templates à la sortie, 2 de plus Q1 2027
- 🏗️ **Q3** : **PDF brandé** exportable en 1 clic
- 🏗️ **Q3** : **Export CSV compatible Affinity** pour import dans votre CRM deal
- 🔨 **Q4** : **API Affinity bidirectionnelle** (push/pull)
- ⏳ **Y2** : **API REST Enterprise** complète (GraphQL, webhooks)
- ⏳ **Y2 Q1** : **Extension Chrome** pour enrichir LinkedIn et pages entreprises

---

# PARTIE 4 — 5 CAS D'USAGE CONCRETS

## Use case 1 — Sourcing cible

**Scénario** : un client vous demande "trouvez-moi 5 cibles dans le secteur X, chiffre d'affaires 10-30 M€, en région Y".

**Avant DEMOEMA**
- Recherche Pappers par NAF + CA : 2h
- Filtrage manuel sur Excel : 1h
- Qualification individuelle (chaque fiche) : 3h
- Recherche dirigeants LinkedIn : 1h
- **Total : ~7h**

**Avec DEMOEMA**
- Recherche multi-critères avec scoring automatique : 15 min
- Liste triée avec 10 attributs par cible : 0 min (affichage auto)
- Fiches enrichies pré-qualifiées : 30 min
- Dirigeants identifiés + contacts proposés : 15 min
- **Total : ~1h**

**Gain : 6 heures par sourcing.**

## Use case 2 — Qualification d'une cible

**Scénario** : un intermédiaire vous propose d'acheter une société. Avant de pitcher votre client acquéreur, il faut qualifier.

**Avant DEMOEMA**
- Vérifier SIREN, statuts, KBIS (Infogreffe) : 30 min
- Lire comptes déposés (INPI) : 45 min
- Vérifier sanctions / procédures : 20 min
- Trouver dirigeants et leur réseau : 1h
- Benchmark concurrentiel : 1h
- **Total : ~3h30**

**Avec DEMOEMA**
- Ouvrir la fiche 360° : 5 min
- Consulter le graphe dirigeants : 10 min
- Voir les comparables sectoriels : 5 min
- Générer le teaser IA : 2 min
- **Total : ~25 min**

**Gain : 3 heures par qualification.**

## Use case 3 — Buyer list pour une cible vendue

**Scénario** : vous avez un mandat vendeur. Il vous faut 30 acquéreurs potentiels qualifiés.

**Avant DEMOEMA**
- Brainstorm équipe : 2h
- Recherche manuelle des candidats : 4h
- Vérification capacité financière : 2h
- Identification des contacts décisionnaires : 3h
- **Total : ~11h**

**Avec DEMOEMA**
- Entrer la cible dans le copilot : 1 min
- Obtenir buyer list auto (30 candidats) : immédiat
- Enrichir par capacité financière : automatique
- Vérifier les contacts (Who advises whom) : 30 min
- **Total : ~45 min**

**Gain : 10 heures par mandat vendeur.**

## Use case 4 — Veille sectorielle proactive

**Scénario** : vous couvrez le secteur agro-alimentaire. Vous voulez être le premier sur les deals qui bougent.

**Avant DEMOEMA**
- Veille presse manuelle hebdo : 3h/semaine
- Suivi BODACC manuel : 2h/semaine
- Recherche mandataires sociaux nouveaux : 2h/semaine
- **Total : ~7h/semaine = 350h/an**

**Avec DEMOEMA**
- Alertes email quotidiennes ciblées secteur
- Dashboard "mouvements de la semaine"
- Signaux pré-cession automatiques
- **Total : 30 min/semaine = 25h/an**

**Gain : 325 heures par an pour le suivi sectoriel.**

## Use case 5 — Due diligence express

**Scénario** : vous devez pitcher un client sur une cible en 48h avant concurrents.

**Avant DEMOEMA**
- Collecte data multi-sources : 1 journée
- Analyse comptes : 1 journée
- Contentieux / sanctions / procédures : 0.5 journée
- Synthèse DD brief : 0.5 journée
- **Total : ~3 jours**

**Avec DEMOEMA**
- Rapport DD auto-généré : 2 min
- Validation humaine et enrichissement : 2h
- Analyse approfondie par le copilot : 1h
- Mise en forme finale : 1h
- **Total : ~4h**

**Gain : 2 jours complets de travail économisés.**

---

# PARTIE 5 — POURQUOI NOUS (vs concurrence)

## Matrice comparative

| Critère | Pappers Pro | Société.com | Diane/BvD | Pitchbook | **DEMOEMA (roadmap)** |
|---|---|---|---|---|---|
| **Prix /user/mois** | 39€ | 39€ | 1 250€ (15k/an) | 2 500€ (30k/an) | **199€** |
| **Couverture FR** | 100% | 100% | 100% | 60% | **100%** |
| **Graphe dirigeants** | ❌ | ❌ | ✅ | ⚠️ partiel | 🏗️ Q3 2026 |
| **Signaux pré-cession** | ❌ | ❌ | ❌ | ❌ | ⭐ 🏗️ Q3 2026 |
| **Who advises whom** | ❌ | ❌ | ⚠️ partiel | ✅ | ⭐ 🔨 Q4 2026 |
| **Copilot IA M&A** | ⚠️ Q&A basique | ⚠️ basique | ❌ | ❌ | ⏳ Y2 2027 |
| **Scoring prédictif** | ❌ | ❌ | ❌ | ⚠️ rating | ⏳ Y2 2027 |
| **UX moderne** | ✅ | ⚠️ | ❌ | ⚠️ | ✅ dès V1 |
| **API moderne** | ✅ | ❌ | ❌ SOAP | ⚠️ | ✅ REST Y1, GraphQL Y2 |
| **Souveraineté data** | FR | FR | UK (Moody's) | US | **FR strict** ✅ |
| **Conformité AI Act** | ⚠️ | ⚠️ | ❌ | ❌ | ✅ natif dès Q3 2026 |

*Calendrier de livraison DEMOEMA : 🏗️ Q3 2026 · 🔨 Q4 2026 · ⏳ Y2 2027. Voir programme bêta-testeur.*

## Nos 3 promesses différenciantes

### 🎯 Promesse 1 — 10× moins cher que Bureau van Dijk, à qualité équivalente sur le mid-market

- Diane/BvD : 15-50k€/user/an minimum, contrats annuels rigides
- DEMOEMA Enterprise : à partir de **15k€/an** (toute l'équipe, pas par user)
- Soit **5 à 10× moins cher** pour la même profondeur sur les entreprises FR mid-market

### 🎯 Promesse 2 — 5× plus puissant que Pappers sur le M&A

- Pappers Pro : lookup statique, pas de graphe visuel, pas de scoring, pas d'alertes
- DEMOEMA Pro : **tout ça + copilot + signaux pré-cession + historique advisors**
- Pour **5× le prix** (199€ vs 39€) mais pour un métier (M&A) qui facture 150-300€/h

### 🎯 Promesse 3 — 100% souverain + AI Act natif

- Hébergement : Scaleway Paris (pas AWS US)
- Conforme RGPD dès le premier user
- Conforme Règlement IA UE 2024/1689 (transparence, audit log, mode sans IA)
- Pas de fine-tuning = pas de risque "GPAI provider"
- CGU intègrent une clause explicite "pas de décision automatisée sur personne physique"

---

# PARTIE 6 — NOS DONNÉES

## 140 sources publiques agrégées (catalogue)

> 🏗️ **Ingestion progressive** : 15 sources prioritaires livrées Q3 2026, +15 Q4 2026, le reste progressivement sur 2027-2028 selon les retours clients.

### Entreprises et identités (8 sources)
- API Recherche Entreprises · INSEE SIRENE · INPI RNE · annuaire-entreprises.data.gouv.fr · RNA associations · JOAFE · data.gouv.fr SIRENE géolocalisé

### Identifiants internationaux (7 sources)
- GLEIF · OpenCorporates · Wikidata · ROR · GRID · OpenPermid · OpenSanctions

### Finances et comptes (6 sources)
- INPI comptes annuels · ESANE INSEE · Banque de France Webstat · ANC · data.economie.gouv.fr

### Juridique et contentieux (7 sources)
- Judilibre · Légifrance · CNIL sanctions · Autorité de la Concurrence · DGCCRF · Conseil d'État · CERT-FR

### Propriété intellectuelle (12 sources)
- INPI Brevets · INPI Marques · EPO · EUIPO · WIPO · MESR · CIR/CII · Scanr · HAL · OpenAlex · CrossRef · ORCID

### Marchés publics et aides (12 sources)
- BOAMP · DECP · TED · aides-entreprises · France 2030 · FEDER · FEADER · FSE+ · ASP Telepac · Bpifrance · i-Lab

### ESG / environnement (11 sources)
- ADEME Bilans GES · Base Carbone · EU ETS · BASOL · BASIAS · ICPE · GEOD'AIR · Agence de l'Eau · Agribalyse · ADEME Diag Eco-Flux · RGE

### Presse et signaux (9 sources)
- GDELT · Les Échos · La Tribune · Usine Nouvelle · CFNews · Google News · Wikipedia · Wikidata

### Immobilier et actifs (7 sources)
- DVF · API Cadastre · BAN · BDNB · ADEME DPE · IGN BD TOPO · data.gouv RPG

### Sanctions / compliance (7 sources)
- DGTrésor gels · EU Sanctions · OFAC · UK HMT · AMF listes noires · ACPR REGAFI · Bloctel

### Emploi et RH (7 sources)
- France Travail · DARES · Welcome to the Jungle · Indeed · APEC · OPCO · DSN agrégée

### Sectoriel (10 sources)
- ANSM · BDPM · OpenMedic · RPPS · Observatoire ESS · CGSCOP · Agreste · DREAL transporteurs · ORIAS · AMF GECO

### Web et digital (7 sources)
- Certificate Transparency · Wayback Machine · Common Crawl · RDAP/WHOIS · GitHub public · BuiltWith · SecurityTrails

### International (7 sources)
- BRIS · EBR · Eurostat · OECD · World Bank · Comtrade UN · Douanes FR

**Total : 140 sources activement ingérées**, fraîcheur variable (temps réel à mensuel selon source).

## Garanties qualité

- ✅ Chaque donnée affichée cite sa source d'origine
- ✅ Badge de fiabilité par champ (déclaré / estimé / consolidé)
- ✅ Fraîcheur indiquée (J, J+1, J+7, J+30 selon source)
- ✅ Procédure de correction : si une donnée est erronée, correction sous 48h après signalement
- ✅ Droit à l'oubli : processus RGPD formalisé pour les personnes physiques

---

# PARTIE 7 — SÉCURITÉ & CONFORMITÉ

## RGPD natif
- DPO contracté dès le lancement (cabinet spécialisé)
- DPIA (Analyse d'impact) complétée avant mise en production
- Registre des traitements documenté
- Procédure d'effacement sous 30 jours
- Base légale : intérêt légitime documenté + LIA (Legitimate Interest Assessment)

## Règlement IA (UE 2024/1689)
- Classification système : risque limité (art. 50)
- Transparence IA : chaque output est tagué "généré par IA"
- Audit log des interactions copilot
- Mode "sans IA" disponible pour usage sans interaction machine
- Pas de scoring de personnes physiques (seulement des entreprises)
- Pas de fine-tuning des LLM (statut déployeur, pas fournisseur GPAI)

## Sécurité technique
- ✅ Hébergement **Scaleway Paris** (souveraineté FR)
- ✅ Chiffrement **AES-256** at rest + **TLS 1.3** in transit
- ✅ **Authentification MFA** obligatoire sur Pro et Enterprise
- ✅ **Backups quotidiens** sur S3 Scaleway
- 🏗️ **Q4 2026** : Audit log immuable (traçabilité RGPD)
- ⏳ **Y2 2027** : SSO SAML disponible en Enterprise
- ⏳ **Y2 2027** : Réplication multi-AZ (single-AZ Y1)
- ⏳ **Y2 2027** : Pen-test annuel
- ⏳ **Q2 2028** : Certification SOC2 Type I
- ⏳ **Q2 2029** : Certification SOC2 Type II
- ⏳ **2029** : Certification ISO 27001

## Sources exclues par principe

Pour protéger légalement nos clients :
- ❌ **Pas de scraping LinkedIn** (CGU + jurisprudence)
- ❌ **Pas de scraping Glassdoor** (CGU)
- ❌ **Pas de Trustpilot / Google Reviews** (CGU interdisent usage commercial)
- ❌ **Pas de données de dirigeants hors mandats publics** (pas de profilage émotionnel)
- ❌ **Pas de reconnaissance faciale** (pratique interdite AI Act)

---

# PARTIE 8 — PRICING

## 4 plans + rapports à la carte

### 🔵 Free — Tester avant d'acheter
- **0 €/mois**
- 10 fiches entreprises/mois
- Recherche basique
- Pas de scoring, pas de copilot, pas d'export
- Pour : **tester, référencer un article**

### 🟢 Starter — Pour les indépendants
- **49 €/mois par user** (ou 490 €/an, 2 mois offerts)
- Fiches illimitées
- Scoring basique
- Exports CSV/PDF
- 100 alertes signaux/mois
- Pour : **conseillers solo, petits cabinets, analystes juniors**

### 🟠 Pro — Pour les boutiques M&A ⭐
- **199 €/mois par user** (ou 1 990 €/an)
- Tout Starter +
- ⭐ **Graphe dirigeants visuel**
- ⭐ **Alertes signaux pré-cession**
- ⭐ **Historique advisors (Who advises whom)**
- Copilot LLM (100 requêtes/mois)
- Export Excel avec templates M&A
- API limitée (1 000 calls/mois)
- Collaboration équipe (5 users min)
- Pour : **boutiques M&A, PE seed, family offices, conseil M&A**

### 🔴 Enterprise — Pour les banques et gros fonds
- **À partir de 15 k€/an** (dégressif selon nb users)
- Tout Pro +
- Copilot illimité
- API étendue (100k calls/mois)
- Permissions fines + RBAC + SSO SAML
- Audit log RGPD avancé
- Account manager dédié + SLA 99.5%
- Modules verticaux (santé, industrie, ESS)
- Pour : **banques d'affaires, fonds PE >100M€ AUM, directions M&A grands corp.**

## Rapports one-shot (sans abonnement)

Pour tester DEMOEMA sans engagement :

- 💼 **Rapport "Cible" complet** — **490 €**
  Fiche enrichie 360° d'une entreprise, livrée en 24h
- 💼 **Rapport "Cluster sectoriel"** — **1 490 €**
  Cartographie de 50 entreprises d'un secteur
- 💼 **Rapport "Buyer list qualifiée"** — **2 990 €**
  100 acquéreurs potentiels pour une cible donnée

## Comparaison rapide du coût

| Votre stack actuelle | DEMOEMA Pro |
|---|---|
| Pappers × 5 users = 245 €/mois | |
| LinkedIn Sales Nav × 5 = 400 €/mois | |
| Infogreffe Pro = 100 €/mois | |
| CFNews = 250 €/mois | |
| Capital IQ licence = 1 250 €/mois | |
| **Total = ~2 250 €/mois** | **DEMOEMA Pro × 5 = 995 €/mois** |
| | **Économie : -55%** |

## Add-ons à venir

- ⏳ **Y2 2027** — Contact enrichment (email + tel direct) : 5 €/contact débloqué
- ⏳ **Y2 2027** — Comptes PME enrichis (via partenaire Ellisphere) : +50 €/user/mois
- ⏳ **Y2 2027** — Multiples EBITDA sectoriels : +100 €/user/mois
- ⏳ **Y2 2027** — Extension Chrome / LinkedIn : gratuit pour Pro et Enterprise
- ⏳ **Y3 2028** — **Module Europe (UK + Allemagne)** : +50%/user/mois

---

# PARTIE 9 — PROGRAMME BÊTA-TESTEUR PREMIUM ⭐

## Offre exclusive pour les 10 premiers clients

En tant que **boutique pionnière**, vous avez droit à :

✅ **6 mois d'accès Pro gratuit** (valeur 1 194 € par user)
✅ **Prix de lancement** bloqué 24 mois après la fin de la bêta (-30% vs prix public)
✅ **Onboarding personnalisé** par le founder en direct (3h en visio ou présentiel)
✅ **Support prioritaire** (réponse <4h ouvrées)
✅ **Roadmap participative** : vos suggestions prioritaires intégrées
✅ **Visibilité** : votre logo sur notre page "Ils nous font confiance" (avec accord)

**Contreparties (légères)** :
- Accepter 2 calls de feedback de 30 min/mois
- Tester les nouvelles features en avant-première
- Accepter d'être cité (ou anonymisé selon préférence) comme beta-testeur
- Témoignage écrit court si le produit répond à vos attentes (pas obligatoire)

## Comment rejoindre la bêta

1. Contactez-nous : **[email du founder]**
2. Call de 30 min pour comprendre votre contexte
3. Démo du produit + accès bêta activé
4. Onboarding personnalisé dans les 48h

**Places limitées : 10 boutiques maximum.**

---

# PARTIE 10 — PARCOURS BÊTA-TESTEUR (Q3 2026 onwards)

## Comment vous découvrez DEMOEMA en bêta

### Mois 1 — Onboarding personnalisé (octobre 2026)
- Call 1h avec le founder (pas un commercial)
- Paramétrage de votre compte + watchlist (50 entreprises à surveiller)
- Premières alertes signaux pré-cession reçues sur vos secteurs
- Découverte des fiches enrichies 360°

### Mois 2 — Premiers cas d'usage réels
- Test sur 3 cibles de votre pipeline actuel
- Génération de votre première **buyer list** via DEMOEMA (mode manuel Q4, copilot IA Y2)
- Export Excel avec vos templates M&A
- Premier ressenti partagé (call 30 min de feedback)

### Mois 3 — Who advises whom disponible (décembre 2026)
- Accès à la base des 3 000+ deals M&A indexés
- Test : "qui conseille mes cibles actuelles ?"
- Import/export CSV vers votre Affinity / Dealcloud
- Point hebdo avec le founder (support direct en bêta)

### Mois 4-6 — Mesure du ROI
- Revue des KPIs : temps gagné, cibles qualifiées, deals issus
- Ajustement de la roadmap selon votre feedback (vous co-designez)
- Extension à votre équipe (jusqu'à 5 users inclus dans Pro)

### Mois 6+ — Transition bêta → client
- Tarif préférentiel bloqué 24 mois (prix bêta conservé)
- Témoignage/case study en co-construction (optionnel)
- Accès prioritaire aux nouvelles features (copilot IA Y2, contact enrichment Y2, etc.)

---

## Parcours standard (à partir de Q2 2027, hors bêta)

1. Inscription en ligne (3 min, sans CB)
2. Accès à 10 fiches gratuites pour tester
3. Upgrade Starter (49€/mois) ou Pro (199€/mois) selon vos besoins
4. Onboarding vidéo 20 min + documentation
5. Support par email <24h ouvrées

---

# PARTIE 11 — FAQ

## Questions fréquentes

### Sur la donnée

**Q : D'où viennent les données ?**
**R :** De 140 sources publiques officielles (INSEE, INPI, BODACC, AMF, Ministère de l'Économie, etc.). Chaque donnée est sourcée avec lien de vérification. **Ingestion progressive Q3 2026 → fin 2027** selon priorité.

**Q : Quelle fraîcheur ?**
**R :** Variable selon la source, à partir de sa mise en production :
- Sanctions : mise à jour quotidienne (sources officielles)
- BODACC : mise à jour quotidienne (flux public)
- Comptes annuels INPI : à chaque dépôt (généralement J+15-30)
- Presse : polling RSS toutes les heures

**Q : Que se passe-t-il si une entreprise n'a pas déposé ses comptes ?**
**R :** Nous affichons les **ratios sectoriels ESANE INSEE** comme estimation, clairement marqués "estimé". **Y2 2027** : partenariat avec Ellisphere / Altares pour des estimations plus fines.

**Q : Couvrez-vous les entreprises étrangères ?**
**R :** Aujourd'hui : uniquement FR. **Y3 2028** : extension **UK + Allemagne**. **Y4 2029** : BENELUX + Italie + Espagne.

### Sur la confidentialité

**Q : Nos recherches sont-elles vues par quelqu'un ?**
**R :** Non. Vos recherches sont strictement privées, chiffrées, et ne sont jamais partagées ni revendues.

**Q : Qu'en est-il du RGPD pour les dirigeants apparaissant dans les fiches ?**
**R :** Base légale = intérêt légitime documenté (LIA). Procédure de droit à l'oubli formalisée. Données personnelles limitées aux mandats publics officiels (JO, INSEE, INPI).

**Q : Que se passe-t-il si un dirigeant demande à être retiré ?**
**R :** Sous 30 jours, retrait effectif de la base. Notification au demandeur. Procédure documentée par notre DPO.

### Sur la concurrence

**Q : Pourquoi pas Pappers ?**
**R :** Pappers est excellent pour le lookup. Mais il ne fait pas de graphe visuel, pas de signaux pré-cession, pas d'historique advisors, pas d'intelligence prédictive. Il est outil de référence, nous sommes outil de production M&A.

**Q : Pourquoi pas Bureau van Dijk / Diane ?**
**R :** 15-50k€/user/an minimum, UX des années 2000, contrats annuels rigides, pas d'IA. Nous offrons 80% de la valeur pour 10% du prix.

**Q : Pourquoi pas Pitchbook ?**
**R :** 25-80k€/user/an, aveugle sur l'ETI française, US-centric. Nous sommes FR-natifs et accessibles.

### Sur le produit

**Q : Combien de temps pour se former ?**
**R :** 30 minutes pour les cas d'usage basiques. 2h pour maîtriser le copilot et les exports. Onboarding 3h inclus en Pro et Enterprise.

**Q : Peut-on tester gratuitement ?**
**R :** Oui. Plan Free (10 fiches/mois) sans carte bancaire. Ou rejoignez le **programme bêta-testeur 6 mois gratuit** (10 places).

**Q : Que se passe-t-il si je ne suis pas satisfait ?**
**R :** Starter : résiliable à tout moment (pas d'engagement). Pro annuel : remboursement prorata temporis si problème technique majeur non résolu sous 30 jours.

### Sur l'IA

**Q : Le copilot peut-il se tromper ?**
**R :** Comme tout LLM, oui. C'est pourquoi nous citons toujours les sources et proposons un mode "sans IA". L'utilisateur reste seul décisionnaire. Conformité AI Act garantie.

**Q : Utilisez-vous les données clients pour entraîner l'IA ?**
**R :** **Jamais.** Nous utilisons Claude et Mistral via API, sans fine-tuning. Vos recherches et requêtes ne servent pas à entraîner quoi que ce soit.

### Commercial

**Q : Comment payer ?**
**R :** Carte bancaire (Stripe) pour Free/Starter/Pro. Facture + virement SEPA pour Enterprise. Pay-per-report : CB uniquement.

**Q : Contrats annuels obligatoires ?**
**R :** Non. Engagement mensuel possible (pas de remise). Annuel = -20% (2 mois offerts).

**Q : Facturation multi-users ?**
**R :** Oui. Pro avec 5+ users = facture unique, gestion centralisée.

---

# PARTIE 12 — LE FOUNDER ET LA VISION

## Notre histoire

DEMOEMA est née d'une frustration concrète :

> *"Quand j'étais en M&A, je payais Pappers plusieurs centaines d'euros/mois. Au-delà du prix, ce qui me frustrait c'était de switcher entre 5 outils pour préparer un simple teaser. Personne ne m'offrait une fiche vraiment intelligente, prédictive, avec le graphe des dirigeants. J'ai décidé de construire l'outil que j'aurais voulu avoir."*
>
> — [Nom du founder]

## Notre thèse

- Les **sources publiques françaises et européennes** contiennent déjà 80% de l'information dont un professionnel M&A a besoin
- Le problème n'est pas l'accès à la donnée, c'est la **centralisation, la fraîcheur et l'intelligence** (graphe, signaux, IA)
- Les **outils premium (BvD, Pitchbook)** sont réservés à un top 1% qui peut payer 30-80k€/user/an
- Les **200 boutiques M&A françaises mid-market** sont coincées entre "trop cher (BvD)" et "pas assez puissant (Pappers)"
- DEMOEMA comble ce gap avec **UX moderne + prix accessible + intelligence prédictive + souveraineté FR**

## Notre roadmap 4 ans

| | **2026** (Q2-Q4) | **2027** | **2028** | **2029** |
|---|---|---|---|---|
| **Scope** | 5M FR (light) | 5M FR enrichi | 5M FR + UK + DE | Europe complète |
| **Features** | Socle fiche 360° + ⭐ Alertes pré-cession + ⭐ Who advises whom | Copilot IA + scoring ML + contact enrichment | Modules verticaux + Europe UK/DE | Marketplace + IA avancée + BENELUX/Italie/Espagne |
| **Clients** | 50 | 200 | 500 | 2 000+ |
| **Équipe** | 4-5 | 9 | 18 | 35 |

## Notre engagement

- **Souveraineté** : données hébergées et traitées en France
- **Transparence** : chaque source citée, chaque IA signalée
- **Éthique** : respect RGPD + AI Act + droits voisins presse
- **Indépendance** : 100% sources publiques, pas de dépendance Pappers/BvD
- **Écoute** : les clients bêta définissent la roadmap

---

# PARTIE 13 — ILS NOUS FONT CONFIANCE

*À personnaliser après signature des premiers bêta-testeurs.*

### Partenaires bêta-testeurs (à partir de Q3 2026)
*Section à remplir au fur et à mesure des signatures de LOI. Ne pas diffuser de placeholder.*
- [Logo Boutique 1 — à obtenir]
- [Logo Boutique 2 — à obtenir]
- [Logo Boutique 3 — à obtenir]

### Témoignages clients (à collecter après onboarding bêta)

*Section à activer après 3 mois d'usage réel des bêta-testeurs.*

### Advisors (à confirmer)
*Section à activer après confirmation écrite de chaque advisor.*
- [Nom à confirmer], ex-partner [Banque d'affaires]
- [Nom à confirmer], ex-CTO [Scale-up data]
- [Nom à confirmer], juriste RGPD / AI Act

---

# PARTIE 14 — COMMENT DÉMARRER

## 3 façons de commencer dès aujourd'hui

### 🥇 Option 1 — Programme bêta-testeur premium (recommandé)
- **6 mois gratuits** + accompagnement direct du founder
- Places limitées : **10 boutiques**
- Contact : **[email founder]**

### 🥈 Option 2 — Rapport "Cible" à l'unité (pour tester)
- **490 €** un rapport enrichi 360°
- Livré sous 24h
- Aucun engagement
- Commandez : **[lien rapport]**

### 🥉 Option 3 — Démo commerciale 30 min
- Démo live du produit
- Discussion de votre cas d'usage
- Devis personnalisé si pertinent
- Réservez : **[lien Calendly]**

## Contact direct

**[Nom du founder]**
**[Email]**
**[LinkedIn]**
**[Téléphone direct]**

**Site web** : demoema.vercel.app
**Siège** : [Adresse Paris]

---

# PARTIE 15 — NOS ENGAGEMENTS

## Ce que nous vous promettons

1. **Prix stable** : les prix de lancement sont garantis 24 mois (grandfathering des clients existants en cas de hausse)
2. **Clause de sortie** : résiliation possible sans pénalité sur Starter et Pro mensuel
3. **SLA** : **99% uptime Y1 (2026)** → 99.5% Y2 (2027+)
4. **Réponse support** : <24h ouvrées sur Pro Y1 → <4h Y2, <1h Enterprise Y2+
5. **Mise à jour produit** : 1 release majeure par trimestre, patches hebdos
6. **Correction erreur donnée** : engagement sous 5 jours ouvrés après signalement
7. **Confidentialité** : vos recherches ne sont **jamais** vues, partagées, revendues
8. **RGPD** : conformité pleine, DPO externe contracté Q3 2026, DPIA validée Q4 2026
9. **IA Act** : conformité pleine, transparence IA, mode "sans IA" disponible, clause CGU "no automated decision on natural persons"
10. **Souveraineté** : données hébergées en France (Scaleway Paris), entreprise française
11. **Écoute** : roadmap publique, bêta-testeurs impliqués dans les décisions produit

---

# ANNEXES

## A. Glossaire M&A
- **LBO** : Leveraged Buy-Out, rachat avec effet de levier
- **RBE** : Registre des Bénéficiaires Effectifs
- **BODACC** : Bulletin Officiel des Annonces Civiles et Commerciales
- **Buyer list** : liste qualifiée d'acquéreurs potentiels pour une cible
- **Teaser** : document anonymisé de présentation d'une cible
- **DD** : Due Diligence, audit préalable
- **IM** : Information Memorandum, document de présentation complet d'une cible

## B. Références légales
- Règlement (UE) 2016/679 (RGPD)
- Règlement (UE) 2024/1689 (AI Act)
- Arrêt CJUE WM/Luxembourg Business Registers du 22/11/2022 (RBE)
- Licence Etalab 2.0 (data.gouv.fr)
- Code de commerce français (BODACC)

## C. Contacts institutionnels
- **CNIL** : cnil.fr (autorité RGPD et AI Act FR)
- **INSEE** : insee.fr (fournisseur SIRENE)
- **INPI** : inpi.fr (fournisseur RNE, comptes annuels)
- **DGTrésor** : dgtresor.gouv.fr (sanctions financières)

---

## Checklist d'envoi du document à un prospect

Avant d'envoyer ce PDF à un prospect :

- [ ] Personnalisé avec le logo DEMOEMA final
- [ ] Ajout des 2-3 logos bêta-testeurs (avec accord)
- [ ] Ajout des advisors confirmés
- [ ] Ajout des témoignages clients signés
- [ ] Vidéo démo produit liée (Loom)
- [ ] Email founder + Calendly fonctionnel
- [ ] PDF converti, <10 MB, lisible mobile
- [ ] Page de garde et mise en page pro (Figma / Canva)
- [ ] Version courte 1-pager préparée en parallèle

---

_Document commercial DEMOEMA v1.0 — Avril 2026. À convertir en PDF mis en page avant diffusion. Mettez à jour cette version après chaque cohorte de bêta-testeurs._

# RISQUES & CONFORMITÉ

> ⚠️ **Document V2 — corrigé post-audit 2026-04-17.**
>
> ⚠️ **Mises à jour majeures** :
> - **DPO coût** : valeur canonique = **5 000 €/mois (60k€/an)** externe régulier — cf. `FINANCES_UNIFIE.md` (corrige discordance V1 : 30k€/an vs 60-180k€/an)
> - **AI Act** : pas de fine-tuning Mistral (statut "déployeur" non "fournisseur GPAI"), CGU clause "no automated decision", DPIA Q3 2026 (12k€) — cf. `AI_ACT_COMPLIANCE.md`
> - **INPI RBE** : ⚠️ accès public **fermé depuis arrêt CJUE 22/11/2022** (WM/Luxembourg). Source retirée du datalake. Accès dérogatoire possible (avocat, journaliste).
> - **Stratégie email "{prenom}.{nom}"** : ✅ **JAMAIS implémentée** (juste documentée) — risque RGPD = 0 actuel. À ne pas activer sans LIA + DPIA.
> - **Trustpilot + Google Reviews** : retirés du datalake (CGU interdisent scraping commercial)
>
> Cartographie exhaustive des risques techniques, juridiques et business — avec mitigation pour chacun.

---

## 1. Risques juridiques (les plus critiques)

### 1.1 RGPD à 5M scale

| Risque | Détail | Probabilité | Impact | Mitigation |
|---|---|---|---|---|
| **Plainte CNIL pour démarchage non sollicité** | La "stratégie email {prenom}.{nom}" actuellement documentée n'est pas conforme à 5M scale | Haute | 1-4M€ amende | DPO dédié Y1, LIA documentée, opt-out industriel, pas d'envoi à froid sans contact préalable |
| **Demande de droit à l'effacement** | Dirigeants peuvent exiger suppression | Certaine (volume) | Moyen | Workflow <30j, logs accès |
| **Brèche de données** | 5M entités + 15M dirigeants = cible attractive | Moyenne | Élevé (réputation + amende) | Chiffrement at rest/transit, audit régulier, bug bounty |
| **Non-respect article 14 (information indirecte)** | Les personnes doivent être informées de la collecte | Haute | Moyen | Page transparence + notification au premier contact |

**Action immédiate** : DPO contracté (5-15k€/mois) **dès Q1 2026**. Pas négociable.

### 1.2 Droits voisins de la presse (loi 2019)

| Risque | Mitigation |
|---|---|
| Reproduction d'articles presse sans licence | Indexer **titres + URL + dates** uniquement, pas le corps. Si copilot cite : extraits courts (citation + lien) |
| Agrégation Google News-like | Loi française impose licence pour agrégation systématique. Soit licence soit on s'abstient de stocker le corps |

### 1.3 Scraping & CGU

| Source | Statut | Décision |
|---|---|---|
| LinkedIn | CGU interdisent scraping ; jurisprudence HiQ contestée | **Exclu** de l'archi |
| Glassdoor | CGU strictes | **Exclu** sauf API officielle si payant raisonnable |
| Trustpilot public | OK consultation, pas de scraping massif | API officielle uniquement |
| Wayback Machine | OK pour usage non commercial massif, sinon contrat | Limiter volume |
| Common Crawl | OK licence ouverte | OK |
| Sites institutionnels (data.gouv) | Licence Etalab 2.0 | OK |

**Règle d'or** : si un site n'a pas d'API publique, on **ne scrape pas**. On va voir s'il existe une autre source de la même donnée.

### 1.4 Bloctel

| Risque | Mitigation |
|---|---|
| Démarchage de numéros inscrits | Vérification systématique avant tout appel sortant |

### 1.5 Concurrence avec acteurs établis

| Acteur | Risque | Mitigation |
|---|---|---|
| Pappers, Société.com | Réplication base | Notre base = 100% redéveloppée depuis sources gouv. Aucun copy. |
| Bureau van Dijk (Moody's) | Possible attaque sur extraction | Bien documenter sources publiques |
| Infogreffe | Procédures collectives en doublon | Notre source = BODACC officiel, pas Infogreffe |

---

## 2. Risques techniques

### 2.1 Qualité des données

| Risque | Détail | Mitigation |
|---|---|---|
| **Entity resolution rate une fusion** | 2 lignes pour la même entité = scoring corrompu | Splink + revue humaine queue + métriques précision/rappel mensuelles |
| **Sources désynchronisées** | INSEE mensuel vs INPI temps réel = incohérence | Hiérarchie de sources documentée (golden record), affichage source par champ |
| **Faux positifs alertes M&A** | Signal mal interprété déclenche alerte erronée | Humain in the loop sur signaux haute valeur, A/B sur thresholds |
| **Données financières manquantes** | 50% des PME ne déposent pas leurs comptes | Imputation par benchmark sectoriel ESANE, transparence sur l'estimation |

### 2.2 Performance & scalabilité

| Risque | Mitigation |
|---|---|
| Volumétrie Neo4j (15M+ nœuds, 50M+ arêtes) | Limiter le graphe aux personnes+holdings, le reste en ClickHouse |
| Coût LLM explose à scale | Cache embeddings (obligatoire), LLM routing (Mistral pour simple → Claude pour complexe), batching |
| Latence requêtes graphe profondes | Indexes Neo4j ciblés, limite profondeur par défaut à 3 |
| Compute ML mensuel coûteux | Reentrainement modèle ML 1×/mois, pas plus |

### 2.3 Dépendances externes

| Dépendance | Risque | Mitigation |
|---|---|---|
| API INSEE | Quotas, downtime | Bulk Sirene Stock = source primaire, API = deltas |
| API INPI | Quotas stricts | Idem, prioriser bulk |
| OpenSanctions | Changement de licence (devient payant) | Garder snapshot, surveillance hebdo des CGU |
| Anthropic / Mistral | Coût ou indisponibilité | Multi-provider routing, abstraction LLM |
| Scaleway | Souveraineté mais provider unique | Backup multi-cloud (S3 répliqué OVH ou AWS Frankfurt) |

### 2.4 Sécurité

| Menace | Mitigation |
|---|---|
| Scraping de notre API | Rate limiting, CAPTCHA sur endpoints publics, watermarking données |
| SQL injection | ORM + paramètres préparés, audit |
| Compromission compte admin | MFA obligatoire, rotation secrets, IP whitelist |
| Dépendances vulnérables | Renovate + Snyk + audit pré-déploiement |
| Insider threat | Audit logs immuables, principe least privilege |

---

## 3. Risques business

### 3.1 Marché & concurrence

| Risque | Mitigation |
|---|---|
| **Pappers / Société.com baissent prix** | Différenciation par graphe dirigeants + signaux M&A + copilot IA (pas juste registre) |
| **Bureau van Dijk (Moody's)** écrase | Niche FR + ETI mid-cap + UX moderne ; eux = legacy lourd |
| **API gouv deviennent payantes** | Stockage local bulk + redondance sources + plaidoyer API Gouv |
| **Cycle M&A en baisse** | Diversifier : compliance, due diligence, CRM, intelligence concurrentielle |
| **Nouveau entrant LLM-first** | Vitesse exécution + pricing agressif Y1-Y2 + relations clients établies |

### 3.2 Adoption / Go-to-market

| Risque | Mitigation |
|---|---|
| Cycle de vente long (banques d'affaires, PE) | Self-service + tier gratuit pour acquérir + freemium |
| Churn élevé chez petits clients | Annual contracts, success management, ROI tangible |
| Dépendance à 5-10 gros clients | Diversifier dès Y2 (>100 logos en pipeline) |
| Cannibalisation entre verticaux | Pricing différencié, modules séparés |

### 3.3 Équipe & opérations

| Risque | Mitigation |
|---|---|
| Recrutement Senior data eng difficile en France | Remote-first, equity attractif, marque employeur (open source contrib) |
| Burn-out fondateurs | Equipe étoffée Y2, conseil d'administration actif |
| Départ d'un sachant clé | Documentation systématique, pair programming, redundance compétences |
| Conflit cofondateurs | Pacte d'actionnaires + advisory board |

---

## 4. Risques financiers

| Risque | Mitigation |
|---|---|
| **Échec levée seed** | Bootstrap revenue Y1 avec premiers contrats, backup BPI/non-dilutif |
| **Runway < 6 mois** | Suivi mensuel cash, alerte à 9 mois, plan B (réduire équipe) |
| **Coûts infra explosent** | FinOps mensuel, alertes budget, archivage S3 IA après 90j |
| **Devises (LLM en USD)** | Hedging si exposition >50k€/mois |
| **Recouvrement clients** | Conditions paiement avant 30j, relances auto, factoring si besoin |

---

## 5. Plan de continuité (BCP/DRP)

| Composant | RPO (perte max) | RTO (downtime max) | Solution |
|---|---|---|---|
| ClickHouse Gold | 1h | 4h | Snapshot horaire + réplique multi-AZ |
| Neo4j | 1h | 4h | Backup horaire + replica |
| Qdrant | 4h | 8h | Snapshot 4h, reconstructible depuis ClickHouse |
| S3 Iceberg | 0 (immutable) | 1h | Réplication multi-région Scaleway |
| API FastAPI | 0 | 5min | Multi-instance derrière LB, auto-restart |
| Front Next.js | 0 | 1min | Vercel edge, fallback statique |

**Test DRP** : 1× par an minimum, simulation de panne complète d'un composant.

---

## 6. Conformité — checklist Y1

- [ ] DPO externe contracté (Q1 2026)
- [ ] Registre des traitements RGPD rédigé (Q1 2026)
- [ ] LIA documentée pour prospection B2B (Q1 2026)
- [ ] Page transparence/cookies/mentions légales (Q1 2026)
- [ ] Procédure droit à l'effacement (workflow Notion + dev) (Q1 2026)
- [ ] Audit RGPD complet (Q4 2026)
- [ ] CGU & politique de confidentialité validées par avocat (Q1 2026)
- [ ] Conditions API publique rédigées (Q4 2026)
- [ ] Pacte d'actionnaires + KBIS + statuts (Q1 2026)

## Conformité — checklist Y2-Y4

- [ ] Audit pen-test annuel (Y2)
- [ ] Bug bounty (Y2)
- [ ] DPO interne (Y3)
- [ ] SOC2 Type I → Type II (Y3 → Y4)
- [ ] ISO 27001 (Y4)
- [ ] HDS si santé en module vertical (Y3-Y4)
- [ ] DPIA pour les modules à risque élevé (Y2)

---

## 7. Matrice de criticité

| Risque | Probabilité | Impact | Score | Action |
|---|---|---|---|---|
| RGPD démarchage non conforme | 4/5 | 5/5 | 20 | **CRITIQUE** — DPO dès Q1 |
| Brèche données | 2/5 | 5/5 | 10 | Prio sécurité Y1 |
| Échec levée seed | 3/5 | 5/5 | 15 | Bootstrap revenue + plan B |
| Pappers baisse prix | 3/5 | 3/5 | 9 | Différenciation graph + IA |
| Entity resolution rate | 4/5 | 4/5 | 16 | Splink + queue revue + tests |
| Coût LLM explose | 3/5 | 4/5 | 12 | Cache + routing |
| Cycle vente long | 4/5 | 3/5 | 12 | Self-service + freemium |
| Recrutement data eng | 4/5 | 3/5 | 12 | Marque employeur + remote |
| Dépendance INSEE/INPI | 2/5 | 4/5 | 8 | Bulk + redondance |
| Scraping non autorisé | 2/5 | 4/5 | 8 | Politique stricte API only |

> Tout score ≥15 = action immédiate. Tout score ≥10 = plan d'action documenté.

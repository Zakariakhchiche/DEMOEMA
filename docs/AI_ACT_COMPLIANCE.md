# CONFORMITÉ AI ACT (Règlement UE 2024/1689)

> ⚠️ **Document V2 — décisions AI Act verrouillées le 2026-04-17.**
>
> **Décisions clés** (cf. section "Décisions verrouillées" plus bas) :
> - ❌ **Pas de fine-tuning Mistral** → statut "déployeur" (pas "fournisseur GPAI")
> - ✅ **CGU clause obligatoire** : interdiction usage décisionnel automatique sur personnes physiques
> - ✅ **DPIA Q3 2026** par cabinet RGPD (12k€)
>
> Source unique : [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md) · État réel : [`REPONSES_SELF_CHALLENGE.md`](./REPONSES_SELF_CHALLENGE.md)
>
> Le règlement européen sur l'IA est entré progressivement en vigueur depuis 2024. Application complète aux systèmes IA généralistes en **août 2026**, et à la majorité des systèmes en **août 2027**. Notre copilot LLM est concerné.

---

## Classification de notre système IA

### Composants IA dans DEMOEMA

| Composant | Risque AI Act | Statut |
|---|---|---|
| **Scoring M&A (LightGBM)** | Risque limité | Pas d'impact direct sur droits fondamentaux des personnes |
| **Scoring défaillance (Signaux Faibles)** | Risque limité | Idem, sortie informationnelle |
| **NLP extraction événements presse** | Risque minimal | Tâche technique standard |
| **Entity matching (Splink)** | Risque minimal | Déduplication de bases publiques |
| **Copilot LLM (Claude / Mistral)** | **Système IA à usage général (GPAI)** + risque limité | **Obligations de transparence** |
| **Recommandations cibles M&A** | Risque limité | Aide à la décision business, pas administrative ou personnelle |
| **Notation/scoring de personnes physiques** | ⚠️ ATTENTION | Si on score les **dirigeants individuellement**, risque "haut" possible |

### Notre niveau de risque global

🟢 **Risque LIMITÉ** : la majorité de notre stack tombe dans cette catégorie.
🟡 **Vigilance** : tout scoring qui touche **directement** des personnes physiques (dirigeants notés sur leur "performance") = potentiellement à haut risque, à éviter ou à encadrer.
🔴 **Interdit** : aucune fonctionnalité interdite (notation sociale, manipulation, etc.).

### Décisions verrouillées 2026-04-17 (audit SELF_CHALLENGE Q30-Q31)

✅ **Pas de fine-tuning de LLM génératif** (Mistral 7B Instruct, Claude, Llama) : nous restons "déployeur" d'API LLM. **Pas de statut GPAI provider**, pas d'obligations art. 53.

✅ **Fine-tuning AUTORISÉ de modèles NLP encoder/extracteur** (CamemBERT, spaCy, BERT, RoBERTa pour NER/classification) — utilisé pour Killer feature #2 "Who advises whom" (extraction triplet `(cible, acquéreur, advisors)` depuis sites M&A). **Ces modèles ne sont pas des GPAI** au sens de l'art. 3(66) AI Act (qui cible les modèles génératifs de portée générale type Mistral/Llama/GPT). **Aucune obligation art. 53**.

> **Précision juridique post-audit V3 (Q165)** : la définition GPAI (art. 3 §66) précise *"modèle d'IA … capable d'exécuter avec compétence un large éventail de tâches distinctes"*. Un CamemBERT fine-tuné pour la NER de noms d'advisors est **étroitement spécialisé** = hors périmètre GPAI. Référence : guidance officielle BCAI 2025 sur la distinction modèles spécialisés vs généralistes.

✅ **CGU clause obligatoire** : interdiction explicite à nos clients d'utiliser nos scores pour des décisions automatisées sur personnes physiques (crédit, embauche, etc.). **Le score reste "aide à la qualification" non décisionnelle**. Évite la bascule en système IA haut risque (Annexe III §5(b)).

✅ **DPIA planifiée Q3 2026** par cabinet RGPD spécialisé (12k€ initial + 5k€/an mise à jour).

---

## Obligations applicables

### 1. Transparence (article 50) — **Obligatoire**

Pour notre copilot LLM, nous devons :
- [ ] **Indiquer clairement à l'utilisateur qu'il interagit avec une IA** (mention visible dans l'UI)
- [ ] **Marquer le contenu généré** comme "généré par IA" (watermark technique + label visuel)
- [ ] **Permettre la détection** automatique des contenus IA (steganographie / metadata)

### 2. Modèles GPAI (article 53) — Si utilisation directe

Nous **utilisons** des GPAI (Claude, Mistral) — nous ne les **fournissons** pas. Donc obligations limitées :
- Nous devons documenter **comment** nous les utilisons
- Nous devons avoir des **garde-fous** (filtrage prompts, limitation outputs)

### 3. Si scoring de personnes physiques (article 6)

Si on évalue un **dirigeant** (note de fiabilité, prédiction comportement) :
- [ ] **Évaluation des risques** documentée
- [ ] **Surveillance humaine** obligatoire dans le workflow
- [ ] **Information de la personne** sur le scoring
- [ ] **Droit de contestation** offert

> **Décision recommandée** : on score les **entreprises** (pas les personnes). Les "scores dirigeants" sont indicatifs et descriptifs (nombre de mandats, ancienneté), pas évaluatifs.

### 4. Documentation technique (article 11) — Pour systèmes à risque

Pas applicable directement à nous, mais bonnes pratiques à adopter :
- Datasheets pour chaque modèle
- Logs des entraînements
- Versions des modèles tracées

---

## Calendrier d'application

| Date | Obligation | Notre action |
|---|---|---|
| **2 août 2025** | Pratiques interdites entrées en vigueur | ✅ Déjà conforme (rien d'interdit chez nous) |
| **2 août 2026** | Modèles GPAI | Audit usage Claude/Mistral, documentation |
| **2 août 2027** | Systèmes à haut risque + transparence | Watermarking + mention IA + DPIA |
| **Continu** | Code de bonnes pratiques GPAI | Suivre les guidelines BCAI |

---

## Plan d'action conformité IA

### Q1-Q2 2026
- [ ] Designer le DPIA (Data Protection Impact Assessment) qui couvre aussi l'AI Act
- [ ] Définir la charte d'usage de l'IA (interne + utilisateurs)
- [ ] Inventaire des modèles utilisés (datasheet par modèle)

### Q3 2026 (avec lancement copilot)
- [ ] Mention "IA générée" obligatoire dans toutes les réponses du copilot
- [ ] Watermarking technique des outputs
- [ ] Logs des prompts/réponses (pour audit + amélioration)
- [ ] Filtrage des prompts à risque (PII excessif, données sensibles)
- [ ] Possibilité utilisateur de désactiver le copilot

### Q4 2026
- [ ] Audit externe AI Act readiness (cabinet juridique spécialisé)
- [ ] Procédure d'incident IA documentée
- [ ] Formation équipe (devs + sales) sur AI Act

### Y2-Y3
- [ ] Si scoring de personnes : DPIA renforcé + procédure de contestation
- [ ] Adhésion au code de bonnes pratiques GPAI BCAI (volontaire)
- [ ] Audit annuel conformité

---

## Pratiques explicitement à éviter

| Pratique | Pourquoi |
|---|---|
| **Prédire la solvabilité personnelle** d'un dirigeant individuellement | Système à haut risque (annexe III) |
| **Profilage** émotionnel ou comportemental | Pratique interdite (art. 5) |
| **Notation sociale** des dirigeants/entreprises au-delà du business factuel | Pratique interdite (art. 5) |
| **Reconnaissance faciale** sur photos dirigeants | Pratique interdite hors exceptions strictes |
| **Manipulation comportementale** des utilisateurs (dark patterns IA) | Pratique interdite (art. 5) |

---

## Articulation avec le RGPD

L'AI Act ne remplace pas le RGPD — il s'y ajoute. Les deux s'appliquent **cumulativement** :

| Aspect | RGPD | AI Act |
|---|---|---|
| Données personnelles | ✅ | (uniquement si IA traite ces données) |
| Décisions automatisées | Art. 22 RGPD | Article 14 + classification risque |
| Transparence | Art. 13-14 RGPD | Article 50 AI Act |
| DPIA | Art. 35 RGPD | + AIIA (AI Impact Assessment) si haut risque |
| Sanctions | 4% CA | **Jusqu'à 7% CA mondial** (plus sévère) |

---

## Sanctions financières

| Manquement | Sanction max |
|---|---|
| Pratiques interdites | 7% du CA mondial ou 35M€ |
| Obligations systèmes haut risque / GPAI | 3% du CA mondial ou 15M€ |
| Obligations transparence (article 50) | 1% du CA mondial ou 7.5M€ |

> Ces sanctions sont **cumulables** avec celles du RGPD.

---

## Checklist Go/No-Go avant lancement copilot

Avant d'activer le copilot LLM en production :

- [ ] Mention "Cette réponse est générée par IA" visible
- [ ] Watermark technique sur outputs (LLM-watermarking ou metadata)
- [ ] Charte d'usage IA accessible utilisateurs
- [ ] Logs prompts/réponses avec rétention conforme RGPD
- [ ] Procédure d'incident IA testée
- [ ] DPIA validé par DPO
- [ ] Filtrage prompts à risque actif
- [ ] Bouton "désactiver copilot" disponible
- [ ] Pas de scoring de personnes physiques activé
- [ ] Audit externe AI Act passé

**Tant que cette checklist n'est pas verte, le copilot reste en mode démo interne.**

---

## Ressources

- Texte officiel : EUR-Lex 32024R1689
- BCAI (Bureau européen IA) : ec.europa.eu/digital-strategy/policies/european-ai-office
- CNIL — guides IA : cnil.fr/fr/intelligence-artificielle
- Code de bonnes pratiques GPAI (en cours de rédaction par BCAI)

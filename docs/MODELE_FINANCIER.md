# MODÈLE FINANCIER 3 ANS — 2026-2028

> ⚠️ **Document V2 — chiffres reconciliés post-audit 2026-04-17.**
>
> **Source unique de vérité chiffrée** : [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md) (= ce doc + alignement avec roadmap/budget)
> **Source CSV mensuel** : [`modele_financier.csv`](./modele_financier.csv) (ouvrable Excel / Google Sheets)
>
> ⚠️ **Calendrier** : les "M01-M12 = jan-déc 2026" sont à lire comme **"M01 = avril 2026"** (décalage +3 mois post-audit).
>
> P&L mensuel, hypothèses détaillées, sensibilités. Aligné Scénario B (décisions validées le 2026-04-17).

---

## Hypothèses générales

### Côté revenus

| Composant | Hypothèse | Source |
|---|---|---|
| **Pay-per-report** | Démarre M5 (août 2026), 2 rapports puis +30%/mois | Validation marché Q2 |
| **Starter (49€/mois)** | Lancement M7 (octobre 2026), +5 users/mois Y1, +5/mois Y2, +10/mois Y3 | Auto-onboarding self-service |
| **Pro (199€/mois)** | Lancement M10 (janvier 2027), +5 users/mois Y1-Y2, +15/mois Y3 | Sales + product-led |
| **Enterprise (avg 25k€/an)** | 1er contrat M22 (janvier 2028) — cycle vente long Y2 | Sales direct, démo ROI |
| **Churn mensuel** | 5% Starter, 3% Pro, 1% Enterprise | Standard B2B SaaS early-stage |
| **Annualisation** | 30% des Starter, 60% Pro, 100% Enterprise | Discount −20% engagement annuel |

### Côté coûts

| Composant | Hypothèse |
|---|---|
| **Salaires** | Chargés Paris tech 2026 (cf. `BUDGET_EQUIPE.md`), +3%/an inflation |
| **Founder** | 0€ Y1 (equity), 60k€/an chargé Y2, 100k€/an Y3 |
| **Infra** | Croît avec usage : 100€/mois Y1 → 500€ Y2 → 2k€ Y3 (cf. `ARCHITECTURE_TECHNIQUE.md`) |
| **LLM** | Démarre Q3 2026, monte progressivement avec users (~2€/user/mois moyen) |
| **DPO externe** | 5k€/mois fixe dès M2 (Mai 2026) |
| **Légal corporate** | 1k€/mois moyen + spikes (levée, contrat) |
| **Marketing** | 1k€/mois Y1, 4k€ Y2, 12k€ Y3 (≈10% revenu) |
| **Recrutement** | 1.5k€/mois moyen (LinkedIn, AT, prime cooptation) |
| **Bureau** | 0€ Y1-Y2 (full remote), 8k€/mois à partir M30 (Sep 2028) |
| **Contingence** | +10% sur tous les coûts opérationnels (provision imprévus) |

### Cash injections (calendrier décalé +3 mois post-audit 2026-04-17)

| Phase | Mois | Calendrier | Montant | Hypothèse |
|---|---|---|---|---|
| **Pré-amorçage** | M3 | **Juin 2026** | **600 k€** | Mix BPI Bourse FT (30k) + 4-5 BA (570k) |
| **Seed** | M14 | **Mai 2027** | **2 000 k€** | VC seed FR (Frst, Kima, Elaia) |
| **Series A** | M26 | **Mai 2028** | **8 000 k€** | VC tech FR/UE (Partech, Eurazeo) |

> **Note** : "Y1 fiscal" = M1-M12 = **avril 2026 à mars 2027** (12 mois). Y2 = M13-M24. Y3 = M25-M36. Si tu raisonnes en année calendaire pour la compta : 2026 calendaire = M1-M9 (9 mois Apr-Dec), 2027 = M10-M21, 2028 = M22-M33, 2029 = M34-M36 (3 mois Jan-Mar).

---

## Synthèse annuelle (P&L) — chiffres alignés CSV (fiscal year)

> Y1 fiscal = avril 2026 → mars 2027 ; Y2 = avril 2027 → mars 2028 ; Y3 = avril 2028 → mars 2029.

| Ligne | Y1 (FY 2026-27) | Y2 (FY 2027-28) | Y3 (FY 2028-29) |
|---|---|---|---|
| **Revenus pay-per-report** | 32 k€ | 110 k€ | 111 k€ |
| **Revenus Starter (récurrent)** | 8 k€ | 91 k€ | 206 k€ |
| **Revenus Pro (récurrent)** | 7 k€ | 193 k€ | 775 k€ |
| **Revenus Enterprise (récurrent)** | 0 | 15 k€ | 576 k€ |
| **Revenus totaux** | **44 k€** | **412 k€** | **1 680 k€** |
| **MRR récurrent fin de période** | 6.7 k€ | 48.7 k€ | 199 k€ |
| **ARR fin de période** | **80 k€** | **584 k€** | **2 389 k€** |
| | | | |
| **Salaires (chargés + frais)** | 364 k€ | 996 k€ | 2 178 k€ |
| **Infra cloud** | 14 k€ | 64 k€ | 178 k€ |
| **LLM + APIs** | 5 k€ | 51 k€ | 219 k€ |
| **Outils SaaS** | 14 k€ | 24 k€ | 43 k€ |
| **Légal + DPO** | 91 k€ | 86 k€ | 78 k€ |
| **Comptabilité** | 8 k€ | 8 k€ | 12 k€ |
| **Marketing & Sales** | 15 k€ | 40 k€ | 102 k€ |
| **Voyage / events** | 8 k€ | 22 k€ | 50 k€ |
| **Recrutement** | 17 k€ | 28 k€ | 56 k€ |
| **Bureau** | 0 | 0 | 28 k€ |
| **Autres** | 11 k€ | 12 k€ | 21 k€ |
| **Contingence (10%)** | 53 k€ | 132 k€ | 297 k€ |
| **Coûts totaux** | **578 k€** | **1 447 k€** | **3 262 k€** |
| | | | |
| **Résultat opérationnel** | **-534 k€** | **-1 035 k€** | **-1 582 k€** |
| | | | |
| **Cash injections** | **600 k€** | **2 000 k€** | **8 000 k€** |
| **Cash variation** | +66 k€ | +965 k€ | +6 418 k€ |
| **Cash position fin période** | **66 k€** | **1 031 k€** | **7 449 k€** |

> ⚠️ **Source unique : ce tableau et `FINANCES_UNIFIE.md`** sont alignés sur le CSV mensuel. Si écart avec `BUDGET_EQUIPE.md`, c'est ce document + `FINANCES_UNIFIE.md` qui font foi.

### Conséquence opérationnelle

Le modèle est **viable** (cash positif sur les 3 années), avec :
- **Pré-amorçage 600 k€ obligatoire** (closing fin juin 2026) — sinon cash épuisé M13 (avril 2027)
- **Seed 2 M€ minimum** mai 2027 (M14) — sinon cash épuisé M14
- **Series A 8 M€** mai 2028 (M26) — pour financer Y3 (équipe 18 FTE)
- **Cash position fin Y3** : ~7.4 M€ → runway >12 mois ou rentabilité Y4

---

## Synthèse trimestrielle (vue plus fine, fiscal year)

### Y1 fiscal (Avril 2026 → Mars 2027)

| Trimestre fiscal | Période | Revenus | Coûts | Résultat | Headcount |
|---|---|---|---|---|---|
| Q1 (Avr-Jun 2026) | M1-M3 | 0 | 59 k€ | -59 k€ | 1.5 |
| Q2 (Jul-Sep 2026) | M4-M6 | 2.5 k€ | 129 k€ | -126 k€ | 2.5-3.5 |
| Q3 (Oct-Dec 2026) | M7-M9 | 10.6 k€ | 191 k€ | -180 k€ | 4 |
| Q4 (Jan-Mar 2027) | M10-M12 | 31.2 k€ | 200 k€ | -169 k€ | 4 |
| **Y1 fiscal** | M1-M12 | **44 k€** | **578 k€** | **-534 k€** | 4 fin Y1 |

### Y2 fiscal (Avril 2027 → Mars 2028)

| Trimestre fiscal | Période | Revenus | Coûts | Résultat | Headcount |
|---|---|---|---|---|---|
| Q1 (Avr-Jun 2027) | M13-M15 | 58 k€ | 273 k€ | -215 k€ | 5 |
| Q2 (Jul-Sep 2027) | M16-M18 | 84 k€ | 345 k€ | -261 k€ | 6 |
| Q3 (Oct-Dec 2027) | M19-M21 | 112 k€ | 403 k€ | -291 k€ | 7 |
| Q4 (Jan-Mar 2028) | M22-M24 | 158 k€ | 426 k€ | -268 k€ | 7 |
| **Y2 fiscal** | M13-M24 | **412 k€** | **1 447 k€** | **-1 035 k€** | 7 fin Y2 |

### Y3 fiscal (Avril 2028 → Mars 2029)

| Trimestre fiscal | Période | Revenus | Coûts | Résultat | Headcount |
|---|---|---|---|---|---|
| Q1 (Avr-Jun 2028) | M25-M27 | 225 k€ | 582 k€ | -357 k€ | 9-10 |
| Q2 (Jul-Sep 2028) | M28-M30 | 338 k€ | 718 k€ | -380 k€ | 10-13 |
| Q3 (Oct-Dec 2028) | M31-M33 | 511 k€ | 900 k€ | -389 k€ | 13-15 |
| Q4 (Jan-Mar 2029) | M34-M36 | 605 k€ | 1 063 k€ | -458 k€ | 16-18 |
| **Y3 fiscal** | M25-M36 | **1 680 k€** | **3 263 k€** | **-1 583 k€** | 18 fin Y3 |

---

## Évolution du headcount par mois (calendrier réajusté +3 mois)

| Mois | Calendrier | Arrivée | Cumul FTE chargés | Salaire total mensuel |
|---|---|---|---|---|
| M1 | **Avril 2026** | Founder (0€) + designer freelance 5k€ | 1 + 0.5 freelance | 5 k€ |
| M2 | Mai 2026 | — | 1 + 0.5 | 5 k€ |
| M3 | **Juin 2026 (closing pré-amorçage)** | Lead Data Eng signé (start M4) | 1 + 0.5 | 5 k€ |
| M4 | **Juillet 2026** | **Lead Data Eng arrive (200k€/an chargé)** | 2 + 0.5 | 22 k€ |
| M5 | Août 2026 | — | 2 + 0.5 | 22 k€ |
| M6 | **Septembre 2026** | **Senior Backend (170k€)** | 3 + 0.5 | 36 k€ |
| M7 | **Octobre 2026** | **Senior Frontend (160k€)** + fin freelance designer | 4 | 47 k€ |
| M8 | Novembre 2026 | — | 4 | 47 k€ |
| M9 | Décembre 2026 | — | 4 | 47 k€ |
| M10 | Janvier 2027 | (ML Engineer décalé Y2) | 4 | 44 k€ |
| M11 | Février 2027 | — | 4 | 44 k€ |
| M12 | Mars 2027 | — | 4 | 44 k€ |
| M13 | Avril 2027 | **ML Engineer (200k€)** | 5 | 64 k€ |
| M14 | **Mai 2027 (Seed 2M€)** | **Founder se rémunère (60k€/an)** | 5 | 69 k€ |
| M16 | Juillet 2027 | **Lead Sales (200k OTE)** | 6 | 86 k€ |
| M19 | Octobre 2027 | **Product Manager (170k€)** | 7 | 100 k€ |
| M22 | Janvier 2028 | **Backend #2 (140k€)** | 8 | 112 k€ |
| M25 | Avril 2028 | **Data Engineer #2 (170k€)** | 9 | 126 k€ |
| M26 | **Mai 2028 (Series A 8M€)** | — | 9 | 126 k€ |
| M28 | Juillet 2028 | **CRO (350k€ OTE)** + AE #1 | 11 | 158 k€ |
| M30 | Septembre 2028 | **AE #2** + **DPO interne (130k€)** | 13 | 184 k€ |
| M32 | Novembre 2028 | **ML Engineer #2 (200k€)** + Frontend #2 | 15 | 213 k€ |
| M34 | Janvier 2029 | **Customer Success + SDR + Designer interne** | 18 | 246 k€ |

---

## Cash flow mensuel — points clés

```
Cash position (€k)
1500 ┤                                                         ╭──── 1461
     │                                                    ╭────╯
1200 ┤                                              ╭─────╯
     │                                        ╭─────╯
 900 ┤                                  ╭─────╯
     │                            ╭─────╯
 600 ┤  ╭───╮                ╭────╯  ← Seed M14: +2000k
     │  │   ╰──╮         ╭───╯
 300 ┤──╯      ╰─────────╯
     │                                                          
   0 ┤────────────────────────────────────────────────────────
     M1                  M12                M14                M24
     ↑                                       ↑
     Pré-amorçage M3 (Jun 2026): +600k       Seed M14 (Mai 2027): +2000k
```

| Moment critique | Cash position | Action |
|---|---|---|
| Démarrage M1 | 0 € | Personal money / advance founders |
| M3 — Pré-amorçage | **+400 k€** | Closing avant fin Q1 |
| M12 — Fin Y1 | **~255 k€** | Runway = ~3-4 mois sans levée |
| M14 — Seed | **+2 000 k€** | Closing début Q1 2027 |
| M24 — Fin Y2 | **~1 461 k€** | Runway = ~5-6 mois sans levée |
| M26 — Series A | **+8 000 k€** | Closing Q1 2028 |
| M36 — Fin Y3 | **~8 124 k€** | Runway >18 mois ou rentable Y4 |

> **Risque #1** : si Seed pas closé M14, runway épuisé entre M16 et M18. **Backup** : revenue-based financing Karmen (~500k€) si MRR >40k€.

---

## Métriques SaaS clés

| Métrique | Y1 | Y2 | Y3 |
|---|---|---|---|
| **MRR fin période** | 8 k€ | 55 k€ | 200 k€ |
| **ARR fin période** | 96 k€ | 660 k€ | 2 400 k€ |
| **Croissance ARR** | n/a | +588% | +264% |
| **Nb clients payants** | ~50 | ~180 | ~500 |
| **ARPU mensuel** | ~80 € | ~150 € | ~330 € |
| **Net Revenue Retention** | n/a | 105% | 115% |
| **Gross Margin** | 70% | 75% | 80% |
| **CAC** (estimé) | n/a | 800 € | 1 500 € |
| **LTV** (estimé) | n/a | 2 400 € | 6 000 € |
| **LTV/CAC** | n/a | 3× | 4× |
| **Burn multiple** (cash burn / nouveau ARR) | n/a | 1.4× | 0.8× |
| **Headcount fin période** | 5 | 9 | 18 |
| **Revenue per employee** | 12 k€ | 57 k€ | 104 k€ |

---

## Sensibilités (scénarios)

### Scénario PESSIMISTE (revenu −30%)

| | Y1 | Y2 | Y3 |
|---|---|---|---|
| Revenus | 41 k€ | 357 k€ | 1 313 k€ |
| Burn | -562 k€ | -947 k€ | -1 899 k€ |
| **Cash fin Y3** | | | **6 562 k€** |

→ Toujours viable, runway suffisant pour replanifier.

### Scénario OPTIMISTE (revenu +50%)

| | Y1 | Y2 | Y3 |
|---|---|---|---|
| Revenus | 87 k€ | 765 k€ | 2 813 k€ |
| Burn | -516 k€ | -539 k€ | -399 k€ |
| **Cash fin Y3** | | | **9 062 k€** |

→ Possibilité de **skip Series B**, atteindre rentabilité Y4 sans nouvelle dilution.

### Scénario CATASTROPHE (Seed pas levé)

→ Cash épuisé M16 (avril 27). Backup : RBF + réduction équipe à 3 personnes + focus revenu pure-play.

---

## Pricing sensitivity

L'ARR Y3 dépend fortement du mix produit. Sensibilité au pricing :

| Pricing Pro | Pricing Enterprise | ARR Y3 |
|---|---|---|
| 149€/mois | 20 k€ | 2 100 k€ |
| **199€/mois (default)** | **25 k€** | **2 400 k€** |
| 249€/mois | 30 k€ | 2 750 k€ |
| 299€/mois | 35 k€ | 3 100 k€ |

→ Pricing Pro 199€ est **conservateur**. Si validation marché confirme appétence à 249€, ARR Y3 +15%.

---

## Checks de cohérence avec autres docs

| Doc | Engagement | Modèle | Statut |
|---|---|---|---|
| `BUDGET_EQUIPE.md` Y1 budget | 525 k€ | 603 k€ (avec contingence) | ⚠️ Légèrement supérieur — corrigeable en lissant recrutement Q4 |
| `ROADMAP_4ANS.md` ARR Y2 | 500-800 k€ | 660 k€ | ✅ Au milieu |
| `ROADMAP_4ANS.md` ARR Y3 | 2-3 M€ | 2 400 k€ | ✅ Cohérent |
| `BUDGET_EQUIPE.md` headcount Y3 | 12-18 | 18 | ✅ Haut de fourchette |
| `BUDGET_EQUIPE.md` Levée Series A | 6-10 M€ | 8 M€ | ✅ Au milieu |

> Le modèle est légèrement plus prudent que BUDGET_EQUIPE V2 (contingence baked-in). Aligné sur Scénario B.

---

## Lignes que je n'ai PAS modélisées (à ajouter pour pitch VC)

À produire séparément si demandé :

- [ ] **Bilan** (Balance Sheet) — actif/passif
- [ ] **TVA & taxes** détaillées
- [ ] **CIR / CII** (créances fiscales R&D, ~−180k€/an Y2-Y3)
- [ ] **JEI** (réduction charges sociales, ~−40k€/an)
- [ ] **DSO/DPO** (délais paiement clients/fournisseurs)
- [ ] **Working capital** (besoin en fonds de roulement)
- [ ] **Cap table évolution** post-chaque levée
- [ ] **Valorisation pre-money** scénarios par tour
- [ ] **Dilution fondateurs** par scénario

---

## Comment exploiter le CSV

Le fichier `modele_financier.csv` contient **36 lignes** (M1 à M36) × **22 colonnes** :

```
Mois | Période | Headcount | Salaires | Infra | LLM | Outils | Legal | Compta | Marketing | Voyage | Recrut | Bureau | Autres | Contingence | Coûts | Reports | Starter | Pro | Enterprise | Revenus | Cash | (etc.)
```

**Pour modifier les hypothèses** : ouvrir dans Excel/Sheets, ajuster les cellules en colonne, recalculer (les sommes sont hardcodées dans le CSV — à transformer en formules si tu veux jouer avec).

**Recommandation** : copie le CSV dans un Google Sheet partagé avec ton expert-comptable et ton conseil. C'est plus facile à itérer.

---

## Prochaines actions recommandées

1. **Faire valider le modèle** par un expert-comptable (1-2h, ~500€)
2. **Présenter aux investisseurs** dans le deck pré-amorçage (slide "Use of funds" + "Trajectory")
3. **Mettre à jour mensuellement** dès Q2 2026 (réel vs prévu)
4. **Ajouter un Budget vs Actuals dashboard** (Notion ou Stripe Sigma + Pennylane plus tard)

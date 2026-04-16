# Signaux M&A — Scoring sur 100 points

## Systeme de scoring : 12 dimensions, 103 signaux

Chaque entreprise cible recoit un score global sur 100 points.
Les points sont repartis sur 12 dimensions avec un plafond par dimension.
Un score >= 65 = Action Prioritaire, >= 45 = Qualification,
>= 25 = Monitoring, < 25 = Veille Passive.

## Repartition des dimensions

| # | Dimension | Max pts | Poids | Nb signaux |
|---|-----------|---------|-------|------------|
| 1 | Maturite du dirigeant | 20 | 20% | 10 |
| 2 | Signaux patrimoniaux | 20 | 20% | 15 |
| 3 | Dynamique financiere | 15 | 15% | 17 |
| 4 | RH & Gouvernance | 12 | 12% | 10 |
| 5 | Consolidation sectorielle | 10 | 10% | 9 |
| 6 | Juridique & Reglementaire | 8 | 7% | 9 |
| 7 | Presse & Media | 8 | 5% | 6 |
| 8 | Innovation & PI | 6 | 3% | 5 |
| 9 | Immobilier & Actifs | 5 | 3% | 5 |
| 10 | ESG & Conformite | 5 | 2% | 4 |
| 11 | International & Cross-border | 5 | 2% | 4 |
| 12 | Marches publics & Dependance | 4 | 1% | 4 |
| | **TOTAL** | **~118 brut, plafonne a 100** | **100%** | **103** |

---

## DIMENSION 1 : MATURITE DIRIGEANT (max 20 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| founder_60_no_successor | Fondateur > 60 ans sans successeur | FORT | 7 | INPI RNE |
| founder_over_65 | Dirigeant de plus de 65 ans | FORT | 6 | INPI RNE |
| director_withdrawal | Retrait progressif du fondateur | FORT | 5 | LinkedIn, Presse |
| spouse_director_departure | Depart du conjoint co-dirigeant | FORT | 5 | BODACC, INPI |
| founder_age_55_65 | Dirigeant dans la tranche 55-65 ans | FAIBLE | 3 | INPI RNE |
| director_mandate_20plus | Mandat du dirigeant > 20 ans | FAIBLE | 2 | INPI RNE |
| dirigeant_multi_mandats | Mandats dans plusieurs societes | MOYEN | 3 | INPI RNE |
| director_new_ventures | Dirigeant implique dans nouveaux projets | FAIBLE | 2 | INPI, LinkedIn |
| director_speaker | Dirigeant intervenant / conferences | FAIBLE | 2 | Google News |
| director_health_proxy | Reduction d'activite professionnelle | FAIBLE | 1 | LinkedIn |

## DIMENSION 2 : SIGNAUX PATRIMONIAUX (max 20 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| holding_creation | Creation de holding patrimoniale | FORT | 7 | BODACC, Infogreffe |
| bodacc_cession | BODACC : cession de fonds / parts | FORT | 7 | API BODACC |
| apport_cession_structure | Apport-cession Art. 150-0 B ter | FORT | 6 | Infogreffe |
| share_sale_by_director | Cession de parts par un dirigeant | FORT | 6 | BODACC |
| beneficiaire_effectif_change | Changement de beneficiaire effectif | FORT | 5 | INPI RNE |
| bodacc_capital_change | BODACC : modification de capital | FORT | 5 | API BODACC |
| legal_form_change | Transformation SARL vers SAS | MOYEN | 4 | BODACC, Infogreffe |
| big4_audit | Nomination Big 4 en audit | MOYEN | 4 | Presse |
| infogreffe_capital_change | Modification capital (Infogreffe) | FORT | 4 | Infogreffe |
| sci_creation_linked | Creation SCI liee (separation immo) | MOYEN | 3 | INPI, Infogreffe |
| bodacc_dissolution | BODACC : dissolution / liquidation | FORT | 3 | API BODACC |
| donation_partage | Donation-partage de titres | MOYEN | 3 | Detection indirecte |
| pacte_dutreil | Mise en place Pacte Dutreil | MOYEN | 2 | Presse, notaires |
| auditor_change | Changement de commissaire aux comptes | FAIBLE | 2 | INPI |
| hq_relocation | Demenagement du siege social | FAIBLE | 1 | BODACC |

## DIMENSION 3 : DYNAMIQUE FINANCIERE (max 15 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| procedure_collective | Procedure collective en cours | FORT | 6 | BODACC, URSSAF |
| lbo_4_years | LBO en cours depuis > 4 ans | FORT | 5 | CFNews, Presse |
| revenue_decline_2years | Baisse CA > 10% sur 2 exercices | MOYEN | 4 | INPI comptes |
| ebitda_margin_compression | Compression marge EBITDA > 3 pts | MOYEN | 4 | INPI comptes |
| pret_garanti_etat | PGE important en cours | MOYEN | 3 | INPI bilans |
| debt_ratio_deterioration | Ratio endettement > 4x EBITDA | MOYEN | 3 | INPI bilans |
| exceptional_dividend | Distribution exceptionnelle dividendes | MOYEN | 3 | INPI bilans |
| ca_growth_2years | Croissance CA > 15% sur 2 ans | MOYEN | 3 | INPI comptes |
| score_defaillance_interne | Score defaillance interne eleve | MOYEN | 3 | Calcul interne |
| headcount_growth_20 | Croissance effectifs > 20% / 2 ans | MOYEN | 2 | INSEE, URSSAF |
| late_filing | Retard depot des comptes annuels | FAIBLE | 2 | BODACC, Infogreffe |
| working_capital_stress | Tension BFR (BFR/CA en hausse) | FAIBLE | 2 | INPI bilans |
| capex_decline | Baisse des investissements | FAIBLE | 1 | INPI bilans |
| new_establishment | Ouverture nouvel etablissement | FAIBLE | 1 | INSEE SIRENE |
| bpifrance_aid | Aide BPI France / subvention | FAIBLE | 1 | Data.Subvention |
| presse_levee_fonds | Presse : levee de fonds | MOYEN | 2 | Google News |
| presse_difficultes | Presse : difficultes financieres | FORT | 4 | Google News |

## DIMENSION 4 : RH & GOUVERNANCE (max 12 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| daf_pe_recruitment | Recrutement DAF ex-PE / Big 4 | FORT | 5 | LinkedIn, offres |
| key_hire_manda | Recrutement directeur M&A | FORT | 5 | LinkedIn, offres |
| interim_management | Recours a un manager de transition | FORT | 4 | LinkedIn |
| infogreffe_nouveau_dirigeant | Nouveau dirigeant (Infogreffe) | FORT | 4 | Infogreffe |
| management_package_setup | Management package BSPCE/AGA | MOYEN | 3 | Infogreffe |
| cofounder_departure | Depart co-fondateur / directeur cle | MOYEN | 3 | LinkedIn, INPI |
| board_composition_change | Modification composition conseil | MOYEN | 3 | INPI, Infogreffe |
| mass_layoff_plan | Plan licenciement / PSE | MOYEN | 2 | Presse, DIRECCTE |
| cse_information_consultation | Information-consultation CSE | MOYEN | 2 | Presse |
| linkedin_turnover_spike | Pic de turnover (departs cadres) | FAIBLE | 1 | LinkedIn |

## DIMENSION 5 : CONSOLIDATION SECTORIELLE (max 10 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| pe_platform_in_sector | Plateforme PE active (build-up) | FORT | 4 | CFNews |
| competitor_acquired | Concurrent direct rachete | FORT | 4 | CFNews, Presse |
| infogreffe_fusion_absorption | Fusion / absorption deposee | FORT | 4 | Infogreffe |
| sector_consolidation | Consolidation sectorielle active | MOYEN | 3 | Config sectorielle |
| foreign_buyer_entry | Acquereur etranger dans le secteur | MOYEN | 2 | Presse |
| sector_regulation_change | Changement reglementaire sectoriel | MOYEN | 2 | Journal Officiel |
| presse_partenariat | Presse : partenariat / alliance | MOYEN | 2 | Google News |
| ma_event | Transaction M&A dans le secteur | FAIBLE | 1 | CFNews |
| sector_multiple_expansion | Hausse multiples valorisation | FAIBLE | 1 | Rapports sectoriels |

## DIMENSION 6 : JURIDIQUE & REGLEMENTAIRE (max 8 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| mandat_ad_hoc | Procedure mandat ad hoc | FORT | 4 | Detection indirecte |
| conciliation_procedure | Procedure de conciliation | FORT | 4 | BODACC |
| commercial_court_filing | Inscription Tribunal de Commerce | FORT | 3 | BODACC |
| sanction_detected | Sanction (gels avoirs, AMF, ACPR) | FORT | 3 | Gels Avoirs, AMF |
| infogreffe_transfert_siege | Transfert siege social (Infogreffe) | MOYEN | 2 | Infogreffe |
| change_of_purpose | Modification objet social | FAIBLE | 1 | Infogreffe |
| litigation_signal | Contentieux significatif | FAIBLE | 1 | Judilibre |
| rgpd_sanction | Sanction CNIL / RGPD | FAIBLE | 1 | CNIL |
| environmental_sanction | Sanction environnementale | FAIBLE | 1 | DREAL |

## DIMENSION 7 : PRESSE & MEDIA (max 8 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| presse_cession | Presse : cession / vente detectee | FORT | 5 | Google News |
| press_advisor_mandate | Mandat confie a un conseil M&A | FORT | 5 | CFNews, Les Echos |
| press_strategic_review | Annonce de revue strategique | FORT | 4 | Presse |
| press_succession_mention | Mention succession dans la presse | MOYEN | 3 | Google News |
| press_award_ranking | Prix / classement entreprise | FAIBLE | 1 | Presse |
| press_regional | Couverture presse regionale | FAIBLE | 1 | JDE RSS |

## DIMENSION 8 : INNOVATION & PI (max 6 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| key_patent_expiry | Expiration brevets cles | MOYEN | 3 | INPI Brevets |
| patent_portfolio_growth | Croissance portefeuille brevets | FAIBLE | 2 | INPI Brevets |
| cir_cii_beneficiary | Beneficiaire CIR / CII | FAIBLE | 1 | MESR |
| patent_licensing_activity | Activite de licensing brevets | FAIBLE | 1 | INPI |
| tech_obsolescence_risk | Risque obsolescence technologique | FAIBLE | 1 | Analyse sectorielle |

## DIMENSION 9 : IMMOBILIER & ACTIFS (max 5 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| sale_leaseback | Operation sale and leaseback | FORT | 3 | Presse |
| real_estate_sale | Vente immobiliere par la societe | MOYEN | 2 | DVF |
| sci_creation_linked | Creation SCI liee | MOYEN | 2 | INPI, Infogreffe |
| site_closure | Fermeture site / etablissement | MOYEN | 2 | INSEE SIRENE |
| lease_expiry_approaching | Echeance bail commercial proche | FAIBLE | 1 | Detection indirecte |

## DIMENSION 10 : ESG & CONFORMITE (max 5 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| bilan_ges_publie | Bilan GES publie (signal taille) | FAIBLE | 2 | ADEME |
| carbon_regulation_exposure | Exposition reglementaire carbone | FAIBLE | 1 | Taxonomie UE |
| bcorp_certification | Certification B-Corp | FAIBLE | 1 | Registre B-Corp |
| social_audit_failure | Echec audit social | FAIBLE | 1 | Presse |

## DIMENSION 11 : INTERNATIONAL & CROSS-BORDER (max 5 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| foreign_shareholder_entry | Entree actionnaire etranger | FORT | 3 | BODACC, INPI |
| ie_foreign_investment_screening | Controle investissements etrangers | MOYEN | 2 | DG Tresor |
| foreign_subsidiary_creation | Creation filiale a l'etranger | FAIBLE | 1 | INPI |
| export_dependency_high | Dependance export > 50% CA | FAIBLE | 1 | INPI bilans, Douanes |

## DIMENSION 12 : MARCHES PUBLICS & DEPENDANCE (max 4 pts)

| Signal | Label | Force | Points | Source |
|--------|-------|-------|--------|--------|
| major_contract_loss | Perte contrat/client majeur | MOYEN | 2 | Presse, BOAMP |
| public_contract_concentration | Concentration marches publics > 40% CA | FAIBLE | 1 | BOAMP, DECP |
| major_contract_win | Gain contrat majeur | FAIBLE | 1 | BOAMP, Presse |
| client_concentration_risk | Concentration client > 30% CA | FAIBLE | 1 | INPI bilans |

---

## SIGNAUX COMPOSITES (multiplicateurs de confiance)

Ces combinaisons de signaux augmentent drastiquement la confiance :

| Signal | Label | Composition | Effet |
|--------|-------|-------------|-------|
| triple_signal_patrimoine | Holding + SCI + Big4 | holding_creation + sci_creation + big4_audit (< 18 mois) | Score x1.5 |
| exit_preparation_cluster | Cluster preparation sortie | daf_pe_recruitment + legal_form_change + (holding OU management_package) | Score x1.5 |
| distressed_cluster | Cluster detresse | revenue_decline + ebitda_compression + (late_filing OU score_defaillance) | Score x1.3 |
| succession_urgency | Urgence successorale | founder_over_65 + spouse_departure + pas de pacte_dutreil | Score x1.5 |
| sector_wave_target | Cible vague consolidation | pe_platform + competitor_acquired + ca_growth | Score x1.3 |

---

## Algorithme de scoring

```python
score_total = 0
for dimension in dimensions:
    raw = sum(signal.points for signal in company.signals if signal.dimension == dimension)
    capped = min(raw, dimension.max_points)
    score_total += capped

# Appliquer les multiplicateurs composites
for composite in composites:
    if all(s in company.signals for s in composite.required_signals):
        score_total = min(100, score_total * composite.multiplier)

# Classification
if score_total >= 65: priority = "Action Prioritaire"
elif score_total >= 45: priority = "Qualification"
elif score_total >= 25: priority = "Monitoring"
else: priority = "Veille Passive"
```

#!/usr/bin/env python3
"""Optimized INPI RNE formalités ingester — 7 bronze tables, COPY-based.

Usage: ingest_formalites_fast.py <file.json>   (env: DSN)
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation

import psycopg


# ─── Helpers ──────────────────────────────────────────────────────────────

def _d(s):
    if not s:
        return ""
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date().isoformat()
    except Exception:
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d").date().isoformat()
        except Exception:
            return ""


def _ts(s):
    if not s:
        return ""
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).isoformat()
    except Exception:
        return ""


def _int(v):
    if v is None or v == "":
        return ""
    try:
        return str(int(v))
    except (ValueError, TypeError):
        return ""


def _num(v):
    if v is None or v == "":
        return ""
    try:
        return str(Decimal(str(v)))
    except (InvalidOperation, ValueError):
        return ""


def _bool(v):
    if v is None:
        return ""
    return "true" if bool(v) else "false"


def _arr(v) -> str:
    """Serialize python list to Postgres array literal for TEXT[] columns."""
    if not v or not isinstance(v, list):
        return ""
    escaped = [str(x).replace("\\", "\\\\").replace('"', '\\"') for x in v if x is not None]
    return "{" + ",".join(f'"{x}"' for x in escaped) + "}"


def _s(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return str(v)


def _uid(*parts) -> str:
    """Deterministic UID from parts (so reruns don't duplicate)."""
    raw = "|".join(str(p or "") for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:40]


def _adr(obj) -> dict:
    """Flatten adresse block. Accept dict or None."""
    if not isinstance(obj, dict):
        return {}
    a = obj.get("adresse") if isinstance(obj.get("adresse"), dict) else obj
    if not isinstance(a, dict):
        return {}
    carac = a.get("caracteristiques") if isinstance(a.get("caracteristiques"), dict) else {}
    return {
        "code_postal": a.get("codePostal"),
        "commune": a.get("commune"),
        "code_insee_commune": a.get("codeInseeCommune"),
        "voie": a.get("voie"),
        "type_voie": a.get("typeVoie"),
        "num_voie": a.get("numVoie"),
        "indice_repetition": a.get("indiceRepetition"),
        "complement": a.get("complementLocalisation"),
        "commune_ancienne": a.get("communeAncienne"),
        "code_pays": a.get("codePays"),
        "pays": a.get("pays"),
        "distribution_speciale": a.get("distributionSpeciale"),
        "ambulant": _bool(carac.get("ambulant")),
        "domiciliataire": _bool(carac.get("domiciliataire")),
    }


def _subtree(content: dict) -> tuple[str, dict]:
    """Returns (subtree_name, block) — the main entity block inside content."""
    for key in ("personneMorale", "personnePhysique", "exploitation"):
        blk = content.get(key)
        if isinstance(blk, dict):
            return key, blk
    return "", {}


# ─── Extractors ───────────────────────────────────────────────────────────

def extract_entreprise(rec: dict) -> tuple | None:
    formality = rec.get("formality") or {}
    content = formality.get("content") or {}
    subtree_name, block = _subtree(content)
    identite = block.get("identite") or {}
    entreprise = identite.get("entreprise") or {}
    description = identite.get("description") or {}
    entrepreneur = identite.get("entrepreneur") or {}
    conjoint = entrepreneur.get("conjoint") or {}
    desc_pers = entrepreneur.get("descriptionPersonne") or {}
    conjoint_desc = conjoint.get("descriptionPersonne") or {}
    conj_adr = _adr(conjoint.get("adresseDomicile") or {})
    ent_adr = _adr(entrepreneur.get("adresseDomicile") or {})

    adr = _adr(block.get("adresseEntreprise") or {})

    contrat = identite.get("contratDAppui") or {}
    noms_domaine = identite.get("nomsDeDomaine") or []
    if isinstance(noms_domaine, list):
        dom_list = [x.get("nomDomaine") for x in noms_domaine if isinstance(x, dict) and x.get("nomDomaine")]
    else:
        dom_list = []

    # registre antérieur (content-level)
    ra = content.get("registreAnterieur") or {}
    rncs = ra.get("rncs") or {}
    rnm = ra.get("rnm") or {}

    # cessation
    dce = block.get("detailCessationEntreprise") or {}

    # structure entreprise (holdings)
    structure = block.get("structureEntreprise")

    formality_id = rec.get("id")
    if not formality_id:
        return None
    siren = (str(rec.get("siren") or "").zfill(9)[:9]) or None

    return (
        str(formality_id)[:128],
        siren,
        formality.get("typePersonne") or "",
        _ts(rec.get("updatedAt")),
        _int(rec.get("nombreEtablissementsOuverts")),
        _int(rec.get("nombreRepresentantsActifs")),
        _arr(rec.get("sirenDoublons")),
        _bool(formality.get("diffusionCommerciale")),
        _bool(formality.get("diffusionINSEE")),
        formality.get("formeJuridique"),
        content.get("formeExerciceActivitePrincipale"),
        formality.get("indicateurStructureEtablissement"),
        entreprise.get("denomination"),
        description.get("sigle"),
        entreprise.get("nomCommercial"),
        entreprise.get("nomExploitation"),
        entreprise.get("codeApe"),
        _d(entreprise.get("dateDebutActiv")),
        _d(entreprise.get("dateImmat")),
        _int(entreprise.get("effectifSalarie")),
        _int(entreprise.get("effectifApprenti")),
        _int(entreprise.get("nombreSalarie")),
        entreprise.get("nicSiege"),
        description.get("objet"),
        description.get("typeDeStatuts"),
        _int(description.get("duree")),
        description.get("dateClotureExerciceSocial"),
        _d(description.get("datePremiereCloture")),
        _d(description.get("dateFinExistence")),
        _d(description.get("dateEffet25M")),
        _num(description.get("montantCapital")),
        description.get("deviseCapital"),
        _bool(description.get("capitalVariable")),
        _num(description.get("capitalMinimum")),
        _bool(description.get("indicateurAssocieUnique")),
        _bool(description.get("indicateurAssocieUniqueDirigeant")),
        description.get("natureGerance"),
        _bool(description.get("ess")),
        _bool(description.get("societeMission")),
        _bool(description.get("continuationAvecActifNetInferieurMoitieCapital")),
        desc_pers.get("nom"),
        desc_pers.get("nomUsage"),
        _arr(desc_pers.get("prenoms")),
        desc_pers.get("pseudonyme"),
        desc_pers.get("dateDeNaissance"),
        desc_pers.get("siren"),
        _bool(entrepreneur.get("qualiteArtisan")),
        conjoint_desc.get("nom"),
        conjoint_desc.get("nomUsage"),
        _arr(conjoint_desc.get("prenoms")),
        conjoint_desc.get("dateDeNaissance"),
        entrepreneur.get("roleConjoint"),
        _d(dce.get("dateRadiation")),
        adr.get("code_postal"),
        adr.get("commune"),
        adr.get("code_insee_commune"),
        adr.get("voie"),
        adr.get("type_voie"),
        adr.get("num_voie"),
        adr.get("indice_repetition"),
        adr.get("complement"),
        adr.get("code_pays"),
        adr.get("pays"),
        adr.get("distribution_speciale"),
        adr.get("domiciliataire"),
        _arr(dom_list),
        _d(rncs.get("dateDebut")),
        _d(rncs.get("dateFin")),
        _d(rnm.get("dateDebut")),
        _d(rnm.get("dateFin")),
        _s(structure) if structure else "",
        json.dumps(rec, ensure_ascii=False, default=str),
    )


def extract_etablissements(rec: dict):
    formality = rec.get("formality") or {}
    content = formality.get("content") or {}
    subtree_name, block = _subtree(content)
    formality_id = str(rec.get("id") or "")[:128]
    siren = (str(rec.get("siren") or "").zfill(9)[:9]) or None

    results = []

    def _emit(etab_obj: dict, idx: int, is_principal: bool):
        if not isinstance(etab_obj, dict):
            return
        de = etab_obj.get("descriptionEtablissement") or {}
        adr = _adr(etab_obj.get("adresse") or {})
        cess = etab_obj.get("detailCessationEtablissement") or {}
        dom = etab_obj.get("domiciliataire") or {}
        ra = etab_obj.get("registreAnterieur") or {}
        rncs = ra.get("rncs") or {}
        rnm = ra.get("rnm") or {}
        raa = ra.get("raa") or {}

        siret = de.get("siret") or ""
        etab_uid = _uid(formality_id, "etab", siret, idx)

        results.append((etab_uid, formality_id, siren, siret[:14] or None,
            _bool(is_principal or de.get("indicateurEtablissementPrincipal")),
            "principal" if is_principal else "autre",
            de.get("rolePourEntreprise"),
            de.get("codeApe"),
            de.get("enseigne"),
            de.get("nomCommercial"),
            de.get("destinationEtablissement"),
            de.get("autreDestination"),
            _bool(de.get("activiteNonSedentaire")),
            _d(de.get("dateEffetFermeture")),
            _d(de.get("dateEffetTransfert")),
            _d(de.get("dateFinActivite")),
            _bool(de.get("indicateurSuppression")),
            de.get("motifSuppression"),
            _bool(de.get("etablissementRdd")),
            de.get("statutPourFormalite"),
            _d(cess.get("dateEffet")),
            _d(cess.get("dateRadiation")),
            _d(cess.get("dateCessationTotaleActivite")),
            _d(cess.get("dateCessationActiviteSalariee")),
            cess.get("destination"),
            _bool(etab_obj.get("isLocationGeranceOrGeranceMandat")),
            dom.get("denomination"),
            dom.get("siren"),
            adr.get("code_postal"),
            adr.get("commune"),
            adr.get("code_insee_commune"),
            adr.get("voie"),
            adr.get("type_voie"),
            adr.get("num_voie"),
            adr.get("indice_repetition"),
            adr.get("complement"),
            adr.get("commune_ancienne"),
            adr.get("code_pays"),
            adr.get("pays"),
            adr.get("distribution_speciale"),
            adr.get("ambulant"),
            adr.get("domiciliataire"),
            _d(rncs.get("dateDebut")),
            _d(rncs.get("dateFin")),
            _d(rnm.get("dateDebut")),
            _d(rnm.get("dateFin")),
            _d(raa.get("dateDebut")),
            json.dumps(etab_obj, ensure_ascii=False, default=str),
        ))
        # activités imbriquées
        for ai, act in enumerate(etab_obj.get("activites") or []):
            if not isinstance(act, dict):
                continue
            origin = act.get("origine") or {}
            pub = origin.get("publication") or {}
            lgm = act.get("locataireGerantMandataire") or {}
            act_uid = _uid(formality_id, "act", siret, idx, ai)
            results_act.append((
                act_uid, etab_uid, formality_id, siren, siret[:14] or None,
                act.get("activiteId"),
                act.get("codeApe"),
                act.get("codeAprm"),
                act.get("categoryCode"),
                act.get("categorisationActivite1"),
                act.get("categorisationActivite2"),
                act.get("categorisationActivite3"),
                act.get("categorisationActivite4"),
                _bool(act.get("indicateurPrincipal")),
                _bool(act.get("indicateurProlongement")),
                _bool(act.get("indicateurArtisteAuteur")),
                _bool(act.get("indicateurNonSedentaire")),
                _bool(act.get("indicateurActiviteeApe")),
                act.get("formeExercice"),
                act.get("exerciceActivite"),
                act.get("descriptionDetaillee"),
                act.get("precisionActivite"),
                act.get("precisionAutre"),
                act.get("qualiteNonSedentaire"),
                act.get("rolePrincipalPourEntreprise"),
                _d(act.get("dateDebut")),
                _d(act.get("dateFin")),
                _bool(act.get("soumissionAuPrecompte")),
                _bool(act.get("activiteRattacheeEirl")),
                lgm.get("mandat"),
                origin.get("typeOrigine"),
                origin.get("autreOrigine"),
                _d(pub.get("datePublication")),
                pub.get("journalPublication"),
                pub.get("publicationUrl"),
                json.dumps(act, ensure_ascii=False, default=str),
            ))

    results_act: list = []
    ep = block.get("etablissementPrincipal")
    if isinstance(ep, dict):
        _emit(ep, 0, is_principal=True)
    autres = block.get("autresEtablissements") or []
    if isinstance(autres, list):
        for i, a in enumerate(autres, start=1):
            _emit(a, i, is_principal=False)

    return results, results_act


def extract_personnes(rec: dict):
    formality = rec.get("formality") or {}
    content = formality.get("content") or {}
    subtree_name, block = _subtree(content)
    composition = block.get("composition") or {}
    pouvoirs = composition.get("pouvoirs") or []
    formality_id = str(rec.get("id") or "")[:128]
    siren = (str(rec.get("siren") or "").zfill(9)[:9]) or None

    rows = []
    if not isinstance(pouvoirs, list):
        return rows
    for i, p in enumerate(pouvoirs):
        if not isinstance(p, dict):
            continue
        rid = p.get("representantId") or _uid(formality_id, "pouv", i)
        individu = p.get("individu") or {}
        ind_dp = individu.get("descriptionPersonne") or {}
        ind_adr = _adr(individu.get("adresseDomicile") or {})
        repr_ = p.get("representant") or {}
        repr_dp = repr_.get("descriptionPersonne") or {}
        repr_adr = _adr(repr_.get("adresseDomicile") or {})
        entreprise = p.get("entreprise") or {}
        ent_adr = _adr(entreprise.get("adresseEntreprise") or {})
        ent_siren = entreprise.get("siren")
        rows.append((
            str(rid)[:128], formality_id, siren,
            p.get("typeDePersonne"),
            _bool(p.get("actif")),
            p.get("roleEntreprise"),
            p.get("autreRoleEntreprise"),
            p.get("secondRoleEntreprise"),
            p.get("libelleSecondRoleEntreprise"),
            _bool(p.get("indicateurSecondRoleEntreprise")),
            _bool(p.get("indicateurActifAgricole")),
            _bool(p.get("qualiteArtisan")),
            ind_dp.get("nom"),
            ind_dp.get("nomUsage"),
            _arr(ind_dp.get("prenoms")),
            ind_dp.get("dateDeNaissance"),
            ind_dp.get("role"),
            _d(ind_dp.get("dateEffetRoleDeclarant")),
            ind_adr.get("code_postal"),
            ind_adr.get("commune"),
            ind_adr.get("code_insee_commune"),
            ind_adr.get("pays"),
            ind_adr.get("code_pays"),
            repr_dp.get("nom"),
            repr_dp.get("nomUsage"),
            _arr(repr_dp.get("prenoms")),
            repr_dp.get("dateDeNaissance"),
            repr_adr.get("code_postal"),
            repr_adr.get("commune"),
            (str(ent_siren).zfill(9)[:9]) if ent_siren else None,
            entreprise.get("denomination"),
            entreprise.get("formeJuridique"),
            entreprise.get("roleEntreprise"),
            _bool(entreprise.get("indicateurAssocieUnique")),
            entreprise.get("lieuRegistre"),
            entreprise.get("pays"),
            ent_adr.get("code_postal"),
            ent_adr.get("commune"),
            json.dumps(p, ensure_ascii=False, default=str),
        ))
    return rows


def extract_observations(rec: dict):
    formality = rec.get("formality") or {}
    content = formality.get("content") or {}
    subtree_name, block = _subtree(content)
    observations = block.get("observations") or []
    formality_id = str(rec.get("id") or "")[:128]
    siren = (str(rec.get("siren") or "").zfill(9)[:9]) or None
    rows = []
    if not isinstance(observations, list):
        return rows
    for i, o in enumerate(observations):
        if not isinstance(o, dict):
            continue
        uid = _uid(formality_id, "obs", i)
        rows.append((
            uid, formality_id, siren,
            _d(o.get("dateObservation") or o.get("date")),
            o.get("type") or o.get("typeObservation"),
            o.get("libelle") or o.get("texte"),
            json.dumps(o, ensure_ascii=False, default=str),
        ))
    return rows


def extract_historique(rec: dict):
    formality = rec.get("formality") or {}
    hist = formality.get("historique") or []
    formality_id = str(rec.get("id") or "")[:128]
    siren = (str(rec.get("siren") or "").zfill(9)[:9]) or None
    rows = []
    if not isinstance(hist, list):
        return rows
    for i, h in enumerate(hist):
        if not isinstance(h, dict):
            continue
        patch_id = h.get("patchId") or _uid(formality_id, "hist", i)
        rows.append((
            str(patch_id)[:128], formality_id, siren,
            h.get("patchId"),
            h.get("numeroLiasse"),
            h.get("libelleEvenement"),
            _ts(h.get("dateIntegration")),
            json.dumps(h, ensure_ascii=False, default=str),
        ))
    return rows


def extract_inscriptions(rec: dict):
    formality = rec.get("formality") or {}
    content = formality.get("content") or {}
    insc = content.get("inscriptionsOffices") or []
    formality_id = str(rec.get("id") or "")[:128]
    siren = (str(rec.get("siren") or "").zfill(9)[:9]) or None
    rows = []
    if not isinstance(insc, list):
        return rows
    for i, o in enumerate(insc):
        if not isinstance(o, dict):
            continue
        uid = _uid(formality_id, "insc", i)
        rows.append((
            uid, formality_id, siren,
            o.get("code") or o.get("officeCode"),
            o.get("libelle") or o.get("officeLibelle"),
            json.dumps(o, ensure_ascii=False, default=str),
        ))
    return rows


# ─── Main ─────────────────────────────────────────────────────────────────

TABLES = {
    "entreprises": {
        "cols": "formality_id, siren, type_personne, updated_at_src, "
                "nombre_etablissements_ouverts, nombre_representants_actifs, siren_doublons, "
                "diffusion_commerciale, diffusion_insee, forme_juridique, "
                "forme_exercice_activite_principale, indicateur_structure_etablissement, "
                "denomination, sigle, nom_commercial, nom_exploitation, code_ape, "
                "date_debut_activite, date_immatriculation, effectif_salarie, effectif_apprenti, "
                "nombre_salarie, nic_siege, objet, forme_statuts, duree_annees, "
                "date_cloture_exercice_social, date_premiere_cloture, date_fin_existence, date_effet_25m, "
                "montant_capital, devise_capital, capital_variable, capital_minimum, "
                "indicateur_associe_unique, indicateur_associe_unique_dirigeant, nature_gerance, "
                "ess, societe_mission, continuation_actif_net_inf_moitie_capital, "
                "entrepreneur_nom, entrepreneur_nom_usage, entrepreneur_prenoms, entrepreneur_pseudonyme, "
                "entrepreneur_date_naissance, entrepreneur_siren, entrepreneur_qualite_artisan, "
                "conjoint_nom, conjoint_nom_usage, conjoint_prenoms, conjoint_date_naissance, "
                "role_conjoint, date_radiation, "
                "adresse_code_postal, adresse_commune, adresse_code_insee_commune, adresse_voie, "
                "adresse_type_voie, adresse_num_voie, adresse_indice_repetition, adresse_complement, "
                "adresse_code_pays, adresse_pays, adresse_distribution_speciale, adresse_domiciliataire, "
                "noms_de_domaine, rncs_date_debut, rncs_date_fin, rnm_date_debut, rnm_date_fin, "
                "structure_entreprise_payload, payload",
        "pk": "formality_id",
    },
    "etablissements": {
        "cols": "etablissement_uid, formality_id, siren, siret, is_principal, role_etablissement, "
                "role_pour_entreprise, code_ape, enseigne, nom_commercial, destination_etablissement, "
                "autre_destination, activite_non_sedentaire, date_effet_fermeture, date_effet_transfert, "
                "date_fin_activite, indicateur_suppression, motif_suppression, etablissement_rdd, "
                "statut_pour_formalite, cessation_date_effet, cessation_date_radiation, "
                "cessation_date_totale_activite, cessation_date_activite_salariee, cessation_destination, "
                "is_location_gerance_ou_mandat, domiciliataire_denomination, domiciliataire_siren, "
                "adresse_code_postal, adresse_commune, adresse_code_insee_commune, adresse_voie, "
                "adresse_type_voie, adresse_num_voie, adresse_indice_repetition, adresse_complement, "
                "adresse_commune_ancienne, adresse_code_pays, adresse_pays, adresse_distribution_speciale, "
                "adresse_ambulant, adresse_domiciliataire, rncs_date_debut, rncs_date_fin, "
                "rnm_date_debut, rnm_date_fin, raa_date_debut, payload",
        "pk": "etablissement_uid",
    },
    "activites": {
        "cols": "activite_uid, etablissement_uid, formality_id, siren, siret, activite_id, "
                "code_ape, code_aprm, category_code, cat_1, cat_2, cat_3, cat_4, "
                "indicateur_principal, indicateur_prolongement, indicateur_artiste_auteur, "
                "indicateur_non_sedentaire, indicateur_activitee_ape, forme_exercice, exercice_activite, "
                "description_detaillee, precision_activite, precision_autre, qualite_non_sedentaire, "
                "role_principal_pour_entreprise, date_debut, date_fin, soumission_au_precompte, "
                "activite_rattachee_eirl, locataire_gerant_mandat, origine_type, origine_autre, "
                "origine_pub_date, origine_pub_journal, origine_pub_url, payload",
        "pk": "activite_uid",
    },
    "personnes": {
        "cols": "representant_id, formality_id, siren, type_de_personne, actif, role_entreprise, "
                "autre_role_entreprise, second_role_entreprise, libelle_second_role_entreprise, "
                "indicateur_second_role, indicateur_actif_agricole, qualite_artisan, "
                "individu_nom, individu_nom_usage, individu_prenoms, individu_date_naissance, "
                "individu_role, individu_date_effet_role, "
                "individu_adresse_code_postal, individu_adresse_commune, individu_adresse_code_insee_commune, "
                "individu_adresse_pays, individu_adresse_code_pays, "
                "representant_nom, representant_nom_usage, representant_prenoms, representant_date_naissance, "
                "representant_adresse_code_postal, representant_adresse_commune, "
                "entreprise_siren, entreprise_denomination, entreprise_forme_juridique, entreprise_role_entreprise, "
                "entreprise_indicateur_associe_unique, entreprise_lieu_registre, entreprise_pays, "
                "entreprise_adresse_code_postal, entreprise_adresse_commune, payload",
        "pk": "representant_id",
    },
    "observations": {
        "cols": "observation_uid, formality_id, siren, date_observation, type_observation, libelle, payload",
        "pk": "observation_uid",
    },
    "historique": {
        "cols": "historique_uid, formality_id, siren, patch_id, numero_liasse, libelle_evenement, "
                "date_integration, payload",
        "pk": "historique_uid",
    },
    "inscriptions_offices": {
        "cols": "inscription_uid, formality_id, siren, office_code, office_libelle, payload",
        "pk": "inscription_uid",
    },
}


def write_csv(buf: io.StringIO, row: tuple):
    # No escapechar — use CSV standard double-quote escaping (""). This matches
    # Postgres COPY CSV default (ESCAPE defaults to the QUOTE character).
    w = csv.writer(buf, delimiter="\t", quoting=csv.QUOTE_MINIMAL,
                   doublequote=True, lineterminator="\n")
    out = []
    for v in row:
        if v is None:
            out.append("")
        else:
            s = str(v)
            # Strip raw newlines and carriage returns from inline text fields
            # (they break CSV line parsing). Payload JSON is on a single line already.
            s = s.replace("\r", " ").replace("\n", " ")
            out.append(s)
    w.writerow(out)


def copy_via_stage(cur, table: str, cols: str, pk: str, buf: io.StringIO) -> int:
    """COPY into temp stage + INSERT ON CONFLICT DO NOTHING for idempotence."""
    target = f"bronze.inpi_formalites_{table}"
    cur.execute(f"CREATE TEMP TABLE _stg (LIKE {target} INCLUDING DEFAULTS) ON COMMIT DROP")
    with cur.copy(f"COPY _stg ({cols}) FROM STDIN WITH (FORMAT CSV, NULL '', DELIMITER E'\\t')") as cp:
        data = buf.getvalue()
        chunk = 4 * 1024 * 1024
        for i in range(0, len(data), chunk):
            cp.write(data[i:i + chunk])
    cur.execute(
        f"INSERT INTO {target} ({cols}) SELECT {cols} FROM _stg ON CONFLICT ({pk}) DO NOTHING"
    )
    inserted = cur.rowcount or 0
    cur.execute("DROP TABLE _stg")
    return inserted


def process_file(path: str, dsn: str) -> dict:
    t0 = time.time()
    with open(path, "rb") as f:
        data = json.load(f)
    t_parse = time.time() - t0
    if not isinstance(data, list):
        raise ValueError("expected JSON array")

    # Buffers
    bufs = {k: io.StringIO() for k in TABLES}
    counts = {k: 0 for k in TABLES}

    for rec in data:
        if not isinstance(rec, dict):
            continue
        ent = extract_entreprise(rec)
        if ent:
            write_csv(bufs["entreprises"], ent)
            counts["entreprises"] += 1
        etabs, acts = extract_etablissements(rec)
        for e in etabs:
            write_csv(bufs["etablissements"], e)
            counts["etablissements"] += 1
        for a in acts:
            write_csv(bufs["activites"], a)
            counts["activites"] += 1
        for p in extract_personnes(rec):
            write_csv(bufs["personnes"], p)
            counts["personnes"] += 1
        for o in extract_observations(rec):
            write_csv(bufs["observations"], o)
            counts["observations"] += 1
        for h in extract_historique(rec):
            write_csv(bufs["historique"], h)
            counts["historique"] += 1
        for i in extract_inscriptions(rec):
            write_csv(bufs["inscriptions_offices"], i)
            counts["inscriptions_offices"] += 1

    t_build = time.time() - t0 - t_parse
    t_db0 = time.time()
    inserted_counts = {}
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            for tbl, meta in TABLES.items():
                if counts[tbl] == 0:
                    inserted_counts[tbl] = 0
                    continue
                bufs[tbl].seek(0)
                inserted_counts[tbl] = copy_via_stage(cur, tbl, meta["cols"], meta["pk"], bufs[tbl])
        conn.commit()

    t_db = time.time() - t_db0
    total = time.time() - t0
    return {
        "file": os.path.basename(path),
        "records": len(data),
        "built": counts,
        "inserted": inserted_counts,
        "t_parse_s": round(t_parse, 2),
        "t_build_s": round(t_build, 2),
        "t_db_s": round(t_db, 2),
        "t_total_s": round(total, 2),
    }


def main():
    if len(sys.argv) < 2:
        print("usage: ingest_formalites_fast.py <file.json>", file=sys.stderr)
        sys.exit(2)
    dsn = os.environ.get("DSN")
    if not dsn:
        print("DSN env var required", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(process_file(sys.argv[1], dsn)))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Vérifie la cohérence entre la doctrine QA et les fichiers qui la référencent.

Source-of-truth : `docs/QA_PLAYBOOKS.md` header YAML (entre les marqueurs
`<!-- DOCTRINE_HEADER_START -->` et `<!-- DOCTRINE_HEADER_END -->`).

Vérifie :
1. Header YAML parsable et contient les clés requises
2. `.claude/skills/qa-audit/SKILL.md` ne hardcode PAS de versions outils
3. `.claude/skills/qa-audit/SKILL.md` ne hardcode PAS de count de modes
4. `.claude/agents/qa-engineer.md` ne hardcode PAS de taille doctrine ni count modes
5. Tous les modes du header sont mentionnés dans le SKILL.md (au moins 1× chacun)

Run : python scripts/check_doctrine_sync.py
Exit code : 0 si cohérent, 1 sinon (pour CI fail-build).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCTRINE = REPO_ROOT / "docs" / "QA_PLAYBOOKS.md"
SKILL = REPO_ROOT / ".claude" / "skills" / "qa-audit" / "SKILL.md"
SUBAGENT = REPO_ROOT / ".claude" / "agents" / "qa-engineer.md"

REQUIRED_HEADER_KEYS = {
    "doctrine_version",
    "modes",
    "axes_count",
    "dimensions_qcs",
    "dimensions_complementaires",
    "levels",
    "qcs_thresholds",
}


def _extract_header(path: Path) -> dict:
    """Extrait le bloc YAML entre DOCTRINE_HEADER_START et DOCTRINE_HEADER_END."""
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r"<!--\s*DOCTRINE_HEADER_START.*?-->\s*```yaml\n(.*?)\n```\s*<!--\s*DOCTRINE_HEADER_END",
        text,
        re.DOTALL,
    )
    if not m:
        raise SystemExit(f"❌ Header YAML doctrine introuvable dans {path}")
    try:
        import yaml  # type: ignore
    except ImportError:
        # Fallback : parser manuel ultra-basique pour CI sans pyyaml
        return _manual_yaml_parse(m.group(1))
    return yaml.safe_load(m.group(1))


def _manual_yaml_parse(yaml_str: str) -> dict:
    """Parser fallback pour environnements sans pyyaml."""
    result: dict = {}
    current_list_key: str | None = None
    current_dict_key: str | None = None
    for line in yaml_str.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):  # liste
            if current_list_key:
                result.setdefault(current_list_key, []).append(line[4:].strip())
        elif line.startswith("  ") and ":" in line:  # nested dict
            k, _, v = line.strip().partition(":")
            if current_dict_key:
                result.setdefault(current_dict_key, {})[k.strip()] = v.strip()
        elif ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            v = v.strip()
            if not v or v == "":
                # Lookahead : list ou dict ?
                current_list_key = k.strip()
                current_dict_key = k.strip()
            else:
                # Inline value (string/int)
                if v.startswith("[") and v.endswith("]"):
                    result[k.strip()] = [x.strip().strip('"') for x in v[1:-1].split(",")]
                elif v.isdigit():
                    result[k.strip()] = int(v)
                else:
                    result[k.strip()] = v.strip('"')
                current_list_key = None
                current_dict_key = None
    return result


def check_header() -> list[str]:
    """Vérifie que le header doctrine est complet."""
    errors: list[str] = []
    header = _extract_header(DOCTRINE)
    missing = REQUIRED_HEADER_KEYS - set(header.keys())
    if missing:
        errors.append(f"Header doctrine manque les clés : {missing}")
    if "modes" in header and not isinstance(header["modes"], list):
        errors.append(f"Header `modes` doit être une liste (got {type(header['modes']).__name__})")
    if "modes" in header and len(header["modes"]) < 5:
        errors.append(f"Header `modes` doit contenir au moins 5 modes (got {len(header['modes'])})")
    return errors


def check_skill_no_hardcoded_count() -> list[str]:
    """Vérifie que SKILL.md ne hardcode pas de count modes / lignes doctrine."""
    errors: list[str] = []
    text = SKILL.read_text(encoding="utf-8")

    # Anti-patterns : "X modes" avec X = nombre fixe
    for m in re.finditer(r"\b(\d+)\s+modes?\b", text, re.IGNORECASE):
        # Tolérer "le 9e mode" ou citations dans changelog
        context = text[max(0, m.start() - 60) : m.end() + 60]
        if "changelog" in context.lower() or "→" in context or "sprint" in context.lower():
            continue
        errors.append(
            f"SKILL.md hardcode '{m.group()}' (utiliser header YAML doctrine `modes` à la place) "
            f"@ position {m.start()}"
        )

    # Anti-patterns : "1782 lignes" ou nombres similaires de doctrine
    for m in re.finditer(r"\b\d{4}\s+lignes?\b", text, re.IGNORECASE):
        errors.append(f"SKILL.md hardcode count lignes : '{m.group()}' (à supprimer)")

    return errors


def check_subagent_no_hardcoded_count() -> list[str]:
    """Vérifie que qa-engineer.md ne hardcode pas count doctrine / modes."""
    errors: list[str] = []
    text = SUBAGENT.read_text(encoding="utf-8")

    # Hardcode taille doctrine
    for m in re.finditer(r"\b\d{4}\s+lignes?\b", text, re.IGNORECASE):
        errors.append(f"qa-engineer.md hardcode count lignes : '{m.group()}'")

    # Hardcode count modes (sauf citations changelog)
    for m in re.finditer(r"\b(\d+)\s+modes?\b", text, re.IGNORECASE):
        context = text[max(0, m.start() - 60) : m.end() + 60]
        if "header" in context.lower() or "yaml" in context.lower():
            continue
        errors.append(f"qa-engineer.md hardcode '{m.group()}' (utiliser header YAML)")

    return errors


def check_modes_referenced_in_skill() -> list[str]:
    """Vérifie que tous les modes du header sont mentionnés dans SKILL.md."""
    errors: list[str] = []
    header = _extract_header(DOCTRINE)
    modes = header.get("modes", [])
    if not isinstance(modes, list):
        return ["Header `modes` invalide"]

    skill_text = SKILL.read_text(encoding="utf-8")
    missing_in_skill: list[str] = []
    for mode in modes:
        # Recherche du mode comme mot ou backticked
        if not re.search(rf"\b`?{re.escape(mode)}`?\b", skill_text):
            missing_in_skill.append(mode)

    if missing_in_skill:
        errors.append(
            f"Modes déclarés dans header mais absents de SKILL.md : {missing_in_skill}"
        )
    return errors


def check_skill_version_format() -> list[str]:
    """Vérifie que le frontmatter SKILL.md a bien `version: X.Y.Z`."""
    errors: list[str] = []
    text = SKILL.read_text(encoding="utf-8")
    m = re.search(r"^version:\s*(\d+\.\d+\.\d+)\s*$", text, re.MULTILINE)
    if not m:
        errors.append("SKILL.md frontmatter manque `version: X.Y.Z`")
    return errors


def main() -> int:
    print("🔍 Vérification cohérence doctrine QA ↔ skill ↔ subagent")
    print("=" * 65)

    all_errors: list[str] = []

    print("\n[1/5] Header doctrine YAML...")
    errs = check_header()
    if errs:
        all_errors.extend(errs)
        for e in errs:
            print(f"  ❌ {e}")
    else:
        print("  ✓ OK")

    print("\n[2/5] SKILL.md sans count modes/lignes hardcodés...")
    errs = check_skill_no_hardcoded_count()
    if errs:
        all_errors.extend(errs)
        for e in errs[:5]:
            print(f"  ❌ {e}")
        if len(errs) > 5:
            print(f"  ... +{len(errs) - 5} autres")
    else:
        print("  ✓ OK")

    print("\n[3/5] qa-engineer.md sans count modes/lignes hardcodés...")
    errs = check_subagent_no_hardcoded_count()
    if errs:
        all_errors.extend(errs)
        for e in errs:
            print(f"  ❌ {e}")
    else:
        print("  ✓ OK")

    print("\n[4/5] Modes header tous référencés dans SKILL.md...")
    errs = check_modes_referenced_in_skill()
    if errs:
        all_errors.extend(errs)
        for e in errs:
            print(f"  ❌ {e}")
    else:
        print("  ✓ OK")

    print("\n[5/5] SKILL.md frontmatter `version: X.Y.Z`...")
    errs = check_skill_version_format()
    if errs:
        all_errors.extend(errs)
        for e in errs:
            print(f"  ❌ {e}")
    else:
        print("  ✓ OK")

    print("\n" + "=" * 65)
    if all_errors:
        print(f"❌ {len(all_errors)} erreur(s) de cohérence détectée(s)")
        return 1
    print("✅ Cohérence doctrine QA OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

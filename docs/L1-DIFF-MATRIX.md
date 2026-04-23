# L1 — Diff Matrix (réconciliation latérale Repo ↔ VPS ↔ Mirror)

Template à remplir par l'agent exécutant le Lot L1 du brief v5 (§15).

## État initial (2026-04-23)

| Emplacement | Sources `.py` | Specs `.yaml` |
|---|---:|---:|
| Repo `infrastructure/agents/` (local, develop) | **116** | **110** |
| VPS `/root/DEMOEMA-agents/` | **109** | **96** |
| Mirror local `DEMOEMA-workdir/DEMOEMA-agents/` | 135 | 189 |

## Méthodologie

Pour chaque fichier présent dans **au moins une** des 3 sources :

1. Calculer le hash SHA-1 si présent (`git hash-object <fichier>` pour git-tracked, `sha1sum` sinon).
2. Décider la version canonique selon règles :
   - **Absent repo, présent VPS + mirror avec même hash** → merger dans repo (mirror sert d'intermédiaire si besoin pour gitleaks scan).
   - **Présent partout, hashes différents** → comparer dates modif, comparer contenus, choisir version la plus à jour **avec** feature fonctionnelle.
   - **Absent repo + VPS, présent mirror seulement** → très suspect (probablement obsolète mirror). À archiver hors repo, pas intégré.
   - **Présent repo seulement** → garder, pas d'action (déjà canonique).
   - **Conflit sémantique** (ex : deepseek_client.py drift détecté cf. brief §6.7) → review humaine, trace dans `docs/MERGE_DECISIONS_L1.md`.
3. Compléter la matrice ci-dessous.

## Matrice (à remplir)

| Fichier | Repo | VPS | Mirror | Choisir | Pourquoi | PR/commit |
|---|---|---|---|---|---|---|
| _(exemple)_ `platform/ingestion/sources/eu_sanctions.py` | absent | `abc123` | `abc123` | VPS | présent deux côtés, consistent | L1.1 |
| _(exemple)_ `platform/ingestion/specs/eu_sanctions.yaml` | absent | `xyz789` | `xyz789` | mirror | spec orpheline jamais commit | L1.2 |
| _(exemple)_ `platform/codegen.py` | `aaa111` | `bbb222` | `ccc333` | VPS | version prod la plus récente + bugs fixes | L1.4 |
| _(exemple)_ `platform/deepseek_client.py` | `ddd444` | `eee555` | `fff666` | **CONFLIT** | drift 40% — review humaine | L1.4 manual |

## Commandes pour générer la matrice automatiquement

```bash
# En local, sur la branche chore/audit-fix + après checkout develop pull
cd C:/Users/zkhch/DEMOEMA
find infrastructure/agents -type f \( -name "*.py" -o -name "*.yaml" \) | sort > /tmp/repo-files.txt

# VPS
ssh -i ~/.ssh/id_ed25519 root@82.165.242.205 '\
  find /root/DEMOEMA-agents -type f \( -name "*.py" -o -name "*.yaml" \) \
  -not -path "*/secrets/*" -not -path "*/__pycache__/*" \
  | sed "s|/root/DEMOEMA-agents/|infrastructure/agents/|" \
  | sort' > /tmp/vps-files.txt

# Mirror
find C:/Users/zkhch/DEMOEMA-workdir/DEMOEMA-agents -type f \( -name "*.py" -o -name "*.yaml" \) \
  -not -path "*/secrets/*" -not -path "*/__pycache__/*" \
  | sed 's|.*DEMOEMA-agents/|infrastructure/agents/|' \
  | sort > /tmp/mirror-files.txt

# Union
cat /tmp/repo-files.txt /tmp/vps-files.txt /tmp/mirror-files.txt | sort -u > /tmp/all-files.txt

# Construire la matrice
while read f; do
  repo_hash=$(test -f "$f" && git hash-object "$f" 2>/dev/null || echo "-")
  vps_hash=$(ssh root@82.165.242.205 "test -f /root/DEMOEMA-agents/${f#infrastructure/agents/} && git hash-object /root/DEMOEMA-agents/${f#infrastructure/agents/} 2>/dev/null || echo -")
  mirror_hash=$(test -f "C:/Users/zkhch/DEMOEMA-workdir/DEMOEMA-agents/${f#infrastructure/agents/}" && git hash-object "C:/Users/zkhch/DEMOEMA-workdir/DEMOEMA-agents/${f#infrastructure/agents/}" 2>/dev/null || echo "-")
  printf "| %s | %s | %s | %s | _TBD_ | _TBD_ | _TBD_ |\n" "$f" "$repo_hash" "$vps_hash" "$mirror_hash"
done < /tmp/all-files.txt > /tmp/diff-matrix-raw.md

# Coller le résultat dans la section "Matrice" ci-dessus, puis remplir les 3 dernières colonnes par review.
```

## Estimation effort

- Génération matrice raw (script ci-dessus) : 15 min.
- Review + décision par fichier : ~15 sec / fichier × ~200 fichiers = **~50 min**.
- Merge commits L1.1-L1.6 : ~3h.
- **Total L1** : **~4-5h** (aligne brief v5 estimation raw 12h / réaliste 30h — la matrice + review est la partie longue).

## Sub-commits de L1

- **L1.1** : `platform/ingestion/sources/` (~40 nouveaux)
- **L1.2** : `platform/ingestion/specs/` (~94 YAML)
- **L1.3** : silver layer (`platform/ingestion/silver_*`)
- **L1.4** : mise à jour `platform/codegen.py`, `deepseek_client.py` (résolution drift §6.7 brief)
- **L1.5** : docs techniques → `infrastructure/agents/docs/` (ETAT_REEL, DEPLOYMENT_RUNBOOK, ARCHITECTURE_TECHNIQUE, ARCHITECTURE_DATA_V2, CLEANUP_LOG, DECISIONS_VALIDEES, INGESTION_AGENTS, DATACATALOG)
- **L1.6** : consolidation `docs/` vs `infrastructure/agents/docs/` — supprimer doublons, 1 index

Docs business (FINANCES_UNIFIE, PITCH_DECK, etc.) : **NE PAS** commit — rester VPS-only. Créer `infrastructure/agents/docs/business/.gitkeep` avec README qui redirige.

## Post-L1

Sur le VPS, remplacer `/root/DEMOEMA-agents/` par symlink vers `/root/DEMOEMA/infrastructure/agents/` (ou supprimer). Plus de divergence possible ensuite.

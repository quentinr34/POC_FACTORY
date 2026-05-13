---
name: factory-report
description: Produit un compte-rendu structuré (CR) après toute exécution dans le contexte de la CGI Factory (POC_FACTORY) et met à jour factory-state.json. Déclenche cette skill à la fin de chaque exécution d'une autre skill factory-* (new-project, speckit-setup, speckit-specify, speckit-plan, speckit-tasks, speckit-implement, git-commit-push, deploy-cloud-run), ou dès que Cowork demande explicitement "produit un factory report" / "fais un CR factory" / "termine cette tâche par un rapport factory". Ce CR est OBLIGATOIRE pour que Cowork puisse restituer l'avancement à l'utilisateur. Ne jamais sauter cette étape.
---

# Factory Report — v1.3

Cette skill est la couche de communication entre Claude Code (exécuteur) et Cowork (orchestrateur user-facing). Sans CR structuré, Cowork ne peut pas restituer proprement l'avancement.

**Nouveautés v1.3** :
- Lecture des marqueurs `[FACTORY_PROGRESS]` depuis `logs/<task_id>.claude-stdout.log` (au lieu de `logs/<task_id>.log` en v1.2). Cohérence avec la nouvelle convention de nommage v3.1 où Cowork redirige le stdout de Claude Code dans ce fichier via `Start-Process`.
- Le reste de v1.2 (UTF-8 forcé, enrichissement CR avec durées par étape, écriture atomique) est conservé.

## Chemin canonique de la factory

```
C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY\
```

Toutes les commandes DOIVENT être exécutées depuis cette racine. Tous les chemins manipulés sont **relatifs** à cette racine.

## Quand utiliser cette skill

1. **Automatique en fin de skill factory-*** : toute autre skill du namespace `factory-*` doit invoquer `factory-report` comme dernière étape.
2. **Explicite via brief** : si Cowork ajoute "Termine par un factory report" ou équivalent.
3. **Récupération manuelle** : si une exécution s'est terminée sans CR, invoquer cette skill avec les inputs disponibles.

## Inputs attendus

- **phase** : `new-project | speckit-setup | specify | plan | tasks | implement | commit | deploy | other`
- **project** : nom du projet (ex: `POC_FACTORY`, `demo/<nom>`). Défaut : `POC_FACTORY`.
- **task_slug** : description courte kebab-case. Si absent, générer depuis phase + action.
- **brief_path** : chemin relatif vers le brief Cowork. `null` si invocation manuelle.
- **status** : `success | partial | failed | blocked` — déterminé par l'exécution réelle.
- **task_id** (optionnel mais fortement recommandé) : si fourni par la skill appelante, réutiliser cet ID pour aligner avec `logs/<task_id>.claude-stdout.log`. Sinon, en générer un nouveau (et la lecture du log de progression ne sera pas possible).

## Étapes d'exécution

### 1. Construire ou récupérer le task_id

Si `task_id` est fourni en input : le réutiliser tel quel.

Sinon, en générer un nouveau :

```
<ISO-8601-local>_<phase>_<task-slug>
```

Exemple : `2026-05-13T17-32-00_new-project_bootstrap-hello-factory-v3`

```powershell
$timestamp = (Get-Date -Format "yyyy-MM-ddTHH-mm-ss")
$TASK_ID = "${timestamp}_${PHASE}_${TASK_SLUG}"
```

### 2. Lire le log de progression (CORRIGÉ v1.3)

Vérifier si `logs/<task_id>.claude-stdout.log` existe (nouveau chemin v1.3, au lieu de `logs/<task_id>.log` en v1.2).

Si oui, le parser pour extraire :

- **start_time** : timestamp du premier marqueur `[FACTORY_PROGRESS] step=1/N status=started`
- **end_time** : timestamp du dernier marqueur `[FACTORY_PROGRESS] step=N/N status=done`
- **duration_seconds** : différence
- **steps_durations** : pour chaque step, sa durée

Format attendu :

```
[FACTORY_PROGRESS] step=1/10 phase=preconditions status=started ts=2026-05-13T15:00:00+02:00
[FACTORY_PROGRESS] step=1/10 phase=preconditions status=done ts=2026-05-13T15:00:02+02:00 duration=2s
```

Lecture sûre en PowerShell (ne pas lock le fichier en exclusif — utiliser FileShare.ReadWrite) :

```powershell
$logPath = "logs\$TASK_ID.claude-stdout.log"
if (Test-Path $logPath) {
    $fs = [System.IO.File]::Open($logPath, 'Open', 'Read', 'ReadWrite')
    $reader = New-Object System.IO.StreamReader($fs, [System.Text.UTF8Encoding]::new($false))
    $content = $reader.ReadToEnd()
    $reader.Close()
    $fs.Close()
    $progressLines = $content -split "`n" | Where-Object { $_ -match "^\[FACTORY_PROGRESS\]" }
    # ... parser les durées ...
}
```

Si le log n'existe pas (invocation manuelle), passer cette étape — durations resteront `—`.

### 3. Collecter métadonnées d'exécution

- **commands_executed** : liste des commandes shell significatives (git, gcloud, gh, specify, docker, npm). Pas de `ls`, `cat`, `cd`.
- **files_changed** : utiliser `git status --porcelain` ou `git diff --stat HEAD~1`.

### 4. Identifier fichiers modifiés (détail)

Pour chaque fichier : `path` (relatif POC_FACTORY, séparateur `/`), `action` (created/modified/deleted/renamed), `lines_delta` (lignes ajoutées/supprimées).

Si >20 fichiers : grouper par dossier.

### 5. Rédiger le CR markdown

Template EXACT :

```markdown
# Factory Report — <task_id>

**Date** : <ISO-8601 avec timezone>
**Project** : <project>
**Phase** : <phase>
**Brief** : <brief_path ou "—" si aucun>
**Status** : <success | partial | failed | blocked>
**Duration** : <X>s (ou "—" si inconnu)

## Ce qui a été fait

<3 à 8 puces, faits concrets, voix active.>

## Fichiers modifiés / créés

<liste formatée comme étape 4, ou "Aucun">

## Décisions techniques prises

<2 à 5 puces, décision + justification. "Aucune décision structurante" si rien.>

## Commandes exécutées

```bash
<commandes significatives, secrets masqués par "***">
```

## Progression par étape (v1.3)

<Tableau si log disponible, sinon "Log de progression non disponible (invocation manuelle ou skill sans instrumentation).">

| # | Étape | Statut | Durée |
|---|---|---|---|
| 1 | preconditions | done | 2s |
| ... | ... | ... | ... |

Durée totale wall-clock : <X>s.

## Blocages / questions ouvertes

<liste ou "Aucun">

## Prochaine étape suggérée

<1 phrase actionnable pour Cowork.>

## État mis à jour dans factory-state.json

```json
<diff JSON des champs modifiés uniquement>
```
```

**Règles de rédaction** :

- Pas d'emoji, pas de markdown décoratif inutile.
- Tout en français, sauf noms techniques.
- Max 100 lignes.
- Honnêteté : `partial` exact préféré à `success` optimiste.

### 6. Patcher factory-state.json

Lire `state/factory-state.json`. Si absent, créer :

```json
{
  "factory_version": "0.1",
  "last_updated": null,
  "projects": {},
  "recent_reports": []
}
```

#### 6.a — `last_updated`

Toujours, vers le `end_time` du CR.

#### 6.b — Clé du projet

Si absent, ajouter avec structure standard (8 phases en `pending`, github_repo et cloud_run_url à `null`).

Puis mettre à jour la phase :

- `success` → `status: done`, `completed_at`, `report: reports/<task_id>.md`, `duration_seconds: <X>`
- `partial` → `status: in-progress`, `started_at`, `last_report`, `duration_seconds`
- `failed` → `status: failed`, `failed_at`, `report`, `duration_seconds`
- `blocked` → `status: blocked`, `blocked_at`, `report`

#### 6.c — Champs spécifiques par phase

| Phase | Champ | Source |
|---|---|---|
| `new-project` | `github_repo` | URL du sous-dossier sur GitHub |
| `deploy` | `cloud_run_url` | URL `gcloud run deploy` |
| `commit` | `last_commit_sha` | `git rev-parse HEAD` |
| `commit` | `last_pr_url` | URL `gh pr create` si PR ouverte |

#### 6.d — `recent_reports`

Ajouter `reports/<task_id>.md` en TÊTE, tronquer à 20 entrées.

#### 6.e — Écriture atomique UTF-8

```bash
python -c "
import json, os
STATE = 'state/factory-state.json'
with open(STATE, 'r', encoding='utf-8') as f:
    state = json.load(f)
# ... appliquer les modifications ...
tmp_path = STATE + '.tmp'
with open(tmp_path, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(state, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, STATE)
"
```

### 7. Écrire le CR markdown sur disque (UTF-8 sans BOM)

Chemin : `reports/<task_id>.md`.

```powershell
[System.IO.File]::WriteAllText("reports\$TASK_ID.md", $content, [System.Text.UTF8Encoding]::new($false))
```

### 8. Confirmer la complétion

Afficher EXACTEMENT en stdout :

```
FACTORY_REPORT_WRITTEN=reports/<task_id>.md
FACTORY_STATE_UPDATED=state/factory-state.json
```

## Edge cases

- **state corrompu** : backup `state/factory-state.json.broken.<timestamp>` puis nouveau state vide. Mentionner dans Blocages.
- **Phase inconnue** : utiliser `other`, préciser dans "Ce qui a été fait".
- **Bootstrap POC_FACTORY** : `project=POC_FACTORY`, phase `new-project`.
- **Log de progression absent** (NOUVEAU v1.3) : section "Progression par étape" remplie avec "Log de progression non disponible". Pas bloquant.
- **Log de progression locké par Cowork** (NOUVEAU v1.3) : utiliser `FileShare.ReadWrite` pour lire sans verrouiller. Si malgré tout l'ouverture échoue : noter "Log inaccessible (lock concurrent)" dans la section Progression et continuer.
- **Tâche sans modif fichiers** : "Aucun" dans Fichiers.
- **Secrets** : masquer par `***`.
- **Mauvais cwd** : `cd C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY` en début.

## Exemple section "Progression par étape" enrichie

```markdown
## Progression par étape

| # | Étape | Statut | Durée |
|---|---|---|---|
| 1 | preconditions | done | 2s |
| 2 | scaffold-dir | done | 1s |
| 3 | vite-scaffold | done | 36s |
| 4 | backend-fastapi | done | 3s |
| 5 | dockerfile | done | 2s |
| 6 | config-files | done | 3s |
| 7 | gcp-apis | done | 11s |
| 8 | cd-root | done | 0s |
| 9 | git-commit-push | done | 6s |
| 10 | invoke-report | done | 4s |

Durée totale wall-clock : 68 secondes.
```

## Anti-patterns

- Réécrire le state entier au lieu de patcher.
- `status: success` alors qu'un test a échoué.
- Secrets en clair dans Commandes.
- CR sans patch state ou patch state sans CR — toujours les deux.
- Dépasser 100 lignes.
- Chemins absolus dans CR ou state.json.
- Encoder en CP-1252 ou avec BOM UTF-8.
- Ignorer le log de progression quand il existe.
- **NOUVEAU v1.3 : ouvrir le claude-stdout.log avec un mode qui lock en exclusif** — toujours `FileShare.ReadWrite`. Cowork peut être en train d'écrire dedans en parallèle.
- **NOUVEAU v1.3 : chercher le log sous l'ancien chemin `logs/<task_id>.log`** — le bon chemin est maintenant `logs/<task_id>.claude-stdout.log`.

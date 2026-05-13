---
name: factory-report
description: Produit un compte-rendu structuré (CR) après toute exécution dans le contexte de la CGI Factory (POC_FACTORY) et met à jour factory-state.json. Déclenche cette skill à la fin de chaque exécution d'une autre skill factory-* (new-project, speckit-setup, speckit-specify, speckit-plan, speckit-tasks, speckit-implement, git-commit-push, deploy-cloud-run), ou dès que Cowork demande explicitement "produit un factory report" / "fais un CR factory" / "termine cette tâche par un rapport factory". Déclenche aussi automatiquement si le filesystem contient un dossier POC_FACTORY/ avec un sous-dossier briefs/ et qu'une action Claude Code vient de s'achever — ce CR est OBLIGATOIRE pour que Cowork puisse restituer l'avancement à l'utilisateur. Ne jamais sauter cette étape même si la tâche est petite ou triviale.
---

# Factory Report — v1.2

Cette skill est la couche de communication entre Claude Code (exécuteur) et Cowork (orchestrateur user-facing) dans la CGI Factory. Sans CR structuré, Cowork ne peut pas restituer proprement l'avancement à l'utilisateur, et la traçabilité de la démo s'effondre.

**Nouveautés v1.2** : encodage UTF-8 forcé pour le CR et le state, enrichissement automatique du CR avec les durées par étape lues depuis le log de progression (`logs/<task_id>.log`) si disponible.

## Chemin canonique de la factory

```
C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY\
```

Toutes les commandes de cette skill DOIVENT être exécutées depuis cette racine (`cd` au démarrage si nécessaire). Tous les chemins manipulés sont **relatifs** à cette racine.

## Quand utiliser cette skill

Trois cas de déclenchement :

1. **Automatique en fin de skill factory-*** : toute autre skill du namespace `factory-*` doit invoquer `factory-report` comme dernière étape.
2. **Explicite via brief** : si Cowork ajoute "Termine par un factory report" ou équivalent.
3. **Récupération manuelle** : si une exécution s'est terminée sans CR (bug, interruption), invoquer cette skill avec les inputs disponibles.

## Inputs attendus

- **phase** : `new-project | speckit-setup | specify | plan | tasks | implement | commit | deploy | other`
- **project** : nom du projet (ex: `POC_FACTORY`, `demo/<nom>`). Défaut : `POC_FACTORY`.
- **task_slug** : description courte en kebab-case (ex: `bootstrap-hello-factory-v2`). Si absent, générer depuis phase + action.
- **brief_path** : chemin relatif vers le brief Cowork. `null` si invocation manuelle.
- **status** : `success | partial | failed | blocked` — déterminé par l'exécution réelle.
- **task_id** (optionnel) : si fourni par la skill appelante, réutiliser cet ID pour aligner avec le log de progression. Sinon, en générer un nouveau.

## Étapes d'exécution

### 1. Construire ou récupérer le task_id

Si `task_id` est fourni en input (cas où une skill factory-* a déjà créé un log de progression sous ce nom) : le réutiliser tel quel.

Sinon, générer un nouveau task_id :

```
<ISO-8601-local>_<phase>_<task-slug>
```

Exemple : `2026-05-13T15-32-00_new-project_bootstrap-hello-factory-v2`

Sous PowerShell :

```powershell
$timestamp = (Get-Date -Format "yyyy-MM-ddTHH-mm-ss")
$TASK_ID = "${timestamp}_${PHASE}_${TASK_SLUG}"
```

### 2. Lire le log de progression si disponible (NOUVEAU v1.2)

Vérifier si `logs/<task_id>.log` existe. Si oui, le parser pour extraire :

- **start_time** : horodatage du premier marqueur `[FACTORY_PROGRESS] step=1/N status=started`
- **end_time** : horodatage du dernier marqueur `[FACTORY_PROGRESS] step=N/N status=done`
- **duration_seconds** : différence entre les deux
- **steps_durations** : pour chaque step, sa durée si `status=done` est présent

Format des marqueurs attendus dans le log :

```
[FACTORY_PROGRESS] step=1/10 phase=preconditions status=started ts=2026-05-13T15:00:00+02:00
[FACTORY_PROGRESS] step=1/10 phase=preconditions status=done ts=2026-05-13T15:00:02+02:00 duration=2s
[FACTORY_PROGRESS] step=2/10 phase=scaffold-dir status=started ts=2026-05-13T15:00:02+02:00
...
```

Si le log n'existe pas (cas d'invocation manuelle), passer cette étape — durations resteront `—`.

### 3. Collecter les métadonnées d'exécution complémentaires

- **commands_executed** : liste des commandes shell significatives (git, gcloud, gh, specify, docker, npm). Ne pas inclure les `ls`, `cat`, `cd`.
- **files_changed** : liste des fichiers créés/modifiés/supprimés. Utiliser `git status --porcelain` ou `git diff --stat HEAD~1` pour avoir un état fiable.

### 4. Identifier les fichiers modifiés (détail)

Pour chaque fichier : `path` (relatif POC_FACTORY, séparateur `/`), `action` (created/modified/deleted/renamed), `lines_delta` (lignes ajoutées/supprimées).

Si plus de 20 fichiers : grouper par dossier et indiquer le nombre.

### 5. Rédiger le CR markdown

Utiliser EXACTEMENT ce template (sections obligatoires, ordre fixe) :

```markdown
# Factory Report — <task_id>

**Date** : <ISO-8601 avec timezone>
**Project** : <project>
**Phase** : <phase>
**Brief** : <brief_path ou "—" si aucun>
**Status** : <success | partial | failed | blocked>
**Duration** : <X>s (ou "—" si inconnu)

## Ce qui a été fait

<3 à 8 puces, faits concrets, voix active. Pas de "j'ai essayé". Si étape échouée, le dire dans Blocages.>

## Fichiers modifiés / créés

<liste formatée comme étape 4, ou "Aucun" si rien>

## Décisions techniques prises

<2 à 5 puces, chaque décision suivie d'une justification courte. "Aucune décision structurante" si rien.>

## Commandes exécutées

```bash
<commandes significatives, secrets masqués par "***">
```

## Progression par étape (v1.2)

<Si log de progression dispo : tableau avec étape, statut, durée. Sinon : "Log de progression non disponible (invocation manuelle ou skill sans instrumentation).">

| # | Étape | Statut | Durée |
|---|---|---|---|
| 1 | preconditions | done | 2s |
| 2 | scaffold-dir | done | 1s |
| 3 | vite-scaffold | done | 342s |
| ... | ... | ... | ... |

## Blocages / questions ouvertes

<liste ou "Aucun">

## Prochaine étape suggérée

<1 phrase actionnable pour Cowork.>

## État mis à jour dans factory-state.json

```json
<diff JSON des champs modifiés uniquement, pas le state entier>
```
```

**Règles de rédaction** :

- Pas d'emoji, pas de markdown décoratif inutile.
- Tout en français, sauf les noms techniques (chemins, commandes, identifiants).
- Max 100 lignes (relevé v1.2 de 80 à 100 pour accommoder le tableau progression). Si plus long, tâche trop grosse.
- Honnêteté : préférer `status: partial` exact à `success` optimiste.

### 6. Patcher factory-state.json

Lire `state/factory-state.json`. S'il n'existe pas, le créer :

```json
{
  "factory_version": "0.1",
  "last_updated": null,
  "projects": {},
  "recent_reports": []
}
```

Modifications :

#### 6.a — `last_updated`

Toujours, vers le `end_time` du CR.

#### 6.b — Clé du projet

Si projet absent, l'ajouter avec la structure standard (8 phases en `pending`, github_repo et cloud_run_url à `null`).

Puis mettre à jour la phase concernée :

- `success` → `status: done`, `completed_at`, `report: reports/<task_id>.md`, `duration_seconds: <X>` (NOUVEAU v1.2)
- `partial` → `status: in-progress`, `started_at`, `last_report`, `duration_seconds`
- `failed` → `status: failed`, `failed_at`, `report`, `duration_seconds`
- `blocked` → `status: blocked`, `blocked_at`, `report`

#### 6.c — Champs spécifiques par phase

| Phase | Champ | Source |
|---|---|---|
| `new-project` | `github_repo` | URL du sous-dossier du projet sur GitHub |
| `deploy` | `cloud_run_url` | URL `gcloud run deploy` |
| `commit` | `last_commit_sha` | `git rev-parse HEAD` |
| `commit` | `last_pr_url` | URL `gh pr create` si PR ouverte |

#### 6.d — `recent_reports`

Ajouter `reports/<task_id>.md` en TÊTE, tronquer à 20 entrées.

#### 6.e — Écriture atomique UTF-8 (RENFORCÉ v1.2)

CRITIQUE : utiliser explicitement l'encodage UTF-8 sans BOM pour éviter la corruption des accents.

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

Le `newline='\n'` force LF même sur Windows pour cohérence cross-platform.

### 7. Écrire le CR markdown sur disque (UTF-8 forcé v1.2)

Chemin : `reports/<task_id>.md` (créer le dossier si besoin).

CRITIQUE : encodage UTF-8 sans BOM. Sous Windows, NE PAS utiliser `Out-File` sans `-Encoding utf8` car PowerShell 5 écrit en CP-1252 par défaut. Utiliser Python pour garantir l'encodage :

```bash
python -c "
content = '''<contenu du CR>'''
with open('reports/<task_id>.md', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
"
```

Ou alternative PowerShell sûre :

```powershell
[System.IO.File]::WriteAllText("reports\<task_id>.md", $content, [System.Text.UTF8Encoding]::new($false))
```

Le `$false` exclut le BOM.

### 8. Confirmer la complétion

À la fin, afficher EXACTEMENT en stdout (et rien d'autre que ce qui les concerne) :

```
FACTORY_REPORT_WRITTEN=reports/<task_id>.md
FACTORY_STATE_UPDATED=state/factory-state.json
```

Cowork parse ces marqueurs pour savoir que le CR est dispo. Chemins relatifs à la racine factory.

## Edge cases

- **state corrompu** : backup `state/factory-state.json.broken.<timestamp>` puis nouveau state vide. Mentionner dans Blocages.
- **Phase inconnue** : utiliser `other`, préciser la phase réelle dans "Ce qui a été fait".
- **Bootstrap POC_FACTORY** : `project=POC_FACTORY`, phase `new-project`.
- **Log de progression absent** : section "Progression par étape" remplie avec "Log de progression non disponible". Pas bloquant.
- **Tâche sans modif fichiers** : "Aucun" dans Fichiers, expliquer dans "Ce qui a été fait".
- **Secrets** : toujours masquer (`GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, etc.) par `***`.
- **Mauvais cwd** : `cd C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY` en début.
- **Encodage cassé** (NOUVEAU v1.2) : si un caractère accentué apparaît sous forme `Ã©` ou `â€™` dans le CR, c'est un bug d'encodage — relire le source et le réécrire en UTF-8 explicite.

## Exemple de section "Progression par étape" enrichie

Quand `logs/<task_id>.log` est disponible :

```markdown
## Progression par étape

| # | Étape | Statut | Durée |
|---|---|---|---|
| 1 | preconditions | done | 2s |
| 2 | scaffold-dir | done | 1s |
| 3 | vite-scaffold | done | 342s |
| 4 | backend-fastapi | done | 1s |
| 5 | dockerfile | done | 1s |
| 6 | config-files | done | 1s |
| 7 | gcp-apis | done | 18s |
| 8 | cd-root | done | 0s |
| 9 | git-commit-push | done | 12s |
| 10 | invoke-report | done | 4s |

Durée totale : 382 secondes (~6 minutes 22).
```

## Anti-patterns à éviter

- Réécrire le state entier au lieu de patcher (risque d'écrasement concurrent).
- `status: success` alors qu'un test a échoué — `partial` + explication.
- Secrets en clair dans Commandes — masquer.
- CR sans patch state ou patch state sans CR — toujours les deux ensemble.
- Dépasser 100 lignes — signal de tâche trop grosse.
- Chemins absolus dans CR ou state.json — toujours relatifs à la racine factory.
- **Encoder en CP-1252 ou avec BOM UTF-8** (NOUVEAU v1.2) — toujours UTF-8 sans BOM, sinon les accents et les liens cassent partout.
- **Ignorer le log de progression quand il existe** — toujours l'enrichir dans le CR.

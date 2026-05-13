---
name: factory-report
description: Produit un compte-rendu structuré (CR) après toute exécution dans le contexte de la CGI Factory (POC_FACTORY) et met à jour factory-state.json. Déclenche cette skill à la fin de chaque exécution d'une autre skill factory-* (new-project, speckit-setup, speckit-specify, speckit-plan, speckit-tasks, speckit-implement, git-commit-push, deploy-cloud-run), ou dès que Cowork demande explicitement "produit un factory report" / "fais un CR factory" / "termine cette tâche par un rapport factory". Déclenche aussi automatiquement si le filesystem contient un dossier POC_FACTORY/ avec un sous-dossier briefs/ et qu'une action Claude Code vient de s'achever — ce CR est OBLIGATOIRE pour que Cowork puisse restituer l'avancement à l'utilisateur. Ne jamais sauter cette étape même si la tâche est petite ou triviale.
---

# Factory Report

Cette skill est la couche de communication entre Claude Code (exécuteur) et Cowork (orchestrateur user-facing) dans la CGI Factory. Sans CR structuré, Cowork ne peut pas restituer proprement l'avancement à Quentin, et la traçabilité de la démo s'effondre. Donc à chaque fin d'exécution factory, on produit un CR et on met à jour l'état.

## Quand utiliser cette skill

Trois cas de déclenchement :

1. **Automatique en fin de skill factory-*** : toute autre skill du namespace `factory-*` doit invoquer `factory-report` comme dernière étape de son exécution.
2. **Explicite via brief** : si Cowork ajoute "Termine par un factory report" ou équivalent dans son brief, on invoque cette skill.
3. **Récupération manuelle** : si une exécution s'est terminée sans CR (bug, interruption), on peut invoquer cette skill avec les inputs disponibles pour reconstruire un CR a posteriori.

## Inputs attendus

Le brief ou l'invocation doit fournir (explicitement ou inférables du contexte) :

- **phase** : une parmi `new-project | speckit-setup | specify | plan | tasks | implement | commit | deploy | other`
- **project** : nom du projet (ex: `POC_FACTORY` pour les actions sur la factory elle-même, `demo/<nom>` pour un projet généré). Si absent, par défaut `POC_FACTORY`.
- **task_slug** : description courte de la tâche en kebab-case (ex: `bootstrap-poc-factory`, `init-speckit-avis-summarizer`). Si absent, en générer un depuis la phase et l'action principale.
- **brief_path** : chemin vers le brief Cowork qui a déclenché l'exécution (ex: `briefs/2026-05-13T14-30-00_new-project.md`). Si l'action n'a pas de brief (ex: action manuelle), mettre `null`.
- **status** : `success | partial | failed | blocked` — déterminé par l'exécution réelle, pas par optimisme.

## Étapes d'exécution

### 1. Construire l'identifiant de la tâche

Format strict pour le `task_id` (= nom du fichier de rapport) :

```
<ISO-8601-local>_<phase>_<task-slug>
```

Exemple : `2026-05-13T14-32-00_new-project_bootstrap-poc-factory`

Où :
- `ISO-8601-local` utilise des tirets dans la partie heure pour éviter les `:` (incompatibles avec certains FS Windows) : `2026-05-13T14-32-00`
- `phase` est la valeur exacte de l'input `phase`
- `task-slug` est en kebab-case, max 50 caractères

Récupérer la date/heure locale via `date -Iseconds` puis remplacer les `:` par des `-` :

```bash
TASK_ID="$(date -Iseconds | sed 's/:/-/g' | sed 's/+.*//')_${PHASE}_${TASK_SLUG}"
```

### 2. Collecter les métadonnées d'exécution

Variables à capturer :

- **start_time** : début de l'exécution (passé par Claude Code, sinon `null`)
- **end_time** : maintenant, en ISO 8601 avec timezone
- **duration_seconds** : `end_time - start_time` si les deux disponibles, sinon `null`
- **commands_executed** : liste des commandes shell significatives (git, gcloud, gh, specify, docker, etc.). Ne pas inclure les `ls`, `cat`, `cd` triviaux.
- **files_changed** : liste des fichiers créés/modifiés/supprimés. Si le projet est sous git, utiliser `git status --porcelain` ou `git diff --stat HEAD` pour avoir un état fiable. Sinon, énumérer manuellement depuis les write/edit effectués.

### 3. Identifier les fichiers modifiés (détail)

Pour chaque fichier de la liste, capturer :

- **path** : chemin relatif au dossier POC_FACTORY
- **action** : `created | modified | deleted | renamed`
- **lines_delta** : pour `created`, le nombre de lignes ; pour `modified`, `+X / -Y` ; pour `deleted`, `-Z`

Exemple :

```
- demo/avis-summarizer/backend/main.py (created, 142 lines)
- demo/avis-summarizer/README.md (modified, +23 / -5)
- demo/avis-summarizer/old.py (deleted, -89)
```

Si beaucoup de fichiers (>20), grouper par dossier et indiquer le nombre.

### 4. Rédiger le CR markdown

Utiliser EXACTEMENT ce template (sections obligatoires, dans cet ordre) :

```markdown
# Factory Report — <task_id>

**Date** : <ISO-8601 avec timezone>
**Project** : <project>
**Phase** : <phase>
**Brief** : <brief_path ou "—" si aucun>
**Status** : <success | partial | failed | blocked>
**Duration** : <X>s (ou "—" si inconnu)

## Ce qui a été fait

<3 à 8 puces, faits concrets, à la voix active. Pas de "j'ai essayé", "il semble que". Si une étape a échoué, le dire dans Blocages, pas ici.>

## Fichiers modifiés / créés

<liste formatée comme étape 3, ou "Aucun" si rien>

## Décisions techniques prises

<2 à 5 puces, chaque décision suivie d'une justification courte (1 phrase). Si aucune décision notable, "Aucune décision structurante" suffit.>

## Commandes exécutées

```bash
<commandes significatives, dans l'ordre. Masquer les tokens/secrets avec "***".>
```

## Blocages / questions ouvertes

<- Blocage 1 + ce qui a été tenté
- Question 1 pour Cowork/utilisateur
ou "Aucun" si tout est passé clean>

## Prochaine étape suggérée

<1 phrase actionnable, formulée pour Cowork. Exemples :
"Cowork peut maintenant lancer la phase speckit-setup."
"Attendre validation utilisateur avant d'enchaîner sur l'implémentation."
"Reprendre cette tâche après résolution du blocage GCP.">

## État mis à jour dans factory-state.json

```json
<diff JSON des champs modifiés — voir étape 5>
```
```

**Règles de rédaction critiques** :

- Pas d'emoji, pas de markdown décoratif inutile (headers de niveau 3+, gras à outrance).
- Tout en français, sauf les noms techniques (chemins, commandes, identifiants).
- Concision : un CR factory ne doit jamais dépasser 80 lignes. Si plus long, c'est que la tâche aurait dû être découpée.
- Honnêteté : si un test a échoué, le dire. Cowork préfère un CR "status: partial" exact à un "success" optimiste.

### 5. Patcher factory-state.json

Lire le fichier `state/factory-state.json` à la racine du repo POC_FACTORY. S'il n'existe pas (cas du tout premier bootstrap), le créer avec :

```json
{
  "factory_version": "0.1",
  "last_updated": null,
  "projects": {},
  "recent_reports": []
}
```

Ensuite, appliquer les modifications suivantes :

#### 5.a — Mettre à jour `last_updated`

Toujours, vers le `end_time` du CR.

#### 5.b — Mettre à jour la clé du projet concerné

Si `project` n'existe pas encore dans `projects`, l'ajouter :

```json
"<project>": {
  "name": "<nom court extrait de project>",
  "created_at": "<end_time>",
  "phases": {
    "new-project": {"status": "pending"},
    "speckit-setup": {"status": "pending"},
    "specify": {"status": "pending"},
    "plan": {"status": "pending"},
    "tasks": {"status": "pending"},
    "implement": {"status": "pending"},
    "commit": {"status": "pending"},
    "deploy": {"status": "pending"}
  },
  "github_repo": null,
  "cloud_run_url": null
}
```

Puis mettre à jour la phase concernée selon le `status` :

- `success` → `"status": "done"`, ajouter `"completed_at": "<end_time>"`, ajouter `"report": "reports/<task_id>.md"`
- `partial` → `"status": "in-progress"`, ajouter `"started_at": "<start_time ou end_time>"`, ajouter `"last_report": "reports/<task_id>.md"`
- `failed` → `"status": "failed"`, ajouter `"failed_at": "<end_time>"`, ajouter `"report": "reports/<task_id>.md"`
- `blocked` → `"status": "blocked"`, ajouter `"blocked_at": "<end_time>"`, ajouter `"report": "reports/<task_id>.md"`

#### 5.c — Mettre à jour les champs spécifiques selon la phase

Selon la phase qui vient de s'achever, enrichir le projet avec les champs détectés :

| Phase | Champ à patcher | Source |
|---|---|---|
| `new-project` | `github_repo` | URL du repo créé par `gh repo create` |
| `deploy` | `cloud_run_url` | URL retournée par `gcloud run deploy` |
| `commit` | `last_commit_sha` | `git rev-parse HEAD` |
| `commit` | `last_pr_url` | URL retournée par `gh pr create` (si PR ouverte) |

Si l'info n'est pas disponible (ex: le commit n'a pas créé de PR), laisser le champ inchangé.

#### 5.d — Ajouter le CR aux `recent_reports`

Ajouter `reports/<task_id>.md` en TÊTE de la liste `recent_reports`, et tronquer la liste à 20 entrées max.

#### 5.e — Écriture atomique

Écrire le JSON dans un fichier temporaire puis renommer, pour éviter une corruption si l'écriture est interrompue :

```bash
python3 - <<'PYEOF'
import json, os, tempfile

STATE = "state/factory-state.json"
with open(STATE, "r") as f:
    state = json.load(f)

# ... appliquer les modifications ...

tmp = tempfile.NamedTemporaryFile("w", dir="state", delete=False)
json.dump(state, tmp, indent=2, ensure_ascii=False)
tmp.close()
os.replace(tmp.name, STATE)
PYEOF
```

JSON formaté avec `indent=2` et `ensure_ascii=False` (pour les accents).

Inclure dans le CR markdown (section "État mis à jour") le **diff JSON** des champs modifiés uniquement, pas le state entier. Format :

```json
{
  "projects": {
    "demo/avis-summarizer": {
      "phases": {
        "new-project": {"status": "done", "completed_at": "2026-05-13T14:32:00+02:00", "report": "reports/2026-05-13T14-32-00_new-project_avis-summarizer.md"}
      },
      "github_repo": "https://github.com/cgi-factory-lab/avis-summarizer"
    }
  }
}
```

### 6. Écrire le CR markdown sur disque

Chemin de sortie strict :

```
reports/<task_id>.md
```

Si le dossier `reports/` n'existe pas, le créer.

### 7. Confirmer la complétion

À la fin de l'exécution, la skill DOIT afficher en sortie standard exactement ces 2 lignes (et rien d'autre que ce qui les concerne) pour que Cowork puisse les parser :

```
FACTORY_REPORT_WRITTEN=reports/<task_id>.md
FACTORY_STATE_UPDATED=state/factory-state.json
```

Cowork repère ces marqueurs et lit le CR pour restituer à Quentin.

## Schéma complet de factory-state.json

Pour référence, voici le schéma complet attendu après plusieurs exécutions :

```json
{
  "factory_version": "0.1",
  "last_updated": "2026-05-13T14:32:00+02:00",
  "projects": {
    "POC_FACTORY": {
      "name": "POC_FACTORY",
      "created_at": "2026-05-13T10:00:00+02:00",
      "phases": {
        "new-project": {"status": "done", "completed_at": "2026-05-13T10:15:00+02:00", "report": "reports/2026-05-13T10-15-00_new-project_bootstrap-poc-factory.md"},
        "speckit-setup": {"status": "pending"},
        "specify": {"status": "pending"},
        "plan": {"status": "pending"},
        "tasks": {"status": "pending"},
        "implement": {"status": "pending"},
        "commit": {"status": "pending"},
        "deploy": {"status": "pending"}
      },
      "github_repo": "https://github.com/cgi-factory-lab/POC_FACTORY",
      "cloud_run_url": null
    },
    "demo/avis-summarizer": {
      "name": "avis-summarizer",
      "created_at": "2026-05-13T14:00:00+02:00",
      "phases": {
        "new-project": {"status": "done", "completed_at": "2026-05-13T14:32:00+02:00", "report": "reports/2026-05-13T14-32-00_new-project_avis-summarizer.md"},
        "speckit-setup": {"status": "in-progress", "started_at": "2026-05-13T14:35:00+02:00"},
        "specify": {"status": "pending"},
        "plan": {"status": "pending"},
        "tasks": {"status": "pending"},
        "implement": {"status": "pending"},
        "commit": {"status": "pending"},
        "deploy": {"status": "pending"}
      },
      "github_repo": "https://github.com/cgi-factory-lab/avis-summarizer",
      "cloud_run_url": null
    }
  },
  "recent_reports": [
    "reports/2026-05-13T14-32-00_new-project_avis-summarizer.md",
    "reports/2026-05-13T10-15-00_new-project_bootstrap-poc-factory.md"
  ]
}
```

## Edge cases

- **factory-state.json corrompu** : si la lecture échoue (JSON invalide), créer un backup `state/factory-state.json.broken.<timestamp>` et démarrer un nouveau state vide. Mentionner cet incident dans la section Blocages du CR.
- **Phase inconnue** : si `phase` ne fait pas partie de la liste autorisée, utiliser `other` et préciser la phase réelle dans la section "Ce qui a été fait".
- **Projet bootstrap (POC_FACTORY)** : pour le tout premier CR (bootstrap de la factory elle-même), le `project` est `POC_FACTORY` et la phase est généralement `new-project`. Le CR sera dans `reports/` à la racine du repo qui vient d'être créé.
- **Tâche sans modifications de fichiers** : si une exécution n'a modifié aucun fichier (ex: vérification, lecture seule), mettre "Aucun" dans la section Fichiers modifiés et expliquer dans "Ce qui a été fait".
- **Secrets dans les commandes** : toujours masquer les tokens (`GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, etc.) dans la section Commandes exécutées. Remplacer par `***`.

## Exemple complet

### Input (brief Cowork)

```
Brief : briefs/2026-05-13T14-30-00_new-project_avis-summarizer.md

Tâche : Créer un nouveau projet "avis-summarizer" dans demo/.
- Initialiser SpecKit dans demo/avis-summarizer
- Créer le repo GitHub cgi-factory-lab/avis-summarizer
- Configurer le CI/CD avec Claude Code GitHub Action
Termine par un factory report.
```

### Output (CR généré dans reports/2026-05-13T14-32-00_new-project_avis-summarizer.md)

```markdown
# Factory Report — 2026-05-13T14-32-00_new-project_avis-summarizer

**Date** : 2026-05-13T14:32:00+02:00
**Project** : demo/avis-summarizer
**Phase** : new-project
**Brief** : briefs/2026-05-13T14-30-00_new-project_avis-summarizer.md
**Status** : success
**Duration** : 142s

## Ce qui a été fait

- Création du dossier demo/avis-summarizer/ avec arborescence standard FastAPI + Vite.
- Initialisation SpecKit via `specify init` (constitution vierge, branche main).
- Création du repo GitHub cgi-factory-lab/avis-summarizer (privé) via `gh repo create`.
- Push initial du squelette projet sur main.
- Configuration du workflow `.github/workflows/claude-review.yml` avec mention @claude sur PR.
- Activation des APIs GCP run.googleapis.com et cloudbuild.googleapis.com.

## Fichiers modifiés / créés

- demo/avis-summarizer/backend/main.py (created, 18 lines)
- demo/avis-summarizer/frontend/package.json (created, 24 lines)
- demo/avis-summarizer/Dockerfile (created, 32 lines)
- demo/avis-summarizer/.github/workflows/claude-review.yml (created, 41 lines)
- demo/avis-summarizer/specify/constitution.md (created, 12 lines)
- demo/avis-summarizer/README.md (created, 28 lines)

## Décisions techniques prises

- Stack figée à FastAPI + Vite/React/TS/Tailwind comme convenu pour le POC.
- Repo privé par défaut, à passer en public au moment de la démo.
- Cloud Run en europe-west9 (Paris) pour latence minimale en démo.

## Commandes exécutées

```bash
mkdir -p demo/avis-summarizer
cd demo/avis-summarizer && specify init .
gh repo create cgi-factory-lab/avis-summarizer --private --source=.
git push -u origin main
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project=*** 
```

## Blocages / questions ouvertes

Aucun.

## Prochaine étape suggérée

Cowork peut maintenant fournir l'expression de besoin à Claude Code pour lancer la phase de cadrage (skill factory-speckit-setup).

## État mis à jour dans factory-state.json

```json
{
  "projects": {
    "demo/avis-summarizer": {
      "phases": {
        "new-project": {"status": "done", "completed_at": "2026-05-13T14:32:00+02:00", "report": "reports/2026-05-13T14-32-00_new-project_avis-summarizer.md"}
      },
      "github_repo": "https://github.com/cgi-factory-lab/avis-summarizer"
    }
  }
}
```
```

## Anti-patterns à éviter

- Réécrire le state entier alors qu'on modifie un seul projet (risque d'écraser des updates concurrents).
- Mettre `status: success` alors qu'un test a échoué — préférer `partial` et expliquer.
- Inclure des secrets en clair dans la section commandes — masquer systématiquement.
- Faire un CR sans patcher le state, ou patcher le state sans CR — les deux sont toujours faits ensemble.
- Dépasser 80 lignes : si le CR est trop long, c'est un signal que la tâche était trop grosse pour une seule exécution factory.

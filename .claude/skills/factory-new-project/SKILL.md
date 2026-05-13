---
name: factory-new-project
description: Bootstrap un nouveau projet logiciel dans le dossier demo/ du repo CGI Factory (quentinr34/POC_FACTORY) avec stack FastAPI + Vite/React/TS/Tailwind, prêt à être déployé sur Cloud Run dans le projet GCP bt-ia-lab-sandbox. Déclenche cette skill dès que Cowork demande "crée un nouveau projet factory", "bootstrap un projet", "démarre un projet <nom>", "monte un nouveau projet dans la factory", ou tout brief contenant phase=new-project. Ne JAMAIS utiliser cette skill pour des projets hors du contexte CGI Factory. La skill commit+push dans le repo POC_FACTORY existant (pas de nouveau repo) et termine TOUJOURS par une invocation de factory-report. NOUVEAU v3 : la skill écrit des marqueurs de progression [FACTORY_PROGRESS] dans stdout ET dans logs/<task_id>.log à chaque étape — c'est ce qui permet à Cowork de suivre l'avancement sans timeout.
---

# Factory New Project — v3

Cette skill orchestre le bootstrap end-to-end d'un nouveau projet dans `demo/` du repo CGI Factory existant. Elle commit + push dans `quentinr34/POC_FACTORY`, active les APIs GCP sur le projet sandbox, et invoque `factory-report`.

**Nouveautés v3** :
- **Marqueurs de progression** `[FACTORY_PROGRESS]` écrits en stdout ET dans `logs/<task_id>.log` à chaque étape (start + done + durée)
- **Encodage UTF-8 forcé** sur tous les fichiers écrits (sinon les accents cassent sur Windows)
- **Détection adaptive Tailwind v3 vs v4** (la skill v2 a découvert empiriquement le problème)
- **Timeout npm install** à 10 minutes max pour éviter les hangs réseau

## Chemin canonique et constantes figées

Racine factory : `C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY\`

Constantes :

- **GITHUB_REPO** = `quentinr34/POC_FACTORY` (existe déjà)
- **GCP_PROJECT** = `bt-ia-lab-sandbox`
- **GCP_PROJECT_ABBREV** = `snd`
- **GCP_ENV** = `dev`
- **GCP_REGION** = `europe-west9`
- **DEFAULT_BRANCH** = `main`
- **Labels GCP obligatoires** : `owner=quentin`, `project=snd`, `env=dev`, `client=internal`
- **Convention Cloud Run service** : `snd-dev-svc-<project_name>`

## Lecture obligatoire avant toute action GCP

Lire `GCP_documentation.md` à la racine POC_FACTORY avant toute commande `gcloud`. Source de vérité pour la gouvernance GCP du Lab.

## Préconditions à vérifier (étape 1)

1. cwd = `C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY` (sinon `cd`).
2. `git remote get-url origin` = `https://github.com/quentinr34/POC_FACTORY.git` ou équivalent SSH.
3. CLI auth : `gh auth status` (quentinr34), `git --version`, `gcloud auth list`, `gcloud config get-value project` = `bt-ia-lab-sandbox` (sinon `gcloud config set project bt-ia-lab-sandbox`), `node --version` ≥ 20, `npm --version`, `python --version` ≥ 3.10.
4. `GCP_documentation.md` présent à la racine. Sinon : abort `failed`.
5. `demo/<project_name>/` n'existe pas déjà.
6. Repo à jour avec origin (`git fetch ; git status` ne montre pas "behind"). Sinon `git pull`.

Si précondition échoue : abort, CR `failed`.

## Inputs attendus

- **project_name** (obligatoire) : kebab-case, pattern `^[a-z][a-z0-9-]{2,49}$`.
- **description** (optionnel) : 1 phrase max 100 chars. Défaut : `"Projet généré par la CGI Factory"`.

## Système de marqueurs de progression (NOUVEAU v3)

### Format des marqueurs

À chaque étape, écrire en stdout ET appender dans `logs/<task_id>.log` :

```
[FACTORY_PROGRESS] step=<N>/10 phase=<phase-name> status=<started|done|failed> ts=<ISO-8601> [duration=<X>s]
```

Exemples :

```
[FACTORY_PROGRESS] step=1/10 phase=preconditions status=started ts=2026-05-13T15:00:00+02:00
[FACTORY_PROGRESS] step=1/10 phase=preconditions status=done ts=2026-05-13T15:00:02+02:00 duration=2s
```

### Fonction PowerShell helper à utiliser

Définir au début de l'exécution :

```powershell
$TASK_ID = "$((Get-Date -Format 'yyyy-MM-ddTHH-mm-ss'))_new-project_bootstrap-$PROJECT_NAME"
$LOG_PATH = "logs\$TASK_ID.log"
New-Item -ItemType Directory -Path "logs" -Force | Out-Null

function Write-FactoryProgress {
    param(
        [int]$Step,
        [int]$Total = 10,
        [string]$Phase,
        [string]$Status,
        [int]$DurationSeconds = -1
    )
    $ts = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz").Replace("zzz", "+02:00")
    $line = "[FACTORY_PROGRESS] step=$Step/$Total phase=$Phase status=$Status ts=$ts"
    if ($DurationSeconds -ge 0) { $line += " duration=${DurationSeconds}s" }
    Write-Host $line
    Add-Content -Path $LOG_PATH -Value $line -Encoding UTF8
}
```

### Liste figée des 10 étapes avec leurs phase-name

| # | phase-name | Description |
|---|---|---|
| 1 | preconditions | Vérification env, CLI, repo |
| 2 | scaffold-dir | Création `demo/<project>/` |
| 3 | vite-scaffold | `npm create vite` + Tailwind |
| 4 | backend-fastapi | `main.py` + `requirements.txt` |
| 5 | dockerfile | Dockerfile multi-stage |
| 6 | config-files | `.dockerignore`, `README.md` |
| 7 | gcp-apis | `gcloud services enable` |
| 8 | cd-root | Retour racine factory |
| 9 | git-commit-push | `git add`, commit, push |
| 10 | invoke-report | Appel `factory-report` |

Chaque étape doit avoir un `started` et un `done` (ou `failed`).

## Étapes d'exécution (avec marqueurs)

### Étape 1 — Préconditions

```powershell
Write-FactoryProgress -Step 1 -Phase "preconditions" -Status "started"
$step1Start = Get-Date

# ... toutes les vérifs préconditions ci-dessus ...

$step1Duration = [int]((Get-Date) - $step1Start).TotalSeconds
Write-FactoryProgress -Step 1 -Phase "preconditions" -Status "done" -DurationSeconds $step1Duration
```

Pattern à appliquer pour chaque étape suivante.

### Étape 2 — Création du dossier local

```powershell
Write-FactoryProgress -Step 2 -Phase "scaffold-dir" -Status "started"
$start = Get-Date

cd C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY
New-Item -ItemType Directory -Path "demo\$PROJECT_NAME" -Force | Out-Null
cd "demo\$PROJECT_NAME"

Write-FactoryProgress -Step 2 -Phase "scaffold-dir" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)
```

### Étape 3 — Scaffold Vite + Tailwind (adaptive v3/v4)

```powershell
Write-FactoryProgress -Step 3 -Phase "vite-scaffold" -Status "started"
$start = Get-Date

# Scaffold Vite
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
cd ..

# Détection Tailwind v3 vs v4 (la v4 a changé l'API)
# Pour le POC, on impose v3 qui est plus stable et compatible avec notre config
cd frontend
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
cd ..

Write-FactoryProgress -Step 3 -Phase "vite-scaffold" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)
```

Si `npm install` dépasse 600 secondes (10 min), considérer comme `failed` et abort proprement.

Puis écraser 4 fichiers Vite avec les contenus customisés CGI (voir détail en fin de skill).

### Étape 4 — Backend FastAPI

```powershell
Write-FactoryProgress -Step 4 -Phase "backend-fastapi" -Status "started"
$start = Get-Date

New-Item -ItemType Directory -Path "backend" -Force | Out-Null
# Écrire backend/main.py et backend/requirements.txt avec UTF-8 forcé
# (voir contenus en fin de skill)

Write-FactoryProgress -Step 4 -Phase "backend-fastapi" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)
```

### Étapes 5 à 7 — Dockerfile, config, GCP

Même pattern. Pour l'étape 7 (GCP), même si échec, marquer `done` avec note dans le CR (best-effort).

### Étape 8 — Retour racine

```powershell
Write-FactoryProgress -Step 8 -Phase "cd-root" -Status "started"
cd C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY
Write-FactoryProgress -Step 8 -Phase "cd-root" -Status "done" -DurationSeconds 0
```

### Étape 9 — Git commit et push

```powershell
Write-FactoryProgress -Step 9 -Phase "git-commit-push" -Status "started"
$start = Get-Date

git add demo/$PROJECT_NAME
git commit -m "factory(new-project): bootstrap demo/$PROJECT_NAME"
git push origin main

Write-FactoryProgress -Step 9 -Phase "git-commit-push" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)
```

Si push échoue : `failed` au lieu de `done`, CR sera `partial`.

### Étape 10 — Invocation factory-report

```powershell
Write-FactoryProgress -Step 10 -Phase "invoke-report" -Status "started"
$start = Get-Date

# Invoquer la skill factory-report avec inputs (notamment task_id = $TASK_ID
# pour qu'elle lise le bon log de progression)
# Inputs : phase=new-project, project=demo/$PROJECT_NAME, task_slug=bootstrap-$PROJECT_NAME,
# brief_path=<chemin brief ou null>, status=<success/partial/failed>, task_id=$TASK_ID

Write-FactoryProgress -Step 10 -Phase "invoke-report" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)
```

## Contenus des fichiers à écrire (UTF-8 forcé)

CRITIQUE : pour TOUS les fichiers texte écrits par cette skill, utiliser UTF-8 sans BOM. Sous PowerShell 5 :

```powershell
[System.IO.File]::WriteAllText("chemin\fichier.ext", $contenu, [System.Text.UTF8Encoding]::new($false))
```

Le `$false` exclut le BOM. `Out-File -Encoding utf8` par défaut écrit AVEC BOM en PS5, ne pas l'utiliser tel quel.

### `frontend/tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: { cgi: "#5336AB" }
    }
  },
  plugins: []
}
```

### `frontend/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### `frontend/src/App.tsx`

```tsx
import { useEffect, useState } from "react"
import "./index.css"

export default function App() {
  const [health, setHealth] = useState<string>("checking...")

  useEffect(() => {
    fetch("/api/health")
      .then(r => r.json())
      .then(d => setHealth(d.status))
      .catch(() => setHealth("backend unreachable"))
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md text-center">
        <h1 className="text-3xl font-bold text-cgi mb-4">PROJECT_NAME_PLACEHOLDER</h1>
        <p className="text-gray-700">Backend status: <span className="font-mono">{health}</span></p>
        <p className="text-sm text-gray-400 mt-4">Generated by CGI Factory</p>
      </div>
    </div>
  )
}
```

### `frontend/vite.config.ts`

```ts
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../backend/static",
    emptyOutDir: true
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000"
    }
  }
})
```

### `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="PROJECT_NAME_PLACEHOLDER")

@app.get("/api/health")
def health():
    return {"status": "ok"}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
```

### `backend/requirements.txt`

```
fastapi==0.118.0
uvicorn[standard]==0.32.0
```

### `Dockerfile`

```dockerfile
# --- Stage 1 : build frontend ---
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2 : runtime backend ---
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /app/backend/static ./static
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
```

### `.dockerignore`

```
node_modules
__pycache__
.venv
venv
.git
.gitignore
README.md
backend/static
```

### `README.md`

```markdown
# PROJECT_NAME_PLACEHOLDER

DESCRIPTION_PLACEHOLDER

Generated by CGI Factory on DATE_PLACEHOLDER.

## Stack
- Backend : FastAPI (Python 3.12)
- Frontend : Vite + React + TypeScript + Tailwind CSS v3
- Container : Docker multi-stage
- Deployment : Google Cloud Run, projet bt-ia-lab-sandbox, région europe-west9

## Local development
Backend : cd backend ; pip install -r requirements.txt ; uvicorn main:app --reload --port 8000
Frontend : cd frontend ; npm install ; npm run dev

Frontend sur http://localhost:5173 (proxy /api/* vers backend:8000).

## Production build
docker build -t PROJECT_NAME_PLACEHOLDER .
docker run -p 8080:8080 PROJECT_NAME_PLACEHOLDER

## Déploiement Cloud Run
Service : snd-dev-svc-PROJECT_NAME_PLACEHOLDER

gcloud run deploy snd-dev-svc-PROJECT_NAME_PLACEHOLDER --source . --region europe-west9 --project bt-ia-lab-sandbox --labels owner=quentin,project=snd,env=dev,client=internal --allow-unauthenticated

Voir ../../GCP_documentation.md pour les règles complètes.

## CI/CD
PRs sur ce repo déclenchent automatiquement Claude Code Review via .github/workflows/claude-review.yml racine. Mention @claude dans un commentaire de PR pour invoquer.
```

Tous ces fichiers contiennent des placeholders à substituer : `PROJECT_NAME_PLACEHOLDER`, `DESCRIPTION_PLACEHOLDER`, `DATE_PLACEHOLDER`.

## Gestion des erreurs (option B sans rollback)

| Étape échouée | Action | Status final |
|---|---|---|
| 1 préconditions | Abort, rien créé | `failed` |
| 2 scaffold-dir | Dossier partiel manuel | `failed` |
| 3 vite-scaffold | Dossier partiel, signaler | `failed` |
| 4 backend-fastapi | Local, signaler | `partial` |
| 5 dockerfile | Local, signaler | `partial` |
| 6 config-files | Local, signaler | `partial` |
| 7 gcp-apis | Scaffold OK, APIs manuelles | `partial` (note) |
| 8 cd-root | Improbable | `partial` |
| 9 git-commit-push | Local, signaler commande | `partial` |
| 10 invoke-report | CR à faire manuel | `partial` |

Toujours invoquer `factory-report` à l'étape 10 même en cas d'échec d'une étape précédente — le status reflète l'état réel.

## Exemple complet de sortie attendue

Stdout pendant l'exécution :

```
[FACTORY_PROGRESS] step=1/10 phase=preconditions status=started ts=2026-05-13T15:00:00+02:00
[FACTORY_PROGRESS] step=1/10 phase=preconditions status=done ts=2026-05-13T15:00:02+02:00 duration=2s
[FACTORY_PROGRESS] step=2/10 phase=scaffold-dir status=started ts=2026-05-13T15:00:02+02:00
[FACTORY_PROGRESS] step=2/10 phase=scaffold-dir status=done ts=2026-05-13T15:00:03+02:00 duration=1s
[FACTORY_PROGRESS] step=3/10 phase=vite-scaffold status=started ts=2026-05-13T15:00:03+02:00
[FACTORY_PROGRESS] step=3/10 phase=vite-scaffold status=done ts=2026-05-13T15:05:45+02:00 duration=342s
... etc ...
[FACTORY_PROGRESS] step=10/10 phase=invoke-report status=done ts=2026-05-13T15:06:25+02:00 duration=4s
FACTORY_REPORT_WRITTEN=reports/2026-05-13T15-06-25_new-project_bootstrap-hello-factory-v2.md
FACTORY_STATE_UPDATED=state/factory-state.json
```

Le log `logs/<task_id>.log` contient les mêmes marqueurs en UTF-8.

## Anti-patterns

- Créer un repo GitHub séparé : le projet vit dans `demo/` du repo POC_FACTORY existant.
- Créer un workflow GitHub Action par projet : workflow racine s'applique à tout.
- Ignorer les conventions GCP : service Cloud Run DOIT être `snd-dev-svc-<project>`, labels obligatoires.
- Déployer sur autre projet GCP que `bt-ia-lab-sandbox`.
- Forcer activation APIs GCP : best-effort, pas bloquant.
- Dockerfile mono-stage : taille image inutilement grosse.
- Oublier invocation `factory-report` finale.
- Commit `node_modules/` ou `backend/static/` (gitignored au niveau racine POC_FACTORY).
- URL Cloud Run hardcodée dans frontend — utiliser `/api/*` relatifs.
- **NOUVEAU v3 : sauter les marqueurs `[FACTORY_PROGRESS]`** — Cowork en dépend pour suivre l'avancement et ne pas timeout.
- **NOUVEAU v3 : écrire des fichiers sans forcer UTF-8 sans BOM** — les accents cassent et le code source devient illisible.

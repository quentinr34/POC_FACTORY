---
name: factory-new-project
description: Bootstrap un nouveau projet logiciel dans le dossier demo/ du repo CGI Factory (quentinr34/POC_FACTORY) avec stack FastAPI + Vite/React/TS/Tailwind, prêt à être déployé sur Cloud Run dans le projet GCP bt-ia-lab-sandbox. Déclenche cette skill dès que Cowork demande "crée un nouveau projet factory", "bootstrap un projet", "démarre un projet <nom>", "monte un nouveau projet dans la factory", ou tout brief contenant phase=new-project. Ne JAMAIS utiliser cette skill pour des projets hors du contexte CGI Factory. La skill commit+push dans le repo POC_FACTORY existant (pas de nouveau repo) et termine TOUJOURS par une invocation de factory-report. Les marqueurs de progression [FACTORY_PROGRESS] sont émis EN STDOUT (pour Claude Code) ET dans logs/<task_id>.progress.log via FileStream avec AutoFlush+FileShare.Read (lecture concurrente Cowork sans lock).
---

# Factory New Project — v3.2

Cette skill orchestre le bootstrap end-to-end d'un nouveau projet dans `demo/` du repo CGI Factory existant. Elle commit + push dans `quentinr34/POC_FACTORY`, active les APIs GCP sur le projet sandbox, et invoque `factory-report`.

**Nouveautés v3.2** (correction du buffering stdout détecté en v3.1) :
- **Double-write rétabli mais SAFE** : les marqueurs `[FACTORY_PROGRESS]` sont écrits en stdout (pour Claude Code) ET dans un fichier dédié `logs/<task_id>.progress.log` ouvert via FileStream .NET avec `AutoFlush=true` et `FileShare.Read`. Cowork peut lire ce fichier en parallèle SANS lock (chacun a son propre fichier, plus de conflit avec `claude-stdout.log`).
- Le reste de v3.1 (UTF-8 forcé, Tailwind v3 figé, timeout npm) est conservé.

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

Lire `GCP_documentation.md` à la racine POC_FACTORY avant toute commande `gcloud`.

## Préconditions à vérifier (étape 1)

1. cwd = `C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY` (sinon `cd`).
2. `git remote get-url origin` = `https://github.com/quentinr34/POC_FACTORY.git`.
3. CLI auth : `gh auth status`, `git --version`, `gcloud auth list`, `gcloud config get-value project` = `bt-ia-lab-sandbox`, `node --version` ≥ 20, `npm --version`, `python --version` ≥ 3.10.
4. `GCP_documentation.md` présent. Sinon : abort `failed`.
5. `demo/<project_name>/` n'existe pas déjà.
6. Repo à jour avec origin. Sinon `git pull`.

Si précondition échoue : abort, CR `failed`.

## Inputs attendus

- **project_name** (obligatoire) : kebab-case, pattern `^[a-z][a-z0-9-]{2,49}$`.
- **description** (optionnel) : 1 phrase max 100 chars.

## Système de marqueurs de progression (CORRIGÉ v3.2 — double-write safe)

### Format des marqueurs

À chaque étape, écrire en stdout ET dans le progress log :

```
[FACTORY_PROGRESS] step=<N>/10 phase=<phase-name> status=<started|done|failed> ts=<ISO-8601> [duration=<X>s]
```

### Génération du task_id et ouverture du progress log

Au tout début de l'exécution :

```powershell
# 1. Generer le task_id
$TASK_ID = "$((Get-Date -Format 'yyyy-MM-ddTHH-mm-ss'))_new-project_bootstrap-$PROJECT_NAME"

# 2. Preparer le chemin progress log
$PROGRESS_LOG = "logs\$TASK_ID.progress.log"
New-Item -ItemType Directory -Path "logs" -Force | Out-Null

# 3. OUVRIR un FileStream .NET sur le progress log
#    Mode: Append, Acces: Write, Partage: Read (Cowork peut lire en parallele)
$script:progressFs = [System.IO.File]::Open(
    $PROGRESS_LOG,
    [System.IO.FileMode]::Append,
    [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::Read
)
$script:progressWriter = New-Object System.IO.StreamWriter(
    $script:progressFs,
    [System.Text.UTF8Encoding]::new($false)
)
# CRITIQUE : AutoFlush=true force l'ecriture immediate, pas de buffer
$script:progressWriter.AutoFlush = $true
```

### Fonction PowerShell helper

```powershell
function Write-FactoryProgress {
    param(
        [int]$Step,
        [int]$Total = 10,
        [string]$Phase,
        [string]$Status,
        [int]$DurationSeconds = -1
    )
    $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
    $line = "[FACTORY_PROGRESS] step=$Step/$Total phase=$Phase status=$Status ts=$ts"
    if ($DurationSeconds -ge 0) { $line += " duration=${DurationSeconds}s" }

    # 1. Stdout (visible par Claude Code, capte par Cowork via stdout redirect)
    Write-Host $line

    # 2. Progress log dedie (lu par Cowork en parallele via Read-LogNonBlocking)
    if ($script:progressWriter) {
        $script:progressWriter.WriteLine($line)
        # Pas besoin de Flush() explicite car AutoFlush=true
    }
}
```

### Fermeture du progress log (CRITIQUE en fin d'exécution)

À la toute fin de la skill, avant le `return` final, fermer proprement le stream :

```powershell
if ($script:progressWriter) {
    $script:progressWriter.Close()
    $script:progressWriter = $null
}
if ($script:progressFs) {
    $script:progressFs.Close()
    $script:progressFs = $null
}
```

Si la skill plante avant cette ligne (erreur fatale), le fichier reste ouvert jusqu'à la fin du process Claude Code, mais le contenu est déjà flushé (AutoFlush=true), donc pas de perte de données.

### Liste figée des 10 étapes

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

Chaque étape : `started` + `done` (ou `failed`).

## Étapes d'exécution

### Étape 1 — Préconditions

```powershell
Write-FactoryProgress -Step 1 -Phase "preconditions" -Status "started"
$step1Start = Get-Date
# ... verifications preconditions ...
Write-FactoryProgress -Step 1 -Phase "preconditions" -Status "done" -DurationSeconds ([int]((Get-Date)-$step1Start).TotalSeconds)
```

Pattern identique pour les étapes 2 à 10.

### Étape 2 — Création du dossier local

```powershell
Write-FactoryProgress -Step 2 -Phase "scaffold-dir" -Status "started"
$start = Get-Date

cd C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY
New-Item -ItemType Directory -Path "demo\$PROJECT_NAME" -Force | Out-Null
cd "demo\$PROJECT_NAME"

Write-FactoryProgress -Step 2 -Phase "scaffold-dir" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)
```

### Étape 3 — Scaffold Vite + Tailwind v3

```powershell
Write-FactoryProgress -Step 3 -Phase "vite-scaffold" -Status "started"
$start = Get-Date

npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
cd ..

cd frontend
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
cd ..

Write-FactoryProgress -Step 3 -Phase "vite-scaffold" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)
```

Puis écrire les 4 fichiers customisés (tailwind.config.js, src/index.css, src/App.tsx, vite.config.ts) en UTF-8 forcé.

### Étape 4 — Backend FastAPI

```powershell
Write-FactoryProgress -Step 4 -Phase "backend-fastapi" -Status "started"
$start = Get-Date

New-Item -ItemType Directory -Path "backend" -Force | Out-Null
# Ecrire backend/main.py et backend/requirements.txt avec UTF-8 force

Write-FactoryProgress -Step 4 -Phase "backend-fastapi" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)
```

### Étapes 5 à 8 — Dockerfile, config, GCP, retour racine

Même pattern.

### Étape 9 — Git commit et push

```powershell
Write-FactoryProgress -Step 9 -Phase "git-commit-push" -Status "started"
$start = Get-Date

git add demo/$PROJECT_NAME
git commit -m "factory(new-project): bootstrap demo/$PROJECT_NAME"
git push origin main

Write-FactoryProgress -Step 9 -Phase "git-commit-push" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)
```

### Étape 10 — Invocation factory-report

```powershell
Write-FactoryProgress -Step 10 -Phase "invoke-report" -Status "started"
$start = Get-Date

# Invoquer factory-report avec inputs :
# phase=new-project, project=demo/$PROJECT_NAME, task_slug=bootstrap-$PROJECT_NAME,
# brief_path=<chemin brief ou null>, status=<success/partial/failed>, task_id=$TASK_ID

Write-FactoryProgress -Step 10 -Phase "invoke-report" -Status "done" -DurationSeconds ([int]((Get-Date)-$start).TotalSeconds)

# FERMETURE DU PROGRESS LOG (CRITIQUE)
if ($script:progressWriter) { $script:progressWriter.Close(); $script:progressWriter = $null }
if ($script:progressFs)     { $script:progressFs.Close();     $script:progressFs = $null }
```

## Contenus des fichiers à écrire (UTF-8 forcé)

CRITIQUE : pour TOUS les fichiers texte écrits par cette skill, UTF-8 sans BOM :

```powershell
[System.IO.File]::WriteAllText("chemin\fichier.ext", $contenu, [System.Text.UTF8Encoding]::new($false))
```

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
Backend : `cd backend ; pip install -r requirements.txt ; uvicorn main:app --reload --port 8000`
Frontend : `cd frontend ; npm install ; npm run dev`

## Production build
`docker build -t PROJECT_NAME_PLACEHOLDER .`
`docker run -p 8080:8080 PROJECT_NAME_PLACEHOLDER`

## Déploiement Cloud Run
Service : `snd-dev-svc-PROJECT_NAME_PLACEHOLDER`

`gcloud run deploy snd-dev-svc-PROJECT_NAME_PLACEHOLDER --source . --region europe-west9 --project bt-ia-lab-sandbox --labels owner=quentin,project=snd,env=dev,client=internal --allow-unauthenticated`

Voir `../../GCP_documentation.md`.

## CI/CD
Workflow racine `.github/workflows/claude-review.yml` review automatiquement chaque PR.
```

Substituer `PROJECT_NAME_PLACEHOLDER`, `DESCRIPTION_PLACEHOLDER`, `DATE_PLACEHOLDER`.

## Gestion des erreurs (option B sans rollback)

| Étape échouée | Action | Status final |
|---|---|---|
| 1 préconditions | Abort, rien créé | `failed` |
| 2 scaffold-dir | Dossier partiel manuel | `failed` |
| 3 vite-scaffold | Dossier partiel | `failed` |
| 4 backend-fastapi | Local, signaler | `partial` |
| 5 dockerfile | Local, signaler | `partial` |
| 6 config-files | Local, signaler | `partial` |
| 7 gcp-apis | Scaffold OK, APIs manuelles | `partial` (note) |
| 8 cd-root | Improbable | `partial` |
| 9 git-commit-push | Local, signaler commande | `partial` |
| 10 invoke-report | CR à faire manuel | `partial` |

Toujours invoquer `factory-report` à l'étape 10 même en cas d'échec. **TOUJOURS fermer le progress log writer** avant de retourner, même en cas d'erreur (utiliser try/finally si possible).

## Anti-patterns

- Créer un repo GitHub séparé.
- Créer un workflow par projet.
- Ignorer conventions GCP : service `snd-dev-svc-*`, labels obligatoires.
- Déployer hors `bt-ia-lab-sandbox`.
- Forcer activation APIs GCP : best-effort.
- Dockerfile mono-stage.
- Oublier invocation `factory-report` finale.
- Commit `node_modules/` ou `backend/static/`.
- URL Cloud Run hardcodée — `/api/*` relatifs.
- Sauter les marqueurs `[FACTORY_PROGRESS]`.
- Écrire sans UTF-8 sans BOM.
- **v3.2 : ouvrir le progress log sans `FileShare.Read`** — Cowork ne pourra plus le lire en parallèle.
- **v3.2 : oublier `AutoFlush=$true`** — les marqueurs resteront buffés et Cowork verra le log vide jusqu'à la fin.
- **v3.2 : oublier de fermer le writer en fin d'exécution** — le fichier reste verrouillé jusqu'à la mort du process.
- **v3.2 : écrire les marqueurs dans `claude-stdout.log` directement** — c'est le fichier que Cowork pilote via `Start-Process`, double-write = IOException.

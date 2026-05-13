---
name: factory-new-project
description: Bootstrap un nouveau projet logiciel dans le dossier demo/ du repo CGI Factory (quentinr34/POC_FACTORY) avec stack FastAPI + Vite/React/TS/Tailwind, prêt à être déployé sur Cloud Run dans le projet GCP bt-ia-lab-sandbox. Déclenche cette skill dès que Cowork demande "crée un nouveau projet factory", "bootstrap un projet", "démarre un projet <nom>", "monte un nouveau projet dans la factory", ou tout brief contenant phase=new-project. Ne JAMAIS utiliser cette skill pour des projets hors du contexte CGI Factory ou pour scaffold un projet sans contexte CGI. La skill commit+push dans le repo POC_FACTORY existant (pas de nouveau repo créé) et termine TOUJOURS par une invocation de factory-report pour produire le CR et patcher factory-state.json.
---

# Factory New Project

Cette skill orchestre le bootstrap end-to-end d'un nouveau projet dans le dossier `demo/` du repo CGI Factory existant. Elle crée le dossier local, scaffold le squelette FastAPI + Vite, commit + push dans `quentinr34/POC_FACTORY`, active les APIs GCP sur le projet sandbox, et invoque `factory-report`.

Le repo POC_FACTORY existe déjà et contient à sa racine `GCP_documentation.md` (règles de gouvernance GCP du Lab BT IA FACTORY) et `.github/workflows/claude-review.yml` (Claude Code Review qui s'applique à toutes les PRs). La skill ne touche à aucun de ces deux fichiers.

## Chemin canonique et constantes figées

Racine factory sur ce poste :

```
C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY\
```

Constantes figées (modifier ici si changement) :

- **GITHUB_REPO** = `quentinr34/POC_FACTORY` (existe déjà)
- **GCP_PROJECT** = `bt-ia-lab-sandbox`
- **GCP_PROJECT_ABBREV** = `snd`
- **GCP_ENV** = `dev`
- **GCP_REGION** = `europe-west9` (Paris)
- **DEFAULT_BRANCH** = `main`
- **Labels GCP obligatoires** : `owner=quentin`, `project=snd`, `env=dev`, `client=internal`
- **Convention Cloud Run service** : `snd-dev-svc-<project_name>` (utilisée plus tard par la skill `factory-deploy-cloud-run`, pas par celle-ci)

## Lecture obligatoire avant toute action GCP

Avant toute commande `gcloud`, lire le fichier `GCP_documentation.md` à la racine POC_FACTORY. Il définit les règles de gouvernance (conventions de nommage, labels, budgets, sécurité). Toute commande GCP de cette skill DOIT respecter ces règles. Si une règle évolue, le fichier est la source de vérité — pas cette skill.

## Quand utiliser cette skill

- Cowork transmet un brief contenant `phase: new-project` et un `project_name`.
- L'utilisateur dit "crée un nouveau projet factory appelé X", "démarre un projet X dans la factory", "monte le projet X".
- NE PAS déclencher si le brief mentionne une phase autre que `new-project`, ni pour scaffold un projet hors `demo/`.

## Préconditions à vérifier en début d'exécution

Avant toute action destructive, vérifier :

1. Working directory = `C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY\`. Sinon : `cd` dans cette racine.
2. Le working directory est bien un repo git pointant vers `quentinr34/POC_FACTORY` :
   ```powershell
   git remote get-url origin
   # doit retourner https://github.com/quentinr34/POC_FACTORY.git ou git@github.com:quentinr34/POC_FACTORY.git
   ```
3. Les outils CLI sont installés et auth :
   - `gh auth status` → logged in as quentinr34
   - `git --version` → succès
   - `gcloud auth list` → un compte actif
   - `gcloud config get-value project` → si la valeur n'est pas `bt-ia-lab-sandbox`, exécuter `gcloud config set project bt-ia-lab-sandbox`
   - `node --version` ≥ 20 et `npm --version` → succès
   - `python --version` ≥ 3.10 → succès
4. Le fichier `GCP_documentation.md` existe à la racine POC_FACTORY. Sinon : abort avec CR `failed` (la skill ne peut pas faire de GCP sans les règles).
5. Le dossier `demo/<project_name>/` n'existe pas déjà localement.
6. Le repo POC_FACTORY local est à jour avec origin (`git fetch && git status` ne montre pas de "behind"). Si en retard : `git pull` d'abord.

Si une précondition échoue : ne PAS continuer. Produire un CR `failed` avec le détail dans Blocages.

## Inputs attendus

- **project_name** (obligatoire) : kebab-case, ex `avis-summarizer`. Pattern : `^[a-z][a-z0-9-]{2,49}$`.
- **description** (optionnel) : 1 phrase de description, max 100 caractères. Défaut : `"Projet généré par la CGI Factory"`.

## Étapes d'exécution

### 1. Validation des inputs

- Vérifier que `project_name` matche le pattern. Sinon : abort avec CR `failed`.
- Vérifier les préconditions ci-dessus.

### 2. Création du dossier local

```powershell
cd C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY
New-Item -ItemType Directory -Path "demo\<project_name>" -Force
cd "demo\<project_name>"
```

### 3. Scaffold du frontend via Vite

Utiliser le scaffold officiel Vite pour éviter d'écrire 15 fichiers de config à la main :

```powershell
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
cd ..
```

Puis remplacer 4 fichiers générés par Vite avec ces contenus :

**`frontend/tailwind.config.js`** :

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

**`frontend/src/index.css`** (écraser le contenu existant) :

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**`frontend/src/App.tsx`** (écraser le contenu existant) :

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

**`frontend/vite.config.ts`** (build vers `../backend/static`) :

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

Remplacer `PROJECT_NAME_PLACEHOLDER` par la valeur réelle de `project_name`.

### 4. Création du backend FastAPI

```powershell
New-Item -ItemType Directory -Path "backend" -Force
```

**`backend/main.py`** :

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="PROJECT_NAME_PLACEHOLDER")

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Sert le frontend buildé (dossier static/ peuplé par 'vite build')
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
```

**`backend/requirements.txt`** :

```
fastapi==0.118.0
uvicorn[standard]==0.32.0
```

Remplacer `PROJECT_NAME_PLACEHOLDER` par la valeur réelle.

### 5. Dockerfile multi-stage

À la racine du projet (`demo/<project_name>/Dockerfile`) :

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

### 6. Fichiers de configuration restants

**`.dockerignore`** :

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

**`README.md`** (à la racine du sous-projet) :

```markdown
# PROJECT_NAME_PLACEHOLDER

DESCRIPTION_PLACEHOLDER

Generated by CGI Factory on DATE_PLACEHOLDER.

## Stack

- Backend : FastAPI (Python 3.12)
- Frontend : Vite + React + TypeScript + Tailwind CSS
- Container : Docker multi-stage
- Deployment : Google Cloud Run, projet `bt-ia-lab-sandbox`, région `europe-west9`

## Local development

Backend :

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend (dans un autre terminal) :

```bash
cd frontend
npm install
npm run dev
```

Frontend disponible sur http://localhost:5173, proxy les /api/* vers le backend sur :8000.

## Production build (Docker)

```bash
docker build -t PROJECT_NAME_PLACEHOLDER .
docker run -p 8080:8080 PROJECT_NAME_PLACEHOLDER
```

## Déploiement Cloud Run

Nom du service Cloud Run (convention GCP du Lab) : `snd-dev-svc-PROJECT_NAME_PLACEHOLDER`

```bash
gcloud run deploy snd-dev-svc-PROJECT_NAME_PLACEHOLDER \
  --source . \
  --region europe-west9 \
  --project bt-ia-lab-sandbox \
  --labels owner=quentin,project=snd,env=dev,client=internal \
  --allow-unauthenticated
```

Voir `../../GCP_documentation.md` pour les règles complètes de gouvernance GCP du Lab.

## CI/CD

Les PRs sur ce repo POC_FACTORY déclenchent automatiquement Claude Code Review via le workflow `.github/workflows/claude-review.yml` à la racine POC_FACTORY. Mention `@claude` dans un commentaire de PR pour invoquer Claude.
```

Remplacer les 3 placeholders (PROJECT_NAME_PLACEHOLDER, DESCRIPTION_PLACEHOLDER, DATE_PLACEHOLDER).

### 7. Activation des APIs GCP (best-effort)

Vérifier d'abord que le projet `bt-ia-lab-sandbox` est sélectionné :

```powershell
gcloud config set project bt-ia-lab-sandbox
```

Puis activer les APIs nécessaires pour Cloud Run :

```powershell
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

Si la commande échoue (pas de permissions, projet non trouvé) : ne PAS abort. Mentionner dans le CR que les APIs sont à activer manuellement avant le premier déploiement Cloud Run.

### 8. Retour à la racine factory

```powershell
cd C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY
```

### 9. Commit et push dans le repo POC_FACTORY

Vérifier l'état git :

```powershell
git status
```

Si des modifications non liées sont présentes en working tree, NE PAS les inclure dans le commit. Ajouter uniquement le sous-dossier du nouveau projet :

```powershell
git add demo/<project_name>
git commit -m "factory(new-project): bootstrap demo/<project_name>"
git push origin main
```

Si le push échoue (conflit, droits, réseau) : ne PAS abort. CR `partial` avec la commande de push à relancer manuellement.

### 10. Invocation de factory-report

Invoquer la skill `factory-report` avec les inputs :

- **phase** : `new-project`
- **project** : `demo/<project_name>`
- **task_slug** : `bootstrap-<project_name>`
- **brief_path** : chemin du brief Cowork (null si invocation manuelle)
- **status** :
  - `success` si tout est passé (incluant APIs GCP activées et push réussi)
  - `partial` si scaffold complet + commit réussis MAIS APIs GCP ou push ont échoué
  - `failed` si une étape critique (validation, préconditions, scaffold, commit local) a échoué

La skill `factory-report` se charge ensuite d'écrire le CR markdown, patcher `state/factory-state.json` (notamment le champ `github_repo` qui pointera vers le sous-dossier `https://github.com/quentinr34/POC_FACTORY/tree/main/demo/<project_name>`), et afficher les marqueurs de complétion.

## Gestion des erreurs (option B : pas de rollback)

Si une étape échoue après que des artefacts aient été créés, NE PAS supprimer ce qui a été fait. Stopper, lister précisément ce qui a réussi/échoué, invoquer `factory-report` avec `status=partial`, et fournir dans "Prochaine étape suggérée" la commande pour reprendre manuellement.

| Étape échouée | Action | Status final |
|---|---|---|
| Validation input | Aucun artefact créé | `failed` |
| Préconditions (gh non auth, repo non clone, etc.) | Aucun artefact créé | `failed` |
| GCP_documentation.md manquant | Aucun artefact créé | `failed` |
| Création dossier local | Dossier partiel à nettoyer manuellement | `failed` |
| Scaffold Vite (npm error) | Dossier partiel, signaler | `failed` |
| Backend FastAPI | Tout est en local, signaler comment continuer | `partial` |
| Activation APIs GCP | Scaffold OK, APIs à activer plus tard | `partial` (note seulement) |
| `git add` ou commit | Tout en local, signaler la commande de commit | `partial` |
| `git push` | Commit local fait, signaler la commande de push | `partial` |

## Exemple complet

### Input (brief Cowork)

```
Brief : briefs/2026-05-13T14-30-00_new-project_avis-summarizer.md

Phase : new-project
Project name : avis-summarizer
Description : Mini-app qui résume un transcript Notion via Claude
```

### Sortie attendue

1. Dossier créé : `C:\Users\quentin.roche\Desktop\Factory\POC_FACTORY\demo\avis-summarizer\` avec backend FastAPI + frontend Vite scaffold + Dockerfile + README + .dockerignore.
2. APIs GCP activées sur `bt-ia-lab-sandbox` (run, cloudbuild, artifactregistry).
3. Commit `factory(new-project): bootstrap demo/avis-summarizer` poussé sur main de `quentinr34/POC_FACTORY`.
4. CR dans `reports/2026-05-13T14-32-00_new-project_avis-summarizer.md`
5. `state/factory-state.json` patché avec la nouvelle entrée `demo/avis-summarizer` (github_repo pointe vers `https://github.com/quentinr34/POC_FACTORY/tree/main/demo/avis-summarizer`).
6. Marqueurs stdout :
   ```
   FACTORY_REPORT_WRITTEN=reports/2026-05-13T14-32-00_new-project_avis-summarizer.md
   FACTORY_STATE_UPDATED=state/factory-state.json
   ```

## Anti-patterns à éviter

- Créer un repo GitHub séparé : le projet vit dans `demo/` du repo POC_FACTORY existant.
- Créer un workflow GitHub Action par projet : le workflow racine `claude-review.yml` s'applique à toutes les PRs.
- Ignorer les conventions de nommage GCP du Lab : le service Cloud Run DOIT être nommé `snd-dev-svc-<project_name>`.
- Oublier les labels GCP obligatoires au déploiement : `owner=quentin`, `project=snd`, `env=dev`, `client=internal`.
- Déployer sur un autre projet GCP que `bt-ia-lab-sandbox` : c'est le seul projet sandbox autorisé pour les démos factory.
- Forcer l'activation des APIs GCP : si ça échoue, ce n'est pas bloquant.
- Embarquer un Dockerfile mono-stage (taille d'image inutilement grosse).
- Oublier d'invoquer `factory-report` à la fin — sans CR, Cowork ne peut pas restituer.
- Commit du `node_modules/` ou de `backend/static/` (fichiers build) — vérifier qu'ils sont gitignored au niveau du repo POC_FACTORY.
- Hardcoder une URL Cloud Run dans le code frontend — utiliser des chemins relatifs `/api/*`.

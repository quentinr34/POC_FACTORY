# Factory Report — 2026-05-13T14-57-25_new-project_bootstrap-hello-factory

**Date** : 2026-05-13T14:57:25+02:00
**Project** : demo/hello-factory
**Phase** : new-project
**Brief** : —
**Status** : success
**Duration** : —

## Ce qui a été fait

- Création du dossier `demo/hello-factory/` avec arborescence standard FastAPI + Vite.
- Scaffold frontend via `npm create vite@latest` (react-ts), Tailwind v3 installé et configuré.
- Fichiers `App.tsx`, `index.css`, `tailwind.config.js`, `vite.config.ts` écrasés avec les templates CGI Factory.
- Création du backend FastAPI (`main.py`, `requirements.txt`) avec route `/api/health` et service du SPA buildé.
- Création du `Dockerfile` multi-stage (Node 20 Alpine + Python 3.12 slim) et `.dockerignore`.
- Activation des APIs GCP `run.googleapis.com`, `cloudbuild.googleapis.com`, `artifactregistry.googleapis.com` sur `bt-ia-lab-sandbox`.
- Commit `factory(new-project): bootstrap demo/hello-factory` (26 fichiers, 4238 insertions) poussé sur `main`.

## Fichiers modifiés / créés

- `demo/hello-factory/backend/main.py` (created, 21 lines)
- `demo/hello-factory/backend/requirements.txt` (created, 2 lines)
- `demo/hello-factory/Dockerfile` (created, 18 lines)
- `demo/hello-factory/.dockerignore` (created, 8 lines)
- `demo/hello-factory/README.md` (created, 58 lines)
- `demo/hello-factory/frontend/` — 21 fichiers scaffold Vite (created, ~4131 lines total)

## Décisions techniques prises

- Tailwind v3 installé explicitement (au lieu de v4 installé par défaut par Vite) : la `tailwind.config.js` requise par la skill est du format v3 ; `npx tailwindcss init -p` n'existe plus en v4.
- Le projet vit dans `demo/hello-factory/` du repo `quentinr34/POC_FACTORY` (pas de repo séparé) : conforme à la convention factory.
- `vite.config.ts` redirige le build vers `../backend/static` pour le serving SPA par FastAPI.

## Commandes exécutées

```bash
npm create vite@latest frontend -- --template react-ts
npm install
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project=bt-ia-lab-sandbox
git add demo/hello-factory
git commit -m "factory(new-project): bootstrap demo/hello-factory"
git push origin main
```

## Blocages / questions ouvertes

Aucun.

## Prochaine étape suggérée

Cowork peut maintenant lancer la phase `speckit-setup` pour cadrer le projet `hello-factory`, ou procéder directement au déploiement Cloud Run via la skill `factory-deploy-cloud-run` (service : `snd-dev-svc-hello-factory`).

## État mis à jour dans factory-state.json

```json
{
  "projects": {
    "demo/hello-factory": {
      "phases": {
        "new-project": {
          "status": "done",
          "completed_at": "2026-05-13T14:57:25+02:00",
          "report": "reports/2026-05-13T14-57-25_new-project_bootstrap-hello-factory.md"
        }
      },
      "github_repo": "https://github.com/quentinr34/POC_FACTORY/tree/main/demo/hello-factory"
    }
  }
}
```

# Factory Report — 2026-05-13T16-53-18_new-project_bootstrap-hello-factory-v2

**Date** : 2026-05-13T16:58:30+02:00
**Project** : demo/hello-factory-v2
**Phase** : new-project
**Brief** : —
**Status** : success
**Duration** : 279s (~4 minutes 40)

## Ce qui a été fait

- Bootstrap du projet `demo/hello-factory-v2` dans le repo POC_FACTORY existant (pas de nouveau repo GitHub créé).
- Scaffold Vite + React + TypeScript (`npm create vite@latest frontend --template react-ts`) et installation de Tailwind CSS v3 + PostCSS + Autoprefixer.
- Customisation des 4 fichiers Vite : `tailwind.config.js` (couleur cgi=#5336AB), `src/index.css` (directives @tailwind), `src/App.tsx` (UI minimaliste ping /api/health), `vite.config.ts` (build outDir vers `../backend/static`, proxy /api).
- Création du backend FastAPI minimal : `backend/main.py` (route /api/health + SPA fallback) et `backend/requirements.txt` (FastAPI 0.118.0 + uvicorn 0.32.0).
- Création du `Dockerfile` multi-stage (build frontend node:20-alpine puis runtime python:3.12-slim) et `.dockerignore`.
- Activation best-effort des APIs GCP `run`, `cloudbuild`, `artifactregistry` sur le projet `bt-ia-lab-sandbox`.
- Commit `c2b978e` (26 fichiers, +4210 lignes) poussé sur `origin/main`.
- Marqueurs `[FACTORY_PROGRESS]` émis en stdout pour les 10 étapes (le log fichier était tenu exclusivement par Cowork pendant l'exécution, fallback stdout-only).

## Fichiers modifiés / créés

26 fichiers créés sous `demo/hello-factory-v2/` :

- Racine projet : `.dockerignore`, `Dockerfile`, `README.md`
- `backend/` : `main.py`, `requirements.txt`
- `frontend/` : 21 fichiers (scaffold Vite complet + tailwind.config.js + postcss.config.js, App.tsx/vite.config.ts/index.css customisés)

## Décisions techniques prises

- Tailwind v3 imposé (au lieu de v4) — la skill v3 mentionne explicitement que v3 est plus stable et compatible avec la config CGI.
- Pas de rollback en cas d'échec partiel — option B de la skill, le state reflète l'état réel.
- Push direct sur `main` (pas de feature branch) — convention de la factory pour les bootstraps demo.

## Commandes exécutées

```bash
npm create vite@latest frontend -- --template react-ts
npm install
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
gcloud services enable run.googleapis.com --project=bt-ia-lab-sandbox
gcloud services enable cloudbuild.googleapis.com --project=bt-ia-lab-sandbox
gcloud services enable artifactregistry.googleapis.com --project=bt-ia-lab-sandbox
git add demo/hello-factory-v2
git commit -m "factory(new-project): bootstrap demo/hello-factory-v2"
git push origin main
```

## Progression par étape

Le fichier `logs/<task_id>.log` était verrouillé en exclusivité par Cowork pendant toute l'exécution. Les marqueurs ont été émis uniquement en stdout. Durées reconstituées depuis les markers émis :

| # | Étape | Statut | Durée |
|---|---|---|---|
| 1 | preconditions | done | 4s |
| 2 | scaffold-dir | done | 0s |
| 3 | vite-scaffold | done | 36s |
| 4 | backend-fastapi | done | 3s |
| 5 | dockerfile | done | 2s |
| 6 | config-files | done | 3s |
| 7 | gcp-apis | done | 11s |
| 8 | cd-root | done | 0s |
| 9 | git-commit-push | done | 6s |
| 10 | invoke-report | done | ~15s |

Durée totale wall-clock (premier marker -> CR écrit) : ~279s (~4 min 40).

## Blocages / questions ouvertes

- Le log fichier `logs/<task_id>.log` était ouvert en lecture exclusive par Cowork ; toute tentative d'append a échoué (`IOException: in use by another process`). La v3 de `factory-new-project` prétend écrire en double (stdout + log fichier) mais ce double-write est incompatible avec le mode actuel de Cowork. À résoudre côté harness ou en repassant la skill v3 en stdout-only.

## Prochaine étape suggérée

Lancer un `docker build` local de `demo/hello-factory-v2` pour valider le Dockerfile multi-stage avant le premier `gcloud run deploy snd-dev-svc-hello-factory-v2`.

## État mis à jour dans factory-state.json

```json
{
  "last_updated": "2026-05-13T16:58:30+02:00",
  "projects.demo/hello-factory-v2": {
    "name": "hello-factory-v2",
    "created_at": "2026-05-13T16:58:30+02:00",
    "phases.new-project": {
      "status": "done",
      "completed_at": "2026-05-13T16:58:30+02:00",
      "report": "reports/2026-05-13T16-53-18_new-project_bootstrap-hello-factory-v2.md",
      "duration_seconds": 279
    },
    "github_repo": "https://github.com/quentinr34/POC_FACTORY/tree/main/demo/hello-factory-v2"
  },
  "recent_reports[0]": "reports/2026-05-13T16-53-18_new-project_bootstrap-hello-factory-v2.md"
}
```

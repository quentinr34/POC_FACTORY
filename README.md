# POC_FACTORY — CGI Augmented SDLC Factory

POC démontrant la chaîne complète de production logicielle assistée par IA, du cadrage à la mise en production, via Cowork comme orchestrateur user-facing et Claude Code comme exécuteur technique.

## Composants

- **Cowork** : orchestrateur user-facing (lit Notion, pilote Claude Code, anime les démos)
- **Claude Code** : exécuteur technique CLI (skills factory-*, Git, GCP, Docker)
- **SpecKit** : cadrage, conception, plan, tasks, implémentation
- **GitHub Actions** : Claude Code Review automatique sur PRs (workflow racine)
- **Google Cloud Run** : déploiement applicatif (projet `bt-ia-lab-sandbox`, région `europe-west9`)

## Structure du repo

```
POC_FACTORY/
├── .claude/skills/        skills factory-* utilisées par Claude Code
├── .github/workflows/     claude-review.yml (PR review automatique)
├── briefs/                prompts structurés écrits par Cowork pour Claude Code
├── reports/               CR structurés écrits par Claude Code via factory-report
├── state/                 factory-state.json (état lu par Cowork et le cockpit)
├── logs/                  logs bruts d'exécution (non versionnés)
├── cockpit/               Live Artifact cockpit factory
├── demo/                  projets générés par la factory
└── GCP_documentation.md   règles GCP du Lab BT IA FACTORY
```

## Gouvernance GCP

Voir `GCP_documentation.md` à la racine. Toute action GCP de la factory respecte ces règles : projet `bt-ia-lab-sandbox`, conventions de nommage `snd-dev-<type>-<nom>`, labels obligatoires `owner=quentin / project=snd / env=dev / client=internal`.

## Statut

POC en cours de construction. Skills disponibles à ce jour :

- `factory-report` (à installer)
- `factory-new-project` (à installer)

Les skills sont déposées dans `.claude/skills/<skill-name>/SKILL.md`.

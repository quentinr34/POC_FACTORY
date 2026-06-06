# Déploiement & monitoring — Quote Catcher

Service déployé sur **Cloud Run** (région `europe-west9`) via le workflow
`.github/workflows/deploy.yml` (déclenchement manuel `workflow_dispatch`).

## Prérequis GCP (une fois)

1. **APIs** : activer `run.googleapis.com`, `firestore.googleapis.com`,
   `secretmanager.googleapis.com`, `cloudbuild.googleapis.com`,
   `monitoring.googleapis.com`.
2. **Firestore** : créer une base en mode Native dans `europe-west9`.
3. **Secret Claude** :
   ```bash
   echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
   ```
4. **Service account de runtime** avec rôles `roles/datastore.user` et
   `roles/secretmanager.secretAccessor`.
5. **Workload Identity Federation** pour GitHub Actions (recommandé, sans clé JSON).

## Secrets GitHub Actions à configurer

| Secret | Description |
| --- | --- |
| `GCP_PROJECT_ID` | ID du projet GCP |
| `GCP_WIF_PROVIDER` | Provider Workload Identity Federation |
| `GCP_SERVICE_ACCOUNT` | Service account de déploiement |

## Accès (IAP / IAM)

Le service est déployé avec `--no-allow-unauthenticated`. L'accès interne CGI
se fait via IAM (`roles/run.invoker`) ou un IAP devant un load balancer.

## Monitoring de base

- **Health check** : endpoint `GET /healthz` (utilisé pour les sondes).
- **Logs structurés** : l'application émet du JSON sur stdout
  (`severity`, `message`, `method`, `path`, `status`, `duration_ms`),
  ingéré automatiquement par Cloud Logging.
- **Métriques Cloud Run** : latence, taux d'erreur, instances (intégrées).

### Uptime check + alerte (exemple)

```bash
# Uptime check sur /healthz
gcloud monitoring uptime create quote-catcher-health \
  --resource-type=uptime-url \
  --host="<SERVICE_URL_SANS_SCHEME>" \
  --path="/healthz"

# Politique d'alerte sur le taux d'erreur 5xx (via la console Monitoring
# ou un fichier de policy JSON applique avec :)
gcloud alpha monitoring policies create --policy-from-file=alert-5xx.json
```

# BT IA FACTORY — Infrastructure GCP — Documentation technique

---

## 1. Contexte et objectifs

Ce document décrit l'infrastructure Google Cloud Platform (GCP) mise en place pour le BT IA FACTORY. Il couvre la structure des projets, les règles de gouvernance, les mécanismes de sécurité et les procédures opérationnelles.

### 1.1 Périmètre

L'infrastructure GCP est hébergée sur un compte personnel rattaché à l'adresse quentin.roche@cgi.com. Elle supporte quatre cas d'usage principaux :

- Développement et industrialisation de Kuiper Recast
- Expérimentation R&D et exploration de nouveaux modèles
- Démonstrations clients en contexte avant-vente
- Hébergement de POC

### 1.2 Principes directeurs

| Principe | Traduction concrète |
|---|---|
| **Coût maîtrisé** | Budget Max 300 €/mois · alertes automatiques · arrêt des VMs hors heures ouvrées |
| **Traçabilité totale** | Labels obligatoires sur toutes les ressources · rapport de coûts par projet et par client |
| **Sécurité** | Zéro secret en clair · Secret Manager |
| **Propreté opérationnelle** | Suppression automatique des ressources orphelines · suppression POC en une commande |

---

## 2. Structure GCP

### 2.1 Organisation des projets

L'infrastructure est organisée en quatre projets GCP distincts, chacun correspondant à un cas d'usage spécifique. Cette séparation permet d'isoler les coûts, les droits et les ressources par domaine.

| Project ID | Usage | Budget | Abréviation | Env |
|---|---|---|---|---|
| bt-ia-kuiper-dev | Kuiper / Recast — POC techniques | 80 €/mois | **kpr** | dev |
| bt-ia-lab-sandbox | R&D · expérimentation · modèles | 50 €/mois | **snd** | dev |
| bt-ia-client-demo | Démos AVV — environnements stables | 40 €/mois | **demo** | stg |
| bt-ia-poc-clients | POC facturables — client1, client2, etc. | 60 €/mois | **poc** | dev |

### 2.2 Régions

La répartition des services entre les deux régions Europe répond à une contrainte de disponibilité GCP :

| Région | Services | Raison |
|---|---|---|
| europe-west1 (Belgique) | Cloud Functions · Cloud Scheduler | Seule région EU supportant ces services |
| europe-west9 (Paris) | VMs · Buckets · Vertex AI | Proximité · conformité France pour les POC clients |

> **Note importante**
> Les fonctions de monitoring (auto-stop, scan labels) tournent en europe-west1 mais agissent sur les ressources de toutes les régions. La région d'une fonction n'a aucun impact sur sa capacité à piloter des ressources dans d'autres régions.

### 2.3 Matrice IAM

Les droits sont définis au niveau de chaque projet.

| Membre | kuiper-dev | lab-sandbox | client-demo | poc-clients |
|---|---|---|---|---|
| **Quentin** | Owner | Owner | Owner | Owner |
| **Clément** | Owner | Owner | Owner | Owner |
| **Yoann** | Owner | Owner | Owner | Owner |
| **Membres** | Editor | Editor | Viewer | — |

---

## 3. Budget et alertes

### 3.1 Structure budgétaire

Un budget global de 300 €/mois est défini sur le compte de facturation, avec des budgets individuels par projet. Les alertes sont envoyées à quentin.roche@cgi.com, clement.leroy@cgi.com, yoann.joulia@cgi.com, pierre.pys@cgi.com.

| Niveau | Seuil | Alertes déclenchées | Action |
|---|---|---|---|
| Budget global | 300 €/mois | 50% · 75% · 90% · 100% | Email Quentin + Clément + Yoann + Pierre |
| bt-ia-kuiper-dev | 80 €/mois | 80% · 100% | Email alerte |
| bt-ia-lab-sandbox | 50 €/mois | 80% · 100% | Email alerte |
| bt-ia-client-demo | 40 €/mois | 80% · 100% | Email alerte |
| bt-ia-poc-clients | 60 €/mois | 80% · 100% | Email alerte |

### 3.2 Escalade budgétaire

| Seuil | Moment | Action immédiate | Action sous 24h |
|---|---|---|---|
| 50% | ~150 € | Information — consommation normale | Aucune |
| 75% | ~225 € | Revue du projet le plus consommateur | Optimisation si possible |
| 90% | ~270 € | Suspension des workloads non urgents | Arrêt VMs et endpoints inutilisés |
| 100% | 300 € | Notification — décision go/stop | Arbitrage manuel |

> **Rappel important**
> GCP n'arrête pas automatiquement les ressources en cas de dépassement de budget. Les alertes sont informatives. L'action manuelle reste nécessaire au-delà de 90%. L'arrêt automatique des VMs (section 4) est le principal mécanisme de contrôle des coûts.

---

## 4. Arrêt automatique des VMs

### 4.1 Planning d'exécution

Un scheduler Cloud (bt-ia-kuiper-dev, europe-west1) déclenche automatiquement l'arrêt et le redémarrage des VMs selon le planning suivant :

| Job | Cron | Timezone | Action |
|---|---|---|---|
| bt-ia-stop-soir | `0 19 * * 1-5` | Europe/Paris | Arrêt VMs — 19h lun-ven |
| bt-ia-stop-weekend | `0 19 * * 5` | Europe/Paris | Arrêt total — ven 19h → lun 8h |
| bt-ia-start-lundi | `0 8 * * 1` | Europe/Paris | Démarrage VMs auto-start=true |

### 4.2 Labels de contrôle

Deux labels pilotent le comportement de l'auto-stop sur chaque VM :

| Label | Valeurs | Comportement | Usage typique |
|---|---|---|---|
| **auto-stop** | true / false | true = arrêt planifié · false = VM jamais arrêtée | Par défaut true sur toutes les VMs |
| **auto-start** | true / false | true = redémarrage automatique lundi 8h | Opt-in — à poser explicitement |

### 4.3 Cas du budget critique (> 90%)

- Si le budget dépasse 90% et qu'une VM persistante (auto-stop=false) est allumée en journée → email d'alerte nommant la VM, son projet, son owner et son coût estimé
- Si le budget dépasse 90% et qu'une VM persistante est allumée après 19h ou le weekend → arrêt forcé

### 4.4 Poser un label sur une VM

```bash
gcloud compute instances add-labels NOM_VM \
  --zone=europe-west9-a \
  --project=bt-ia-kuiper-dev \
  --labels=auto-stop=false
```

---

## 5. Politique de labels

### 5.1 Labels obligatoires

Toutes les ressources GCP du Lab doivent porter les labels suivants. L'absence d'un label déclenche la procédure de ressource orpheline (section 5.2).

| Label | Obligatoire | Valeurs autorisées | Utilisation |
|---|---|---|---|
| **owner** | Oui | quentin · clement · yoann | Rapport coûts · alertes orphelins |
| **project** | Oui | kpr · snd · demo · poc | Rapport coûts par projet |
| **env** | Oui | dev · stg · prd | Filtrage · politique réseau |
| **auto-stop** | Oui (VMs) | true · false | Script arrêt automatique |
| **client** | Si poc/demo | Client1 · client2 · clientN · internal | Rapport coûts par client |
| **poc-id** | Si POC | Identifiant court du POC (ex: client1) | Script de suppression automatique en fin de POC |

### 5.2 Règle zero-label — procédure orphelin

Toute ressource détectée sans labels obligatoires est traitée selon la procédure suivante. Un scan automatique s'exécute toutes les 6 heures.

| Étape | Moment | Action | Ressource concernée |
|---|---|---|---|
| Détection | T+0 | Tag `orphan-detected-at` + email d'alerte | Toutes |
| Désactivation | T+24h | Stop VM · undeploy endpoint · désactivation SA · blocage bucket | Toutes |
| Quarantaine | T+24h | Contenu déplacé vers bt-ia-quarantine | Buckets GCS uniquement |
| Suppression | T+7j | Suppression définitive si aucune action | Toutes |
| Purge quarantaine | T+7j | Purge définitive du contenu en quarantaine | Buckets GCS |

Pour réactiver une ressource stoppée, poser les labels manquants puis redémarrer manuellement. La ressource sera réactivée au prochain cycle de scan.

---

## 6. Conventions de nommage

### 6.1 Structure

Toutes les ressources GCP suivent la convention : `[projet]-[env]-[type]-[nom-court]`

| Segment | Valeurs | Exemple | Règle |
|---|---|---|---|
| **[projet]** | kpr · snd · demo · poc | kpr | Obligatoire |
| **[env]** | dev · stg · prd | dev | Obligatoire |
| **[type]** | vm · bkt · ep · sa | vm | Obligatoire |
| **[nom-court]** | Libre, descriptif, kebab-case | recast-worker | Obligatoire · max 63 chars total |

### 6.2 Exemples par type de ressource

| Type | Exemple valide | Exemple invalide |
|---|---|---|
| VM | `kpr-dev-vm-recast-worker` | `vm-test1` / `MyVM_Kuiper` |
| Bucket | `poc-dev-bkt-rts-corpus` | `bucket-new` / `TestBucket` |
| Endpoint | `kpr-dev-ep-recast-v1` | `endpoint1` / `kuiper_endpoint` |
| Service Account | `kpr-dev-sa-scheduler` | `my-sa` / `ServiceAccount_Dev` |

> **Règles de nommage**
> - Minuscules uniquement — jamais de majuscules
> - Tirets comme séparateurs (kebab-case) — jamais d'underscores
> - Maximum 63 caractères (limite GCP)
> - Le [nom-court] doit être descriptif — éviter test, tmp, new, 1, 2…

---

## 7. Sécurité des secrets et credentials

### 7.1 Règle fondamentale

> **Règle absolue — zéro secret en clair**
> Aucun secret, token, clé API ou credential ne doit apparaître dans le code, les fichiers de configuration, les variables d'environnement en clair, ou dans GitLab. Cette règle s'applique à tous les membres sans exception.

### 7.2 Stockage des secrets

| Type de secret | Stockage | Mode d'accès | Rotation |
|---|---|---|---|
| Clés Service Account | Secret Manager GCP | Workload Identity Federation | 90 jours |
| Tokens API (HuggingFace, Anthropic…) | Secret Manager GCP | Variables CI/CD GitLab | 90 jours |
| Credentials BDD | Secret Manager GCP | IAM + Secret Manager API | 90 jours |
| Clés API clients | Secret Manager GCP | Variables CI/CD GitLab | Fin de mission |

### 7.3 Secrets structurels du Lab

| Nom du secret | Projet | Usage |
|---|---|---|
| kpr-dev-token-huggingface | bt-ia-kuiper-dev | Accès modèles HuggingFace |
| kpr-dev-token-anthropic | bt-ia-kuiper-dev | Accès API Claude / Anthropic |
| kpr-dev-token-gitlab | bt-ia-kuiper-dev | CI/CD GitLab |
| snd-dev-token-huggingface | bt-ia-lab-sandbox | Accès modèles HuggingFace — sandbox |
| snd-dev-token-anthropic | bt-ia-lab-sandbox | Accès API Claude / Anthropic — sandbox |

### 7.4 Renseigner ou faire tourner un secret

```bash
echo -n "VALEUR_DU_SECRET" | gcloud secrets versions add NOM_SECRET \
  --project=PROJECT_ID --data-file=-
```

### 7.5 Procédure en cas d'exposition

- Révoquer immédiatement le secret exposé (ne pas attendre d'évaluer l'impact)
- Créer une nouvelle version du secret dans Secret Manager
- Purger l'historique git si le secret a été commité : `git filter-branch` ou BFG
- Notifier Quentin et enregistrer l'incident dans Cloud Logging
- Auditer les accès sur les 24h précédentes via Cloud Audit Logs

### 7.6 Règles GitLab

- Fichier `.gitignore` obligatoire sur chaque repo : `*.json` · `*.env` · `*credentials*` · `*secret*`
- Secret detection SAST activé — tout push contenant un pattern de secret est bloqué
- Jamais de clé JSON de Service Account téléchargée localement — utiliser Workload Identity
- 1 Service Account = 1 usage — jamais de SA générique partagé entre plusieurs workloads

---

## 8. Suppression projet / POC

### 8.1 Convention de nommage des ressources POC

Toutes les ressources créées dans le cadre d'un POC doivent respecter deux règles cumulatives pour permettre leur suppression automatique :

- Nom préfixé par `poc-[POC_ID]-` : `poc-client1-vm-worker` · `poc-client1-bkt-corpus`
- Label `poc-id=[POC_ID]` posé sur chaque ressource

> **Exemple — POC Client1**
> - VM : `poc-client1-vm-worker` (label `poc-id=client1`)
> - Bucket : `poc-client1-bkt-corpus` (label `poc-id=client1`)
> - Endpoint : `poc-client1-ep-rag-v1` (label `poc-id=client1`)
> - SA : `poc-client1-sa-runner` (label `poc-id=client1`)

### 8.2 Script de suppression

Le script `suppression_poc.sh` supprime toutes les ressources d'un POC en une seule commande. Il demande une confirmation explicite avant toute suppression.

```bash
bash suppression_poc.sh [POC_ID] [PROJECT_ID]
```

Exemples d'utilisation :

```bash
suppression_poc.sh client1 bt-ia-poc-clients
suppression_poc.sh client2 bt-ia-poc-clients
suppression_poc.sh kuiper-v2 bt-ia-kuiper-dev
```

### 8.3 Ressources couvertes par le script

| Type de ressource | Méthode de détection | Action |
|---|---|---|
| VMs Compute Engine | `labels.poc-id=[POC_ID]` | Suppression |
| Endpoints Vertex AI | `labels.poc-id=[POC_ID]` | Undeploy + suppression |
| Buckets GCS | `labels.poc-id=[POC_ID]` | Suppression + contenu |
| Cloud Run services | `metadata.labels.poc-id=[POC_ID]` | Suppression (si API activée) |
| Cloud Functions | `labels.poc-id=[POC_ID]` | Suppression (si API activée) |
| Service Accounts | `email~poc-[POC_ID]` | Suppression |

### 8.4 Vérification post-teardown

```bash
gcloud asset search-all-resources \
  --scope=projects/PROJECT_ID \
  --query="labels.poc-id=POC_ID"
```

---

## 9. Scripts de déploiement

L'ensemble de l'infrastructure est déployé via 5 scripts bash idempotents — ils peuvent être relancés sans risque si une étape échoue.

| Script | Étape | Contenu |
|---|---|---|
| **step1_structure_gcp.sh** | Étape 1 | Création projets · APIs · IAM · budgets et alertes billing |
| **step2_scheduler_autostop.sh** | Étape 2 | SA scheduler · Cloud Function auto-stop · 3 jobs Scheduler |
| **step3_labels_scan.sh** | Étape 3 | Bucket quarantaine · Cloud Function scan labels · job scan 6h |
| **step4_secrets.sh** | Étape 4 | Activation Secret Manager · création secrets structurels · droits SA |
| **suppression_poc.sh** | Outil récurrent | Suppression propre de toutes les ressources d'un POC |

> **Prérequis d'exécution**
> - `gcloud` CLI installé et authentifié (`gcloud auth login`)
> - Compte de facturation GCP actif
> - Exécution depuis Google Cloud Shell recommandée (bash natif, gcloud préconfiguré)
> - Les scripts step2 à step4 nécessitent que step1 soit terminé

---

## 10. Contacts et gouvernance

### 10.1 Équipe

| Membre | Rôle Lab | Email | Droits GCP |
|---|---|---|---|
| **Quentin Roche** | Pilote | quentin.roche@cgi.com | Owner |
| **Clément** | Lead Technique | clement.leroy@cgi.com | Owner |
| **Yoann Joliat** | Lead Technique | yoann.joulia@cgi.com | Owner |

### 10.2 Actions récurrentes

| Action | Fréquence | Responsable | Description |
|---|---|---|---|
| Revue budgétaire | Mensuelle | — | Analyse coûts par projet et client · ajustements budgets |
| Rotation secrets | 90 jours | — | Renouvellement des tokens et clés API |
| Teardown POC terminés | Fin de POC | — | Lancer `step5_teardown_poc.sh` dès que le POC est clôturé |
| Revue ressources orphelines | Mensuelle | — | Vérifier Cloud Logging — ressources taguées `orphan-detected-at` |
| Invitations Owner | À la demande | — | Ajouter nouveaux membres Owner via console GCP |

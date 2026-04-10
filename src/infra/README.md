# POMS — Azure deployment

Infrastructure-as-code and first-time bootstrap for deploying POMS to Azure
Container Apps + Static Web Apps.

## What gets provisioned

| Resource | Purpose |
|---|---|
| Log Analytics workspace | Observability sink for Container Apps |
| Azure Container Registry (Basic) | Hosts the backend container image |
| User-assigned managed identity | Grants the Container App `AcrPull` on the registry |
| Storage account + Azure Files share | Persists the LanceDB vector store |
| Container Apps managed environment | Runtime with the file share mounted |
| Container App (`ca-poms-backend`) | FastAPI + Gmail poller, min=1 replica |
| PostgreSQL Flexible Server (B1ms) | Application database |
| Azure OpenAI account | `gpt-4o-mini` + `text-embedding-3-large` deployments |
| Static Web App (Free) | React frontend |

## Files

```
src/infra/
├── main.bicep      # All resources, declarative
├── bootstrap.sh    # First-time deploy + GitHub OIDC setup
└── README.md       # This file
```

## Prerequisites

- **Azure CLI** ≥ 2.50, logged in with Contributor on the target subscription
- **GitHub CLI** (`gh`), authenticated with admin access to the repo
- **jq**

## First-time deploy

```bash
./src/infra/bootstrap.sh
```

The script:

1. Registers the required resource providers.
2. Creates the resource group.
3. Deploys `main.bicep` with a hello-world placeholder image so the Container
   App exists before CI builds the real one.
4. Creates a GitHub OIDC app registration + two federated credentials
   (`refs/heads/main` and `environment:production`).
5. Assigns `Contributor` on the resource group and `AcrPush` on the ACR to the
   service principal.
6. Fetches the Static Web App deploy token.
7. Seeds the following GitHub Actions secrets on the repo:

   | Secret | Used by |
   |---|---|
   | `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` | OIDC login in both workflows |
   | `AZURE_RESOURCE_GROUP` | Backend deploy |
   | `AZURE_CONTAINER_REGISTRY` | Backend deploy (image push) |
   | `AZURE_CONTAINER_APP` | Backend deploy (`az containerapp update`) |
   | `AZURE_CONTAINER_APP_FQDN` | Frontend build (baked into `VITE_API_BASE_URL`) |
   | `AZURE_STATIC_WEB_APP_TOKEN` | Frontend deploy |

After bootstrap, cutting a `v*` tag (e.g. `v0.1.0`) triggers
`.github/workflows/deploy-backend.yml` and `deploy-frontend.yml`. Pushes to
`main` only run CI (`backend.yml`, `frontend.yml`) — they do **not** deploy.

```bash
# Release flow
git checkout main && git pull
git tag v0.1.0
git push origin v0.1.0
# → both deploy workflows run in parallel
```

Both workflows also support manual invocation via `workflow_dispatch` from the
Actions tab.

## Environment variable overrides

| Variable | Default |
|---|---|
| `RG_NAME` | `rg-poms-demo` |
| `LOCATION` | `northeurope` |
| `NAME_PREFIX` | `poms` |
| `ENVIRONMENT` | `demo` |
| `GITHUB_REPO` | auto-detected via `gh` |
| `GITHUB_ENV` | `production` |
| `SP_NAME` | `sp-poms-github` |

## One-off: seed the RAG vector store

The Bicep template provisions the Azure Files share that backs `/app/data`,
but the LanceDB table itself has to be populated once, after the first
revision is running:

```bash
az containerapp exec \
  --name ca-poms-backend \
  --resource-group rg-poms-demo \
  --command "python -m scripts.ingest_knowledge"
```

## Gmail polling (not wired in this template)

The backend reads Gmail OAuth creds from `credentials.json` / `token.json`
**on disk**, not from env vars. Container Apps doesn't natively mount secrets
as files, so this demo template leaves Gmail unconfigured — the app logs a
warning at startup and polling is disabled. The rest of the pipeline (webhook
ingestion, extraction, validation, routing) works unchanged.

To enable Gmail in production, either:

- Add a small entrypoint that serialises Container App secrets into the file
  paths the app expects, or
- Refactor `services/email.py` to read OAuth values from env vars directly.

## Teardown

```bash
# Delete all Azure resources
az group delete --name rg-poms-demo --yes --no-wait

# Remove the OIDC app registration
az ad app delete --id "$(az ad app list --display-name sp-poms-github --query '[0].appId' -o tsv)"
```

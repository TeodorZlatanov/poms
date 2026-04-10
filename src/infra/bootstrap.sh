#!/usr/bin/env bash
# ============================================================================
# POMS — First-time Azure bootstrap
#
# Creates the resource group, deploys the Bicep template, configures GitHub
# Actions OIDC via federated credentials, and seeds the CI secrets needed for
# subsequent deploys from `main`.
#
# After this script succeeds, pushing to main triggers the deploy jobs in
# .github/workflows/ and this script should not need to run again.
#
# Requirements:
#   - Azure CLI >= 2.50, logged in with Owner/Contributor on the subscription
#   - GitHub CLI (`gh`), authenticated with admin access to the repo
#   - jq
#
# Usage:
#   ./src/infra/bootstrap.sh
# ============================================================================
set -euo pipefail

# --- Configuration (override via env vars) ---------------------------------
RG_NAME="${RG_NAME:-rg-poms-demo}"
LOCATION="${LOCATION:-northeurope}"
NAME_PREFIX="${NAME_PREFIX:-poms}"
ENVIRONMENT="${ENVIRONMENT:-demo}"
GITHUB_REPO="${GITHUB_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
GITHUB_ENV="${GITHUB_ENV:-production}"
SP_NAME="${SP_NAME:-sp-poms-github}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
TEMPLATE="${SCRIPT_DIR}/main.bicep"

# --- Prerequisites ----------------------------------------------------------
command -v az >/dev/null || { echo "az CLI not found"; exit 1; }
command -v gh >/dev/null || { echo "gh CLI not found"; exit 1; }
command -v jq >/dev/null || { echo "jq not found"; exit 1; }
[[ -f "$TEMPLATE" ]]     || { echo "Template not found: $TEMPLATE"; exit 1; }

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
echo "Subscription: ${SUBSCRIPTION_ID}"
echo "Repository:   ${GITHUB_REPO}"
echo "Resource grp: ${RG_NAME} (${LOCATION})"
echo

# --- Prompt for secrets -----------------------------------------------------
read -rsp "PostgreSQL admin password (min 8 chars, mixed case+digits): " POSTGRES_PASSWORD
echo

# --- Register resource providers --------------------------------------------
echo ">>> Registering resource providers"
for provider in Microsoft.App \
                Microsoft.ContainerRegistry \
                Microsoft.DBforPostgreSQL \
                Microsoft.OperationalInsights \
                Microsoft.CognitiveServices \
                Microsoft.Storage \
                Microsoft.Web \
                Microsoft.ManagedIdentity; do
  az provider register --namespace "$provider" --wait -o none
  echo "  $provider"
done

# --- Create resource group --------------------------------------------------
echo ">>> Creating resource group"
az group create --name "$RG_NAME" --location "$LOCATION" -o none

# --- Deploy infrastructure --------------------------------------------------
echo ">>> Deploying Bicep template"
DEPLOYMENT_NAME="poms-bootstrap-$(date +%Y%m%d%H%M%S)"
az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$RG_NAME" \
  --template-file "$TEMPLATE" \
  --parameters \
    namePrefix="$NAME_PREFIX" \
    environment="$ENVIRONMENT" \
    postgresAdminPassword="$POSTGRES_PASSWORD" \
  -o none

# --- Read Bicep outputs -----------------------------------------------------
OUTPUTS="$(az deployment group show -g "$RG_NAME" -n "$DEPLOYMENT_NAME" --query properties.outputs)"
ACR_NAME="$(echo "$OUTPUTS"         | jq -r .containerRegistryName.value)"
ACR_LOGIN_SERVER="$(echo "$OUTPUTS" | jq -r .containerRegistryLoginServer.value)"
CONTAINER_APP_NAME="$(echo "$OUTPUTS" | jq -r .containerAppName.value)"
CONTAINER_APP_FQDN="$(echo "$OUTPUTS" | jq -r .containerAppFqdn.value)"
STATIC_WEB_APP_NAME="$(echo "$OUTPUTS" | jq -r .staticWebAppName.value)"
STATIC_WEB_APP_HOSTNAME="$(echo "$OUTPUTS" | jq -r .staticWebAppHostname.value)"

# --- GitHub OIDC: app registration + federated credentials ------------------
echo ">>> Configuring GitHub Actions OIDC"
APP_ID="$(az ad app list --display-name "$SP_NAME" --query '[0].appId' -o tsv)"
if [[ -z "$APP_ID" ]]; then
  APP_ID="$(az ad app create --display-name "$SP_NAME" --query appId -o tsv)"
  az ad sp create --id "$APP_ID" -o none
fi
SP_OBJECT_ID="$(az ad sp show --id "$APP_ID" --query id -o tsv)"

# Federated credentials: main branch + production environment
for subject in "repo:${GITHUB_REPO}:ref:refs/heads/main" \
               "repo:${GITHUB_REPO}:environment:${GITHUB_ENV}"; do
  name="poms-$(echo "$subject" | tr ':/' '--')"
  az ad app federated-credential create --id "$APP_ID" --parameters "$(cat <<EOF
{
  "name": "${name:0:60}",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "${subject}",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF
)" -o none 2>/dev/null || echo "  federated credential already exists: ${subject}"
done

# --- Role assignments -------------------------------------------------------
echo ">>> Assigning roles to the CI service principal"
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role Contributor \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG_NAME}" \
  -o none 2>/dev/null || true

az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role AcrPush \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG_NAME}/providers/Microsoft.ContainerRegistry/registries/${ACR_NAME}" \
  -o none 2>/dev/null || true

# --- Static Web Apps deploy token -------------------------------------------
SWA_TOKEN="$(az staticwebapp secrets list \
  --name "$STATIC_WEB_APP_NAME" \
  --resource-group "$RG_NAME" \
  --query properties.apiKey -o tsv)"

# --- Seed GitHub Actions secrets --------------------------------------------
echo ">>> Setting GitHub Actions secrets on ${GITHUB_REPO}"
gh secret set AZURE_CLIENT_ID            --repo "$GITHUB_REPO" --body "$APP_ID"
gh secret set AZURE_TENANT_ID            --repo "$GITHUB_REPO" --body "$TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID      --repo "$GITHUB_REPO" --body "$SUBSCRIPTION_ID"
gh secret set AZURE_RESOURCE_GROUP       --repo "$GITHUB_REPO" --body "$RG_NAME"
gh secret set AZURE_CONTAINER_REGISTRY   --repo "$GITHUB_REPO" --body "$ACR_LOGIN_SERVER"
gh secret set AZURE_CONTAINER_APP        --repo "$GITHUB_REPO" --body "$CONTAINER_APP_NAME"
gh secret set AZURE_CONTAINER_APP_FQDN   --repo "$GITHUB_REPO" --body "$CONTAINER_APP_FQDN"
gh secret set AZURE_STATIC_WEB_APP_TOKEN --repo "$GITHUB_REPO" --body "$SWA_TOKEN"

cat <<EOF

Bootstrap complete.

  Backend:  https://${CONTAINER_APP_FQDN}
  Frontend: https://${STATIC_WEB_APP_HOSTNAME}

Next steps:
  1. Seed the RAG vector store (see src/infra/README.md).
  2. Push to main to trigger the deploy workflows.
EOF

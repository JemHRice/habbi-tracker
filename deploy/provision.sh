#!/usr/bin/env bash
# Provision (or update) the Habbi-Tracker Azure resources.
#
# Idempotent: it is an ARM deployment, so running it again converges the
# resources onto whatever this script and main.bicep describe. Safe to re-run
# after changing a parameter.
#
# Prerequisites: `az login` in this shell, and a Neon connection string.
#
#   DATABASE_URL='postgresql+psycopg://...' ./deploy/provision.sh
#
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-habbi-tracker}"
LOCATION="${LOCATION:-australiaeast}"
SWA_LOCATION="${SWA_LOCATION:-eastasia}"
NAME_PREFIX="${NAME_PREFIX:-habbitracker}"
GITHUB_OWNER="${GITHUB_OWNER:-JemHRice}"
GITHUB_REPO="${GITHUB_REPO:-habbi-tracker}"
API_IMAGE="${API_IMAGE:-ghcr.io/${GITHUB_OWNER}/habbi-tracker-api:latest}"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set. Get the pooled connection string from Neon first." >&2
  echo "See docs/RUNBOOK.md, step 1." >&2
  exit 1
fi

echo "==> Resource group ${RESOURCE_GROUP} in ${LOCATION}"
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --output none

# First pass. CORS is empty because the Static Web App hostname does not exist
# until this deployment creates it; the second pass below fills it in.
echo "==> Deploying infrastructure (this takes a few minutes the first time)"
az deployment group create \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters \
      location="${LOCATION}" \
      staticWebAppLocation="${SWA_LOCATION}" \
      namePrefix="${NAME_PREFIX}" \
      apiImage="${API_IMAGE}" \
      databaseUrl="${DATABASE_URL}" \
  --output none

SWA_HOSTNAME=$(az deployment group show \
  --resource-group "${RESOURCE_GROUP}" \
  --name main \
  --query properties.outputs.staticWebAppHostname.value -o tsv)

# Preview environments are named <app>-<something>.<region>.azurestaticapps.net,
# so they are matched by pattern rather than listed. The pattern is anchored to
# this app's own hostname prefix so it cannot admit somebody else's site.
SWA_PREFIX="${SWA_HOSTNAME%%.*}"
SWA_SUFFIX="${SWA_HOSTNAME#*.}"
CORS_ORIGINS="https://${SWA_HOSTNAME}"
CORS_REGEX="^https://${SWA_PREFIX}-[a-z0-9-]+\\.${SWA_SUFFIX//./\\.}$"

echo "==> Applying CORS for https://${SWA_HOSTNAME} and its previews"
az deployment group create \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters \
      location="${LOCATION}" \
      staticWebAppLocation="${SWA_LOCATION}" \
      namePrefix="${NAME_PREFIX}" \
      apiImage="${API_IMAGE}" \
      databaseUrl="${DATABASE_URL}" \
      corsOrigins="${CORS_ORIGINS}" \
      corsOriginRegex="${CORS_REGEX}" \
  --output none

API_URL=$(az deployment group show \
  --resource-group "${RESOURCE_GROUP}" \
  --name main \
  --query properties.outputs.apiUrl.value -o tsv)

echo
echo "Provisioned."
echo "  API       ${API_URL}"
echo "  Frontend  https://${SWA_HOSTNAME}"
echo
echo "Next: store the deploy secrets in GitHub."
echo "  gh secret set VITE_API_BASE_URL --body '${API_URL}' --repo ${GITHUB_OWNER}/${GITHUB_REPO}"
echo "  gh secret set DATABASE_URL --body '<your neon url>' --repo ${GITHUB_OWNER}/${GITHUB_REPO}"
echo "  az staticwebapp secrets list --name ${NAME_PREFIX}-web --query properties.apiKey -o tsv"
echo "    then: gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --body '<that token>' --repo ${GITHUB_OWNER}/${GITHUB_REPO}"
echo
echo "Then run deploy/github-oidc.sh to let GitHub Actions deploy without a stored password."

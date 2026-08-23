#!/usr/bin/env bash
# Let GitHub Actions deploy to Azure without storing a password.
#
# Creates an Entra app registration, trusts this repository's workflows to
# exchange a GitHub-issued token for an Azure one (OIDC federation), and grants
# it Contributor on the resource group only.
#
# Nothing secret comes out of this: the three values written to GitHub are
# identifiers, not credentials. There is no password to rotate or leak.
#
# Prerequisites: `az login`, `gh auth login`, and provision.sh already run.
#
#   ./deploy/github-oidc.sh
#
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-habbi-tracker}"
GITHUB_OWNER="${GITHUB_OWNER:-JemHRice}"
GITHUB_REPO="${GITHUB_REPO:-habbi-tracker}"
APP_NAME="${APP_NAME:-habbi-tracker-deploy}"
BRANCH="${BRANCH:-main}"

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "==> App registration ${APP_NAME}"
APP_ID=$(az ad app list --display-name "${APP_NAME}" --query "[0].appId" -o tsv)
if [ -z "${APP_ID}" ]; then
  APP_ID=$(az ad app create --display-name "${APP_NAME}" --query appId -o tsv)
fi

if ! az ad sp show --id "${APP_ID}" >/dev/null 2>&1; then
  az ad sp create --id "${APP_ID}" --output none
fi

echo "==> Federated credentials for ${GITHUB_OWNER}/${GITHUB_REPO}"
add_federated_credential() {
  local name="$1" subject="$2"
  if az ad app federated-credential show --id "${APP_ID}" --federated-credential-id "${name}" >/dev/null 2>&1; then
    echo "    ${name} already exists"
    return
  fi
  az ad app federated-credential create \
    --id "${APP_ID}" \
    --parameters "{
      \"name\": \"${name}\",
      \"issuer\": \"https://token.actions.githubusercontent.com\",
      \"subject\": \"${subject}\",
      \"audiences\": [\"api://AzureADTokenExchange\"]
    }" \
    --output none
  echo "    ${name} created"
}

# One per trusted context. Deploys run from main; pull requests get their own
# so preview builds work without widening what main's credential can do.
add_federated_credential "${GITHUB_REPO}-branch-${BRANCH}" \
  "repo:${GITHUB_OWNER}/${GITHUB_REPO}:ref:refs/heads/${BRANCH}"
add_federated_credential "${GITHUB_REPO}-pull-requests" \
  "repo:${GITHUB_OWNER}/${GITHUB_REPO}:pull_request"

echo "==> Granting Contributor on resource group ${RESOURCE_GROUP} only"
az role assignment create \
  --assignee "${APP_ID}" \
  --role Contributor \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  --output none 2>/dev/null || echo "    role assignment already present"

echo "==> Writing identifiers to GitHub repository secrets"
gh secret set AZURE_CLIENT_ID --body "${APP_ID}" --repo "${GITHUB_OWNER}/${GITHUB_REPO}"
gh secret set AZURE_TENANT_ID --body "${TENANT_ID}" --repo "${GITHUB_OWNER}/${GITHUB_REPO}"
gh secret set AZURE_SUBSCRIPTION_ID --body "${SUBSCRIPTION_ID}" --repo "${GITHUB_OWNER}/${GITHUB_REPO}"

echo
echo "Done. GitHub Actions can now deploy to ${RESOURCE_GROUP} with no stored password."

# RUNBOOK — Habbi-Tracker production

Everything needed to stand the app up, keep it running, and move it later.

**Architecture.** The FastAPI backend runs as a container on **Azure Container
Apps**, scaled to zero when idle. The React PWA is served by **Azure Static Web
Apps** on the free tier. Data lives in **Neon** serverless Postgres. Push to
`main` runs the tests and, only if they pass, deploys both halves.

Target cost is **$0/month**: the Static Web Apps Free tier, the Container Apps
monthly free grant, and Neon's free tier.

```
GitHub push → Actions ─┬─ tests ─→ build image → GHCR → Container Apps (API)
                       └─ tests ─→ vite build ──────→ Static Web Apps (PWA)
                                                            │
                                              Neon Postgres ┘
```

---

## 1. First deploy, start to finish

Run the shell scripts from **Git Bash** (they are `bash`, and Git Bash ships
with Git for Windows). Everything is idempotent — re-running converges rather
than duplicating.

### Step 0 — Accounts

1. **Neon** — sign up at [neon.tech](https://neon.tech). Free tier, no card.
2. **Azure** — sign up at [azure.microsoft.com](https://azure.microsoft.com/free/).
   A card is required for identity verification even though everything here sits
   inside free grants. Note your **subscription**.
3. **Azure CLI** — `winget install Microsoft.AzureCLI`, then reopen your terminal.
4. Sign in to both: `az login`, and `gh auth login` if you haven't.

### Step 1 — Neon

Create a project (name it `habbi-tracker`, pick the region nearest you) and a
database. From the dashboard, copy the **pooled** connection string — pooled
matters because a scale-to-zero backend opens and drops connections often.

It will look like:

```
postgresql://user:password@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
```

SQLAlchemy needs its driver named, so change the scheme to
`postgresql+psycopg://`:

```bash
export DATABASE_URL='postgresql+psycopg://user:password@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require'
```

### Step 2 — Azure resources

```bash
bash deploy/provision.sh
```

This creates a resource group, a Log Analytics workspace, the Container Apps
environment, the API container app, and the Static Web App — then re-applies
itself with the CORS origins filled in, because the frontend hostname doesn't
exist until the first pass creates it.

It prints the API and frontend URLs. Keep them.

The Container Apps **environment** is deliberately a separate resource from the
app: it's a shared stage, so any future containerised project of yours can sit
on it at no extra cost.

### Step 3 — Deploy credentials

```bash
bash deploy/github-oidc.sh
```

This registers an Entra application, trusts this repository's workflows to
exchange a GitHub token for an Azure one, grants it Contributor **on the
resource group only**, and writes three identifiers to GitHub secrets. There is
no password anywhere in this flow, so there is nothing to rotate or leak.

Then the two remaining secrets and the deploy variables:

```bash
# The Static Web Apps deployment token (this one IS a credential).
az staticwebapp secrets list --name habbitracker-web \
  --query properties.apiKey -o tsv

gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --body '<that token>'
gh secret set VITE_API_BASE_URL --body 'https://<your-api>.azurecontainerapps.io'

gh variable set AZURE_RESOURCE_GROUP --body 'habbi-tracker'
gh variable set AZURE_CONTAINER_APP  --body 'habbitracker-api'
gh variable set API_BASE_URL         --body 'https://<your-api>.azurecontainerapps.io'
```

### Step 4 — Make the image public

The first backend deploy publishes `ghcr.io/<you>/habbi-tracker-api`. GitHub
creates new packages **private**, and Container Apps has no credential for it,
so make it public once:

GitHub → your profile → Packages → `habbi-tracker-api` → Package settings →
Change visibility → Public.

The image holds no secrets — all configuration arrives as environment variables
— and the source is public anyway, so this exposes nothing new. If you would
rather keep it private, see *Private image* below.

### Step 5 — Deploy

```bash
git push origin main
```

Both workflows run. Tests gate everything: a failing suite blocks the deploy
entirely. The backend job builds the image, pushes it, and rolls out a new
revision; the container's entrypoint applies migrations before it serves.

Watch it with `gh run watch`.

### Step 6 — Seed, exactly once

**Run the seed from your laptop, not from the container.**

The private board in `app/seed/data_local.py` is gitignored *and* excluded from
the image, so a container-side seed would create the generic demo board. Your
machine is the only place your real habits exist.

```bash
DATABASE_URL='<your neon url>' python -m app.seed
```

The seed is guarded: a user whose display name already exists is left completely
alone, so running it twice changes nothing. Deploys never run it.

Verify:

```bash
DATABASE_URL='<your neon url>' python -c "
from sqlalchemy import create_engine, text
import os
c = create_engine(os.environ['DATABASE_URL']).connect()
print('users', c.execute(text('select count(*) from users')).scalar())
print('habits', c.execute(text('select count(*) from habits')).scalar())"
```

### Step 7 — Set real PINs

The seeded PINs come from `SEED_USER_A_PIN` / `SEED_USER_B_PIN` and are marked
**provisional**, so the app will ask each of you to choose your own on first
sign-in (Settings → PIN). Once you both have, those environment variables are no
longer needed anywhere.

### Step 8 — Install on a phone

Open the Static Web Apps URL on the phone.

- **iOS Safari** — Share → Add to Home Screen.
- **Android Chrome** — the install prompt appears, or menu → Install app.

Then run the end-to-end check: pick your user, enter the PIN, tick a habit,
force-close, reopen. The tick should still be there — it's in Neon.

---

## 2. Day-to-day operations

| Task | Command |
|---|---|
| Watch a deploy | `gh run watch` |
| Tail API logs | `az containerapp logs show -n habbitracker-api -g habbi-tracker --follow` |
| Current revisions | `az containerapp revision list -n habbitracker-api -g habbi-tracker -o table` |
| Roll back | `az containerapp update -n habbitracker-api -g habbi-tracker --image ghcr.io/<you>/habbi-tracker-api:<older-sha>` |
| Change a setting | edit `deploy/main.bicep`, re-run `deploy/provision.sh` |
| Rotate the DB URL | `az containerapp secret set -n habbitracker-api -g habbi-tracker --secrets database-url='<new>'` then restart the revision |

**Cold starts.** With `minReplicas: 0` the first request after an idle period
waits a second or two for the container to start, plus migration check time. For
a habit tracker opened once a morning this is the right trade; set
`minReplicas: 1` in `main.bicep` if it ever annoys you, at the cost of leaving
the free grant.

**Migrations** run automatically on every container start, are idempotent, and
are forward-only. Nothing in the deploy path drops or rewrites data.

### Where each secret lives

| Name | Where | What it is |
|---|---|---|
| `DATABASE_URL` | Container Apps secret `database-url` | Neon connection string |
| `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` | GitHub secrets | Identifiers, not credentials — OIDC needs no password |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | GitHub secret | Static Web Apps deployment token |
| `VITE_API_BASE_URL` | GitHub secret | Baked into the frontend build |
| `SEED_USER_A_PIN` / `SEED_USER_B_PIN` | Your machine only, at seed time | Never needed in production |

Nothing sensitive is in the repository or the image.

### Private image

If you'd rather the GHCR package stayed private, create a classic PAT with
`read:packages`, then:

```bash
az containerapp registry set -n habbitracker-api -g habbi-tracker \
  --server ghcr.io --username <you> --password '<pat>'
```

That's one more long-lived credential to remember to rotate, which is why the
default is a public image.

---

## Appendix A — Move runtime secrets to Key Vault

**Documented, not built.** Container Apps secrets are perfectly adequate for one
app with one secret. Key Vault earns its setup when you have several apps
sharing secrets, need audited access, or want automatic rotation.

1. **Provision** a vault and store the value:

   ```bash
   az keyvault create -n habbi-tracker-kv -g habbi-tracker -l australiaeast \
     --enable-rbac-authorization true
   az keyvault secret set --vault-name habbi-tracker-kv \
     --name database-url --value '<neon url>'
   ```

2. **Give the container app an identity:**

   ```bash
   az containerapp identity assign -n habbitracker-api -g habbi-tracker --system-assigned
   PRINCIPAL=$(az containerapp identity show -n habbitracker-api -g habbi-tracker \
     --query principalId -o tsv)
   ```

3. **Grant it read access** — RBAC, scoped to the vault:

   ```bash
   az role assignment create --assignee "$PRINCIPAL" \
     --role "Key Vault Secrets User" \
     --scope "$(az keyvault show -n habbi-tracker-kv --query id -o tsv)"
   ```

4. **Reference the secret** instead of storing its value. In `main.bicep`, swap
   the plain secret for a vault reference:

   ```bicep
   secrets: [
     {
       name: 'database-url'
       keyVaultUrl: 'https://habbi-tracker-kv.vault.azure.net/secrets/database-url'
       identity: 'system'
     }
   ]
   ```

   The `env` block is unchanged — it still uses `secretRef: 'database-url'`, so
   **no application code changes**.

5. Redeploy, confirm `/health`, then delete the old inline secret value.

---

## Appendix B — Move Neon to Azure Database for PostgreSQL

**Documented, not built.** Neon's free tier is real Postgres and costs nothing,
so there is no reason to move today. The trigger would be wanting everything in
one cloud, needing Neon's paid features anyway, or a compliance requirement.

Azure Database for PostgreSQL Flexible Server **B1ms** is roughly $20 AUD/month
with no free tier and no scale-to-zero — the whole reason Neon was chosen.

Both are plain Postgres, so **no application code changes**: same schema, same
migrations, same queries. It is a dump, a restore and a connection string.

1. **Dump** from Neon (off-peak — this is the downtime window):

   ```bash
   pg_dump --no-owner --no-privileges --format=custom \
     --dbname='<neon url>' --file=habbi.dump
   ```

2. **Provision** the server and database:

   ```bash
   az postgres flexible-server create \
     -g habbi-tracker -n habbi-tracker-pg -l australiaeast \
     --tier Burstable --sku-name Standard_B1ms \
     --storage-size 32 --version 16 \
     --public-access 0.0.0.0
   az postgres flexible-server db create \
     -g habbi-tracker -s habbi-tracker-pg -d habit_tracker
   ```

3. **Restore:**

   ```bash
   pg_restore --no-owner --no-privileges \
     --dbname='postgresql://user:pass@habbi-tracker-pg.postgres.database.azure.com/habit_tracker?sslmode=require' \
     habbi.dump
   ```

4. **Swap the connection string** and restart:

   ```bash
   az containerapp secret set -n habbitracker-api -g habbi-tracker \
     --secrets database-url='postgresql+psycopg://...azure.com/habit_tracker?sslmode=require'
   az containerapp revision restart -n habbitracker-api -g habbi-tracker \
     --revision "$(az containerapp revision list -n habbitracker-api -g habbi-tracker \
       --query '[0].name' -o tsv)"
   ```

5. **Verify** `/health`, sign in, tick something, confirm history is intact.
   Keep the Neon project for a week before deleting it.

**Cutover downtime** is however long the dump and restore take — a few minutes
at this data volume. Any tick made between the dump and the swap is lost, so do
it when nobody is using the app.

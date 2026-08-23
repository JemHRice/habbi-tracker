# BUILD PROMPT — Phase 4: Deployment (Azure + Neon + GitHub Actions)

You are a Claude Code agent. Deploy the habit-tracker app — the Phase 1 data model, the
Phase 2 FastAPI backend, and the Phase 3 React + Vite PWA — to production. Phases 1–3
are built and passing. This phase provisions hosting, wires continuous deployment, and
documents the operational runbooks. **Do not change application logic**; if something
doesn't deploy, fix the deployment config, not the app.

Work incrementally and verify each piece is live before moving on. Everything below is a
locked decision from planning — implement it as specified, don't substitute alternatives.

---

## 1. Locked deployment architecture

| Layer | Decision |
|---|---|
| Frontend hosting | **Azure Static Web Apps** (free tier) — serves the Vite PWA build |
| Backend hosting | **Azure Container Apps** — runs the FastAPI Docker container, scale-to-zero |
| Database | **Neon** (serverless Postgres, free tier) |
| CI/CD | **GitHub Actions** — push to `main` → tests run → deploy on pass |
| Secrets (runtime) | **Container Apps secrets** (env-injected); Key Vault documented as a future upgrade |
| Secrets (CI) | **GitHub repository secrets** (Azure deploy credential, Neon URL for migrations) |
| Domain | Ship on the free `*.azurestaticapps.net` HTTPS URL; custom domain deferred |
| Environments | **Single production** + Static Web Apps' free automatic per-PR preview environments |
| Container registry | GitHub Container Registry (free) unless a reason to use Azure Container Registry |

Target cost: effectively **$0/month** (free frontend tier + Container Apps free grant +
Neon free tier).

---

## 2. What to provision

1. **Neon project + database.** Create the Postgres database. Capture the connection
   string (pooled connection recommended for a serverless/scale-to-zero backend). This
   becomes `DATABASE_URL`.
2. **Azure Container Apps environment + app.** Provision the environment (the shared
   "stage" that can host future containerised projects too) and the Container App for the
   FastAPI backend. Configure scale-to-zero (min replicas = 0). Expose the API over HTTPS.
3. **Azure Static Web App.** Provision it to build and serve the Vite PWA. Configure its
   API base URL to point at the Container App's public URL.
4. Wire CORS on the backend to allow the Static Web App's production origin **and** the
   per-PR preview origins.

Provide provisioning as **reproducible scripts** (Azure CLI / Bicep, and Neon via its
CLI or documented console steps) — not click-by-click-only instructions — so the whole
environment can be rebuilt. Keep a `deploy/` directory for these.

---

## 3. Containerisation

- Add a production **Dockerfile** for the FastAPI backend (multi-stage, slim base,
  non-root user, only production dependencies). It must run the same app Phase 2 built.
- The container starts by serving the API (e.g. `uvicorn`/`gunicorn` with uvicorn
  workers), reading all config from environment variables (`DATABASE_URL`, CORS origins,
  any app secrets). No secrets baked into the image.
- Keep the Phase 1 `docker-compose.yml` (local Postgres for dev) intact and separate from
  the production Dockerfile.

---

## 4. Migrations & seed on deploy (get this exactly right)

- **Migrations run on every deploy.** Before or at backend startup, run Alembic
  migrations against the Neon database so the production schema always matches the code.
  This must be idempotent and safe to run repeatedly.
- **Seed runs once, on first provision only.** The seed (User A's full board + User B's
  empty board, plus `dim_date` population) must **not** run on every deploy — that would
  duplicate data. Guard it: run seed only if the database is empty/unseeded (e.g. check a
  marker, or make seed idempotent and explicitly gated behind a one-time command). Document
  the one-time seed step clearly.
- Never destructive: deploys apply forward migrations only. No deploy step ever drops or
  rewrites existing data (consistent with the app's forward-only, non-destructive rules).

---

## 5. CI/CD (GitHub Actions)

Two workflows (or one well-structured pipeline):

1. **Backend:** on push to `main` — install deps, run the pytest suite (Phase 1 + Phase 2),
   and **only on pass** build the Docker image, push it to the registry, and deploy the new
   revision to Container Apps.
2. **Frontend:** on push to `main` — build the Vite PWA and deploy to Static Web Apps.
   Static Web Apps also auto-creates a **preview environment per pull request**; leave that
   enabled.

- Tests gate deployment: a failing test suite blocks the deploy.
- Store all deploy credentials in **GitHub repository secrets** (Azure credential, Neon
  `DATABASE_URL` for the migration step). Nothing sensitive in the repo.
- The frontend build must receive the production API base URL at build time via config,
  not hardcoded.

---

## 6. Runtime config & secrets

- Backend reads `DATABASE_URL`, allowed CORS origins, and any app secrets from **Container
  Apps secrets** injected as env vars. None in code or image.
- Document the exact secret names and where each is set (Container Apps vs GitHub secrets).
- **Appendix A — Key Vault upgrade (document, do not build):** write the steps to move
  runtime secrets to Azure Key Vault later — provision the vault, give the Container App a
  managed identity, grant it read access, and reference secrets from the vault. Explain
  it's the hardening path for when multiple apps or secret rotation justify it.

---

## 7. Runbooks to include (documentation deliverables)

- **First-deploy runbook:** provision Neon → provision Azure → set secrets → deploy →
  run migrations → run the one-time seed → install the PWA on a phone. Start to finish.
- **Appendix B — Neon → Azure Postgres migration:** the documented option to move the
  database to Azure Database for PostgreSQL Flexible Server (B1ms) later. Steps:
  `pg_dump` the Neon database → provision the Azure Flexible Server → `pg_restore`/`psql`
  into it → swap `DATABASE_URL` → redeploy. Note the brief cutover downtime (do it
  off-peak) and that no app code changes (both are plain Postgres).
- **Appendix A — Key Vault upgrade** (from §6).
- Update the main README: the production architecture, the one-command paths, the URL, and
  pointers to all appendices.

---

## 8. Definition of done

- Backend live on Container Apps over HTTPS; scales to zero when idle.
- Frontend live on the free `*.azurestaticapps.net` URL; the PWA installs on a phone from
  that URL.
- End-to-end works in production: pick user → daily PIN → today's board → tick a habit →
  it persists in Neon.
- Push to `main` runs tests and auto-deploys both halves; a failing test blocks deploy.
- Migrations run on deploy; seed ran exactly once; no duplicated data.
- All three runbooks/appendices written; no secrets in the repo or image.

---

## 9. Out of scope (do NOT build this phase)

- Custom domain (documented as optional).
- Azure Key Vault (documented, not built).
- Azure managed Postgres (documented migration path, not built — staying on Neon).
- A standing staging environment (PR previews cover preview-before-merge).
- Notifications, offline sync, warehouse pipeline — all still deferred.
- Any change to application logic or the data model.

Implement only §1–§8. Prefer the simplest configuration that meets the spec, keep the
whole thing rebuildable from scripts, and record any assumption in the README.

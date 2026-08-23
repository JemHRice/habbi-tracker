<#
.SYNOPSIS
    PowerShell equivalent of the Makefile, for Windows without GNU make.

.DESCRIPTION
    Same target names as the Makefile, so the documented commands work in either
    shell. CI and any POSIX shell use the Makefile; this is the Windows door to
    the same actions.

.EXAMPLE
    .\make.ps1 migrate
    .\make.ps1 test
    .\make.ps1 test-postgres
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'install', 'migrate', 'seed', 'test', 'test-postgres',
                 'run', 'db-up', 'db-down', 'db-logs', 'reset', 'clean')]
    [string]$Target = 'help'
)

# Deliberately NOT 'Stop': alembic, pytest and docker all log progress to
# stderr, which PowerShell would otherwise turn into a terminating error even on
# a successful run. Success is decided by exit code, in Invoke-Step below.
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$python = if (Test-Path $venvPython) { $venvPython } else { 'python' }
$postgresUrl = 'postgresql+psycopg://habit:habit@localhost:5433/habit_tracker'

function Invoke-Step {
    param([string]$Description, [scriptblock]$Action)
    Write-Host "==> $Description" -ForegroundColor Cyan
    $global:LASTEXITCODE = 0
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Description failed (exit $LASTEXITCODE)" }
}

try {

switch ($Target) {
    'help' {
        Write-Host 'Targets:'
        Write-Host '  install        Create .venv and install the project with dev extras'
        Write-Host '  migrate        Apply migrations to DATABASE_URL (SQLite by default)'
        Write-Host '  seed           Load User A (full board) and User B (empty board)'
        Write-Host '  test           Run the suite against SQLite'
        Write-Host '  test-postgres  Run the same suite against the docker-compose Postgres'
        Write-Host '  run            Serve the API (/health only in Phase 1)'
        Write-Host '  db-up          Start local Postgres and wait for it'
        Write-Host '  db-down        Stop local Postgres'
        Write-Host '  db-logs        Tail the Postgres logs'
        Write-Host '  reset          Delete the local SQLite DB, then migrate and seed'
        Write-Host '  clean          Remove caches and build artefacts'
    }
    'install' {
        Invoke-Step 'Creating virtualenv' { python -m venv .venv }
        Invoke-Step 'Upgrading pip' { & $venvPython -m pip install --upgrade pip }
        Invoke-Step 'Installing project' { & $venvPython -m pip install -e '.[dev]' }
    }
    'migrate'  { Invoke-Step 'Applying migrations' { & $python -m alembic upgrade head } }
    'seed'     { Invoke-Step 'Seeding boards' { & $python -m app.seed } }
    'test'     { Invoke-Step 'Running tests (SQLite)' { & $python -m pytest } }
    'test-postgres' {
        Invoke-Step 'Starting Postgres' { docker compose up -d --wait }
        $env:TEST_DATABASE_URL = $postgresUrl
        try {
            Invoke-Step 'Running tests (Postgres)' { & $python -m pytest }
        }
        finally {
            Remove-Item Env:\TEST_DATABASE_URL -ErrorAction SilentlyContinue
        }
    }
    'run'      { Invoke-Step 'Serving API' { & $python -m uvicorn app.main:app --reload } }
    'db-up'    { Invoke-Step 'Starting Postgres' { docker compose up -d --wait } }
    'db-down'  { Invoke-Step 'Stopping Postgres' { docker compose down } }
    'db-logs'  { docker compose logs -f postgres }
    'reset' {
        Remove-Item -Force .\habit_tracker.db -ErrorAction SilentlyContinue
        Invoke-Step 'Applying migrations' { & $python -m alembic upgrade head }
        Invoke-Step 'Seeding boards' { & $python -m app.seed }
    }
    'clean' {
        Get-ChildItem -Path $PSScriptRoot -Include '__pycache__', '.pytest_cache', '*.egg-info' `
            -Recurse -Force -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host 'Cleaned.'
    }
}

}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

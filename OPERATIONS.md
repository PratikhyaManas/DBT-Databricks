# OPERATIONS GUIDE

Runbook for setup, deployment, operations, security, and troubleshooting.

## Table of Contents

1. Local Setup
2. Architecture Conventions
3. Deployment Procedures
4. Operations Modules
5. Security Checks
6. Troubleshooting
7. Quick Reference

## Local Setup

### Prerequisites

- Python 3.9+
- Databricks workspace access
- Git repository access
- Optional: Azure DevOps or GitHub Actions access

### Install and Validate

```bash
git clone <repository-url>
cd DBT-Databricks

python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt

cd dbt
dbt debug --profiles-dir .
dbt deps
dbt run
dbt test
```

### Environment Variables

Set required Databricks credentials in `.env`:

```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/warehouse-id
DATABRICKS_TOKEN=your-pat-token

DATABRICKS_HOST_STAGING=https://staging-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH_STAGING=/sql/1.0/warehouses/staging-warehouse-id
DATABRICKS_TOKEN_STAGING=staging-pat-token

DATABRICKS_HOST_PROD=https://prod-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH_PROD=/sql/1.0/warehouses/prod-warehouse-id
DATABRICKS_TOKEN_PROD=prod-pat-token
```

## Architecture Conventions

### Medallion Pattern

- Staging: clean and standardize source data (`stg_`)
- Intermediate: joins and enrichment (`int_`)
- Marts: business tables (`fct_`, `dim_`)

Flow:

```text
raw -> stg_* -> int_* -> fct_*/dim_*
```

### Naming and Materialization

- Use lowercase snake_case for column names
- Primary IDs use `_id` suffix
- Timestamps use `_at` suffix

Recommended materializations:

- `staging`: `view`
- `intermediate`: `view`
- `marts`: `table` or `incremental` for large fact tables

Example:

```yaml
models:
  staging:
    +materialized: view
  intermediate:
    +materialized: view
  marts:
    +materialized: table
```

### Testing Baseline

- Primary keys: `unique` + `not_null`
- Foreign keys: `relationships`
- Custom business logic tests in `dbt/tests/`

## Deployment Procedures

### CI/CD Sources

- Azure DevOps pipeline: `azure-pipelines.yml`
- GitHub Actions workflow: `.github/workflows/dbt-databricks.yml`

CI should run validation, tests, linting, security scans, and docs generation. CD should deploy to staging first, then production with approval.

### Databricks Asset Bundle Deploy

```bash
# Validate
databricks bundle validate --target dev

# Deploy
databricks bundle deploy --target dev
databricks bundle deploy --target staging
databricks bundle deploy --target prod
```

### Scripted Deploy

```bash
python scripts/deploy.py --target dev
python scripts/deploy.py --target staging
python scripts/deploy.py --target prod
```

### Rollback

Preferred rollback:

```bash
git revert <commit-sha>
git push origin main
```

Avoid force push rollback in shared branches unless incident response requires it.

## Operations Modules

### Monitoring (`monitoring/`)

- `telemetry.py`: metrics/events client, health checks, performance tracking
- `monitoring_config.yaml`: alerting and baseline thresholds

Key env vars:

- `APPINSIGHTS_CONNECTION_STRING`
- `DATADOG_API_KEY`

### Governance (`governance/`)

- `data_governance.py`: classification, PII detection, SLA helpers
- `data_classification.yaml`: sensitivity mapping and policy
- `retention_policies.yaml`: retention and archival rules

### Compliance (`compliance/`)

- `audit_logging.py`: immutable audit events and report helpers
- `compliance_frameworks.yaml`: GDPR/CCPA/SOX/HIPAA config

## Security Checks

### Local Security Commands

```bash
# Python SAST
bandit -r scripts/

# SQL and pattern checks
semgrep --config p/databricks dbt/models/

# Secrets scanning
detect-secrets scan --baseline .secrets.baseline

# Dependency vulnerabilities
pip-audit
```

### Makefile Shortcuts

```bash
make security
make security-audit
```

## Troubleshooting

### Connection Failures

Symptoms:

- authorization exception
- workspace connection errors
- HTTP path not found

Checks:

```bash
dbt debug --profiles-dir dbt
databricks workspace list /
databricks sql warehouses list
```

Verify:

- host includes `https://`
- token is active
- SQL warehouse is running
- HTTP path is correct for the target warehouse

### dbt Failures

```bash
cd dbt
dbt parse --profiles-dir .
dbt compile --profiles-dir .
dbt test --select <model_name>
```

Common causes:

- invalid YAML in schema files
- missing source table
- duplicate keys causing uniqueness test failures

### Pipeline Failures

Check:

- required variables and secrets exist and match expected names
- target branch trigger conditions
- environment approval gates

### Bundle Failures

```bash
databricks bundle validate --target dev -v
databricks bundle show --target dev
```

Check for missing variables, invalid references, and resource naming collisions.

## Quick Reference

```bash
make help
make deps
make run
make test
make lint
make docs
make debug
make security-audit

python scripts/deploy.py --target dev
databricks bundle validate --target dev
```

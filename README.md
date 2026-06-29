# DBT Databricks Asset Bundle

Production-ready dbt + Databricks project with dual CI/CD (Azure DevOps and GitHub Actions), security checks, and optional enterprise modules for monitoring, governance, and compliance.

## Quick Start

### 1. Local setup
```bash
git clone <repo-url>
cd DBT-Databricks

python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure credentials
Create `.env` and set at least:
```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/warehouse-id
DATABRICKS_TOKEN=your-pat-token
```

### 3. Validate and run
```bash
cd dbt
dbt debug --profiles-dir .
dbt deps
dbt run
dbt test
```

## Common Commands

```bash
make help
make deps
make run
make test
make lint
make docs
make security
python scripts/deploy.py --target dev
python scripts/deploy.py --target staging
python scripts/deploy.py --target prod
```

## Architecture

- Medallion flow: raw -> staging -> intermediate -> marts
- Multi-environment configs: `dev`, `staging`, `prod`
- Deployment automation: dbt + Databricks Asset Bundles

## CI/CD

- Azure DevOps pipeline: `azure-pipelines.yml`
- GitHub Actions workflow: `.github/workflows/dbt-databricks.yml`

CI includes health checks, dbt validation/tests, linting, security scans, and docs generation. CD deploys to staging and production with approval gates.

## Security and Quality

- Bandit for Python SAST
- Semgrep for SQL/pattern checks
- `pip-audit` for dependency vulnerabilities
- `detect-secrets` for secrets scanning
- dbt tests for data quality

## Project Structure

```text
dbt/                    dbt models, tests, macros, profile, project config
databricks_bundles/     env-specific Databricks Asset Bundle configs
scripts/                deployment and utility scripts
monitoring/             telemetry and monitoring configuration
governance/             data governance policies and logic
compliance/             audit logging and compliance frameworks
```

## Documentation

- `README.md`: overview and quick start
- `OPERATIONS.md`: setup, deployment, CI/CD operations, troubleshooting
- `CHANGELOG.md`: notable updates





# OPERATIONS GUIDE

Complete guide for setup, deployment, architecture, troubleshooting, and best practices.

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Architecture & Design](#architecture--design)
3. [Deployment Procedures](#deployment-procedures)
4. [Monitoring & Observability](#monitoring--observability)
5. [Data Governance](#data-governance)
6. [Compliance & Audit](#compliance--audit)
7. [Security & SAST](#security--sast)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Local Development Setup

### Prerequisites

- Python 3.9 or higher
- Databricks workspace with admin permissions
- Azure DevOps project
- Git repository (Azure Repos or GitHub)

### Installation Steps

#### 1. Clone Repository
```bash
git clone <repository-url>
cd DBT-Databricks
```

#### 2. Create Python Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Set Environment Variables

Create `.env` file (from `.env.example`):
```bash
# Databricks Connection
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_TOKEN=your-personal-access-token

# For multi-environment setup
DATABRICKS_HOST_STAGING=https://staging-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH_STAGING=/sql/1.0/warehouses/staging-warehouse-id
DATABRICKS_TOKEN_STAGING=staging-pat-token

DATABRICKS_HOST_PROD=https://prod-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH_PROD=/sql/1.0/warehouses/prod-warehouse-id
DATABRICKS_TOKEN_PROD=prod-pat-token

# Database Configuration
CATALOG=hive_metastore
DATA_SCHEMA=raw
STAGING_SCHEMA=staging
MARTS_SCHEMA=marts
```

Load environment variables:
```bash
# macOS/Linux
export $(cat .env | xargs)

# Windows PowerShell
Get-Content .env | foreach { $name, $value = $_.split('='); [Environment]::SetEnvironmentVariable($name, $value) }
```

#### 5. Test Databricks Connection
```bash
# Using dbt
cd dbt
dbt debug --profiles-dir .

# Using databricks-cli
databricks workspace list /
```

### Local Development Workflow

#### Running dbt

```bash
cd dbt

# Install dependencies
dbt deps

# Parse project (validate syntax)
dbt parse

# Run all models
dbt run

# Run specific models
dbt run --select stg_customers

# Run by tags
dbt run --select tag:staging

# Run tests
dbt test

# Generate documentation
dbt docs generate
dbt docs serve  # Open http://localhost:8000
```

#### Using Makefile Commands

```bash
make help              # Show all commands
make install           # Install dependencies
make deps              # Install dbt dependencies
make run              # Run all models
make test             # Run tests
make docs             # Generate documentation
make lint             # Run SQL linting
make security         # Run security scanning
make security-audit   # Full security audit
```

#### Database Schema Naming

- **Development**: `dev_analytics`
- **Staging**: `staging_analytics`
- **Production**: `prod_analytics`

Each environment uses its own schema to prevent conflicts.

---

## Architecture & Design

### Medallion Architecture

The project implements the **Medallion Architecture** (Bronze-Silver-Gold):

#### 1. Bronze Layer (Raw)
- **Schema**: `raw_*`
- **Storage**: Delta tables
- **Content**: Unmodified source data
- **Refresh**: Nightly batch exports from source systems

#### 2. Silver Layer (Staging)
- **Schema**: `staging_*`
- **Storage**: Databricks views (lightweight)
- **Content**: Cleaned, deduplicated data
- **Transformations**:
  - Remove nulls & duplicates
  - Standardize formats (dates, strings)
  - Basic data quality checks

#### 3. Gold Layer (Marts)
- **Schema**: `marts_*` or `analytics_*`
- **Storage**: Databricks optimized tables
- **Content**: Business-ready dimensional models
- **Components**:
  - Fact tables (transactions, events)
  - Dimension tables (entities, attributes)
  - Access patterns optimized for queries

### Layer Progression
```
raw_customers (source)
    ↓
stg_customers (clean view)
    ↓
int_customer_orders (join, enrich)
    ├─→ dim_customers (dimension table)
    └─→ fct_customer_orders (fact table)
    
    ↓
BI Tools (Tableau, Power BI, Looker)
```

### Model Naming Conventions

| Layer | Prefix | Example | Type |
|-------|--------|---------|------|
| Raw | (none) | customers | Source table |
| Staging | stg_ | stg_customers | View |
| Intermediate | int_ | int_customer_orders | View |
| Fact marts | fct_ | fct_customer_orders | Table |
| Dimension marts | dim_ | dim_customers | Table |

### Column Naming Standards

- **Lowercase**: All column names lowercase
- **Underscores**: Use underscores for spaces (`customer_id`)
- **IDs**: Foreign keys suffixed: `customer_id`, `order_id`
- **Timestamps**: `created_at`, `updated_at`, `deleted_at`
- **Flags**: Boolean suffixed: `is_active_flag`, `is_deleted`
- **Amounts**: Suffixed `_amount`: `total_amount`, `tax_amount`
- **Counts**: Suffixed `_count`: `order_count`, `line_item_count`
- **Surrogate keys**: Prefixed: `customer_order_key`, `fact_key`

### Materialization Strategy

**Views (Staging & Intermediate)**
- No storage cost, always current data
- Slower queries (computed on-demand)
- Use for: Staging, intermediate, low-cardinality data

**Tables (Marts & Large Datasets)**
- Fast queries, optimized storage
- Storage cost ($), requires refresh
- Use for: Fact tables, dimensions, heavy-join data

**Incremental (Large Fact Tables)**
- Fast updates, reduced compute
- Use for: Fact tables > 1M rows with append-only changes

```yaml
# Example: Materialization in dbt_project.yml
models:
  staging:
    +materialized: view
  intermediate:
    +materialized: view
  marts:
    +materialized: table
```

### Testing Strategy

**Generic/Built-in Tests**
```yaml
columns:
  customer_id:
    tests:
      - unique
      - not_null
  email:
    tests:
      - unique
```

**Relationship Tests**
```yaml
tests:
  - relationships:
      to: source('raw', 'customers')
      field: customer_id
```

**Custom Tests**
```sql
-- tests/test_customer_has_email.sql
SELECT * FROM {{ ref('dim_customers') }}
WHERE email IS NULL OR email = ''
-- Fails if returns rows
```

**Run Tests**
```bash
dbt test                              # All tests
dbt test --select dim_customers       # Specific model
dbt test --select tag:critical        # By tag
```

### Environment Configuration

Define per-environment settings in `dbt/profiles.yml`:

```yaml
databricks_prod:
  outputs:
    dev:
      schema: dev_analytics
      threads: 4
    staging:
      schema: staging_analytics
      threads: 4
    prod:
      schema: prod_analytics
      threads: 8  # More parallelism in prod
```

Override variables in `dbt_project.yml`:
```yaml
vars:
  environment: '{{ target.name }}'
  catalog: 'hive_metastore'
  data_schema: raw
```

---

## Deployment Procedures

### Setting Up Azure DevOps Pipelines

#### 1. Create Variable Groups

In Azure DevOps: Pipelines → Library → Variable groups

Create `databricks-dev`:
```
DATABRICKS_HOST          = https://your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH     = /sql/1.0/warehouses/warehouse-id
DATABRICKS_TOKEN         = (mark as secret)
```

Create separate groups: `databricks-staging`, `databricks-prod` with respective credentials.

#### 2. Create Environments

Pipelines → Environments:
- `staging` (auto-deploy, no approval)
- `production` (requires approval)

#### 3. Link Variable Groups to Pipelines

In pipeline YAML:
```yaml
resources:
  repositories:
    - repository: self
      trigger: true
variables:
  - group: databricks-dev  # Link variable group
```

### Deploying with Databricks Asset Bundle

#### 1. Initialize Bundle
```bash
databricks bundle init -t basic
```

#### 2. Configure Bundle

Edit `databricks.yml` for each environment:

```yaml
targets:
  dev:
    mode: development
    variables:
      environment: dev
      num_workers: 1

  staging:
    variables:
      environment: staging
      num_workers: 2

  prod:
    mode: production
    variables:
      environment: prod
      num_workers: 4
```

#### 3. Deploy Bundle

```bash
# Validate configuration
databricks bundle validate --target dev

# Deploy to dev
databricks bundle deploy --target dev

# Deploy to staging
databricks bundle deploy --target staging

# Deploy to production
databricks bundle deploy --target prod
```

### Automated Deployment Script

Use `python scripts/deploy.py` for unified multi-environment deployment:

```bash
# Deploy to dev
python scripts/deploy.py --target dev

# Deploy to staging with specific models
python scripts/deploy.py --target staging --dbt-select "tag:marts"

# Deploy to production (skip bundle)
python scripts/deploy.py --target prod --skip-bundle

# Deploy with options
python scripts/deploy.py --target staging \
  --dbt-select "tag:facts" \
  --skip-tests \
  --bundle-path databricks_bundles/staging
```

### CI/CD Pipeline Configuration

**Pipeline File**: `azure-pipelines.yml` (consolidated CI/CD)

The repository uses a single, consolidated Azure DevOps pipeline that handles both CI and CD:

**CI Stages** (run on all branches & pull requests):
- **HealthCheck**: Verify Databricks connectivity and warehouse availability
- **Setup**: Install dependencies
- **Validate**: Validate dbt project syntax
- **Test**: Run dbt tests and data quality checks
- **Security**: Run SAST scanning (Bandit, Semgrep, pip-audit, detect-secrets)
- **Lint**: Run SQL linting (sqlfluff)
- **Documentation**: Generate dbt documentation

**CD Stages** (run on main branch only, after successful CI):
- **DeployStaging**: Deploy to staging environment (automatic)
  - Install dependencies
  - Run dbt models against staging schema
  - Run data quality tests
  - Deploy Databricks Asset Bundle
- **ApprovalForProd**: Manual approval gate (24-hour timeout)
  - Notifies data engineering team
  - Requires manual approval to proceed
- **DeployProduction**: Deploy to production (manual trigger)
  - Install dependencies
  - Run dbt models against production schema
  - Run production data quality tests
  - Deploy production Databricks Asset Bundle

**Trigger Rules**:
```yaml
trigger:
  branches:
    include:
      - main
      - develop
      - feature/*

pr:
  branches:
    include:
      - main
      - develop
```

- **Pull Requests**: CI stages run automatically on PRs to `main` and `develop`
- **Feature Branches**: CI stages run on all commits to `feature/*` branches
- **Main Branch**: All CI stages plus all CD stages (staging → approval → production)
- **Develop Branch**: CI stages only (no deployment)

### CI/CD Pipeline Stages

**CI Pipeline** (runs on Pull Request):
1. Health check (Databricks connectivity & warehouse validation)
2. Setup environment
3. Validate dbt config (`dbt debug`)
4. Run dbt tests (modified models using "slim CI")
5. Security scanning (SAST - Bandit, Semgrep, etc.)
6. SQL linting (sqlfluff)
7. Documentation generation

**CD Pipeline** (runs on merge to main):
1. **Staging Deployment** (automatic):
   - Install dependencies
   - Run dbt models against staging schema
   - Run data quality tests
   - Deploy Databricks Bundle

2. **Manual Approval**: Data team reviews staging results

3. **Production Deployment** (triggered after approval):
   - Install dependencies
   - Run dbt in production schema
   - Run production tests
   - Deploy production bundle

### Production Deployment Workflow

```
1. Create Pull Request on feature branch
   ↓
2. CI Pipeline runs automatically
   - Health checks ✅
   - Tests ✅
   - Security scanning ✅
   ↓
3. Code review & approval (by team)
   ↓
4. Merge PR to main
   ↓
5. Automatic staging deployment
   - dbt runs against staging_analytics schema
   - All tests execute
   - DAB resources created/updated
   ↓
6. Manual approval (required)
   - Data team reviews staging results
   - Validates data quality
   ↓
4. Production deployment (manual trigger)
   - dbt runs against prod_analytics schema
   - Final validation tests
   - DAB deploys to production
```

### Rollback Procedures

If deployment fails or needs to be rolled back:

```bash
# Option 1: Revert commit (automatic rollback via pipeline)
git revert <commit-sha>
git push origin main

# Option 2: Manual revert to previous version
git reset --hard <previous-commit>
git push origin main --force

# Option 3: Redeploy specific environment
python scripts/deploy.py --target prod --full-refresh
```

---

## Monitoring & Observability

The project includes enterprise-grade monitoring and observability features through the `monitoring/telemetry.py` module.

### Features

- **Central Telemetry Client**: Single hub for all metrics, events, and logging
- **Dual-Backend Support**: Azure Application Insights and Datadog integration
- **Health Checks**: Automatic validation of Databricks connectivity, warehouse status, schema existence
- **Performance Monitoring**: Track dbt model execution, test execution, and pipeline metrics
- **Structured JSON Logging**: Machine-readable event logs for compliance and analysis
- **Alert Triggers**: Automatic alerts for slow models (60+ seconds), connection failures, and schema issues

### Configuration

Edit `monitoring/monitoring_config.yaml` to customize:

```yaml
# Application Insights (Azure)
application_insights:
  enabled: true
  connection_string: "${APPINSIGHTS_CONNECTION_STRING}"

# Datadog
datadog:
  enabled: true
  api_key: "${DATADOG_API_KEY}"

# Health checks
health_checks:
  databricks:
    enabled: true
    check_frequency_seconds: 300
  warehouse:
    enabled: true
    warehouse_ids: ["${WAREHOUSE_ID_PROD}"]

# Performance baselines
performance_monitoring:
  dbt_models:
    slow_model_threshold_seconds: 60
    alert_on_slow_models: true
```

### Usage Examples

#### Initialize Telemetry in Python Scripts

```python
from monitoring.telemetry import initialize_telemetry, get_telemetry_client

# Initialize on script start
initialize_telemetry("my-script-name")

# Get client (singleton)
telemetry = get_telemetry_client()

# Record metrics
telemetry.record_metric(
    name="model.execution.duration",
    value=45.2,
    properties={"model": "dim_customers", "target": "prod"}
)

# Record events
telemetry.record_event(
    name="pipeline_completed",
    properties={
        "pipeline": "daily_refresh",
        "models_run": 5,
        "tests_passed": 12
    }
)
```

#### Health Checks

```python
from monitoring.telemetry import get_health_check

health_check = get_health_check()

# Check Databricks connectivity
if health_check.check_databricks_connection():
    print("✅ Databricks is reachable")
else:
    print("❌ Connection failed")

# Validate schema
if health_check.validate_schema("prod"):
    print("✅ Schema exists and is accessible")
else:
    print("❌ Schema validation failed")
```

#### Performance Monitoring

```python
from monitoring.telemetry import PerformanceMonitor

monitor = PerformanceMonitor()

# Record model execution
monitor.record_model_run(
    model_name="fct_customer_orders",
    duration_seconds=45.2,
    status="success",
    rows_affected=1500
)

# Record pipeline execution
monitor.record_pipeline_execution(
    pipeline_name="daily_refresh",
    stage="dbt_run",
    status="success",
    duration_seconds=120
)
```

### Environment Variables

Set these environment variables for telemetry:

```bash
# Azure Application Insights
APPINSIGHTS_CONNECTION_STRING=InstrumentationKey=<key>;IngestionEndpoint=https://<region>.in.applicationinsights.azure.com/

# Datadog
DATADOG_API_KEY=<your-datadog-api-key>

# Databricks Health Check
DATABRICKS_HOST=https://<workspace-id>.databricks.com
DATABRICKS_TOKEN=<your-token>
WAREHOUSE_ID_PROD=<warehouse-id>
```

### Viewing Metrics

**In Azure Application Insights**:
```
Home > Application Insights > <your-app> > Metrics
```

Look for custom metrics:
- `dbt.run.duration_seconds`
- `dbt.test.duration_seconds`
- `deployment.bundle.duration_seconds`
- `deployment.total.duration_seconds`

**In Datadog**:
```
Metrics > Metrics Explorer
Search: dbt.databricks.*
```

---

## Data Governance

The project includes comprehensive data governance through the `governance/data_governance.py` module.

### Features

- **Data Classification**: 4 sensitivity levels (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED)
- **PII Detection**: Automated detection of 7 PII types (email, phone, SSN, credit card, address, DOB, account)
- **Data Quality SLAs**: Track and enforce completeness, freshness, and test passage targets
- **Governance Registry**: Central registry of data policies per table/dataset
- **Sensitive Data Tracking**: Automatically flag and protect restricted data

### Configuration

Edit `governance/data_classification.yaml` to define:

```yaml
data_classification:
  customer_tables:
    - table_name: "*.customers"
      sensitivity: "RESTRICTED"
      pii_types: [email, phone, address, date_of_birth]
      retention_days: 2555  # 7 years
      encryption_required: true
      compliance_frameworks: [GDPR, CCPA]

# Access control by role
access_control:
  roles:
    analyst:
      permissions: [read, write]
      can_access: [CONFIDENTIAL, INTERNAL, PUBLIC]
      cannot_access: [customer_pii]
```

### Usage Examples

#### Data Classification Policy

```python
from governance.data_governance import get_governance_registry, DataClassification

registry = get_governance_registry()

# Get policy for a table
policy = registry.get_policy("customers")
print(f"Classification: {policy.classification}")  # RESTRICTED
print(f"Retention: {policy.retention_days} days")  # 2555
print(f"Encryption Required: {policy.encryption_required}")  # True
```

#### PII Detection

```python
from governance.data_governance import PIIDetector, PIIType

detector = PIIDetector()

# Detect PII in text
email = "john.doe@company.com"
if detector.detect_pii(email, PIIType.EMAIL):
    print(f"⚠️  Email detected: {email}")

# Scan DataFrame column
import pandas as pd
df = pd.read_csv("customer_data.csv")

for pii_type in PIIType:
    matches = detector.find_pii_in_column(df["email"], pii_type)
    if matches:
        print(f"Found {len(matches)} {pii_type} values")
```

#### Data Quality SLAs

```python
from governance.data_governance import get_quality_framework, DataQualitySLA

framework = get_quality_framework()

# Get SLA for data freshness
sla = framework.get_sla("data_freshness")
print(f"Target: {sla.target_percentage}%")
print(f"Check Frequency: {sla.check_frequency_hours} hours")

# Record SLA breach
breach = SLABreach(
    sla_id="order_freshness",
    actual_value=89.5,
    target_value=98.0,
    timestamp=datetime.now()
)
framework.record_breach(breach)
```

### Data Retention

Data retention policies are defined in `governance/retention_policies.yaml`:

```yaml
classification_based_retention:
  RESTRICTED:
    default_years: 7
    tables:
      - pattern: "*.customers"
        retention_years: 7
        right_to_be_forgotten: true
        anonymize_before_deletion: true

  CONFIDENTIAL:
    default_years: 3

  PUBLIC:
    default_years: 0  # No limit
```

---

## Compliance & Audit

The project includes comprehensive compliance and audit logging through the `compliance/audit_logging.py` module.

### Supported Frameworks

- **GDPR** (EU): Data protection, right to be forgotten, data portability
- **CCPA** (California): Consumer privacy, deletion requests, opt-out
- **SOX** (US): Financial data integrity, audit trails, change management
- **HIPAA** (US): Health data protection, PHI access controls

### Features

- **Immutable Audit Logs**: SHA-256 signed entries with integrity verification
- **Event Tracking**: 10+ event types (access, modification, deletion, pipeline execution, security events)
- **Compliance Reports**: Auto-generate framework-specific reports
- **Retention Policies**: Automatic data deletion/archival with audit trail preservation
- **Breach Incident Response**: Structured incident tracking and response workflow

### Configuration

Edit `compliance/compliance_frameworks.yaml`:

```yaml
compliance_frameworks:
  GDPR:
    enabled: true
    requirements:
      - name: "Right to be Forgotten (Article 17)"
        max_days_to_comply: 30
        enforcement: required

  CCPA:
    enabled: true
    requirements:
      - name: "Deletion Request"
        max_days_to_comply: 45

  SOX:
    enabled: true
    requirements:
      - name: "Audit Trail (Section 802)"
        retention_years: 6

  HIPAA:
    enabled: true
    requirements:
      - name: "PHI Confidentiality"
        encryption_required: true
```

### Usage Examples

#### Log Data Access

```python
from compliance.audit_logging import get_audit_logger

audit = get_audit_logger()

# Log data access
audit.log_data_access(
    user_id="analyst@company.com",
    resource="customers",
    resource_type="table",
    action="read",
    record_count=1000
)
```

#### Log Data Modification

```python
audit.log_data_modification(
    user_id="dbt@company.com",
    resource="dim_customers",
    action="insert",
    record_count=500,
    details={"source": "stg_customers", "transformation": "dbt_run"}
)
```

#### Log Pipeline Execution

```python
audit.log_pipeline_execution(
    pipeline_name="daily_refresh",
    environment="prod",
    status="success",
    details={
        "models_run": 5,
        "tests_passed": 12,
        "duration_seconds": 180
    }
)
```

#### Generate Compliance Reports

```python
from compliance.audit_logging import ComplianceFramework

audit = get_audit_logger()

# Generate GDPR report
gdpr_report = audit.generate_gdpr_report(
    start_date="2026-01-01",
    end_date="2026-03-31"
)
print(f"Data Processing Activities: {len(gdpr_report['data_processing_activities'])}")
print(f"Deletion Requests: {len(gdpr_report['deletion_requests'])}")

# Generate SOX report
sox_report = audit.generate_sox_report(
    start_date="2025-01-01",
    end_date="2026-03-31"
)
print(f"Financial Data Accesses: {len(sox_report['financial_access_logs'])}")
print(f"System Changes: {len(sox_report['change_logs'])}")
```

### Audit Log Locations

Audit logs are stored in:
- **File-based**: `dbfs:/logs/audit/` (JSON format)
- **Application Insights**: Custom events with `audit_event` type
- **Datadog**: Logs with `source:audit` tag

View audit logs:

```bash
# Local file inspection
ls -la dbfs:/logs/audit/

# Query in Databricks notebook
%sql
SELECT * FROM delta.`dbfs:/logs/audit/`
WHERE timestamp > CURRENT_DATE() - INTERVAL 7 DAY
ORDER BY timestamp DESC
LIMIT 100
```

### Incident Response

When a data breach or security incident is detected:

1. **Log Immediately**: Create incident record with auto-timestamping
2. **Assess Scope**: Determine affected data classifications, users, systems
3. **Notify**: Alert compliance, security, and legal teams
4. **Remediate**: Execute incident response plan
5. **Document**: Record all actions and evidence for audit trail

```python
from compliance.audit_logging import IncidentResponse

incident = IncidentResponse(
    incident_type="unauthorized_access",
    severity="CRITICAL",
    affected_data="customer_data",
    details={
        "detected_at": "2026-03-15T14:30:00Z",
        "affected_users": 150,
        "scope": "email addresses exposed"
    }
)
audit.log_security_event(
    event_type="security_incident",
    details=incident.to_dict()
)
```

---

## Security & SAST

### Static Application Security Testing (SAST)

The project includes comprehensive security scanning through multiple tools.
````

### Python Security (Bandit)

Detects hardcoded secrets, insecure functions, and dangerous patterns.

**Configuration**: `.security/bandit.yaml`

**Run Locally**:
```bash
# Scan all Python scripts
bandit -r scripts/

# Scan with configuration
bandit -c .security/bandit.yaml -r scripts/

# Generate JSON report
bandit -r scripts/ -f json -o bandit-report.json
```

**In Pipeline**:
```yaml
- script: |
    bandit -r scripts/ -f json -o $(Build.ArtifactStagingDirectory)/bandit.json
  displayName: 'Python Security Scan'
  continueOnError: true
```

**Fix Common Issues**:
- Don't hardcode secrets: use environment variables
- Avoid `eval()`, `exec()`, `pickle`
- Use `parameterized` queries instead of string formatting
- Use secure hash functions (not MD5/SHA1)

### SQL Security (Semgrep)

Detects SQL injection risks, insecure patterns, and dbt anti-patterns.

**Configuration**: `.security/semgrep.yml`

**Run Locally**:
```bash
# Scan with Databricks rules
semgrep --config p/databricks dbt/models/

# Scan with custom rules
semgrep --config .security/semgrep.yml dbt/models/

# Generate JSON report
semgrep --config p/databricks dbt/models/ -o semgrep-report.json --json
```

**In Pipeline**:
```yaml
- script: |
    semgrep --config p/databricks dbt/models/ \
      -o $(Build.ArtifactStagingDirectory)/semgrep.json --json
  displayName: 'SQL/dbt Security Scan'
  continueOnError: true
```

**Prevent Common SQL Issues**:
- Use `ref()` and `source()` instead of hardcoded table names
- Avoid dynamic SQL without parameterization
- Sanitize user inputs in macros
- Don't store secrets in model definitions

### Secrets Detection (Detect-Secrets)

Prevents accidental credential commits.

**Run Locally**:
```bash
# Scan repository
detect-secrets scan

# Create baseline
detect-secrets scan > .secrets.baseline

# Validate against baseline
detect-secrets audit .secrets.baseline
```

**In Pipeline**:
```yaml
- script: |
    detect-secrets scan --baseline .secrets.baseline
  displayName: 'Detect Secrets'
  failOnStderr: true
```

**Prevention**:
- Use `.env` files (add to `.gitignore`)
- Store secrets in Azure DevOps or deployment tools
- Never commit credentials, tokens, or keys
- Rotate secrets regularly

### Dependency Vulnerability Scanning (pip-audit)

Checks for vulnerable Python packages.

**Run Locally**:
```bash
# Audit requirements.txt
pip-audit

# Generate report
pip-audit --desc --output json > pip-audit.json
```

**In Pipeline**:
```yaml
- script: |
    pip-audit --desc
  displayName: 'Dependency Vulnerability Scan'
  continueOnError: true
```

**Response Process**:
1. Run `pip-audit` to identify packages
2. Update vulnerable packages: `pip install --upgrade package-name`
3. Update `requirements.txt`
4. Test thoroughly
5. Commit and create PR

### Security Scanning Makefile Command

```bash
# Run all security checks
make security-audit

# Run individual checks
make bandit            # Python security
make semgrep           # SQL/dbt security
make detect-secrets    # Secrets detection
make pip-audit         # Dependency vulnerabilities
```

### CI/CD Security Integration

**In Pipeline YAML**:
```yaml
- stage: Security
  displayName: 'Security Scanning'
  dependsOn: []  # Run in parallel
  jobs:
    - job: SAST
      displayName: 'Run SAST Checks'
      steps:
        - script: bandit -r scripts/ -f json -o bandit.json
        - script: semgrep --config p/databricks dbt/models/ -o semgrep.json --json
        - script: pip-audit --output json > pip-audit.json
        - script: detect-secrets scan --baseline .secrets.baseline
        
        - task: PublishBuildArtifacts@1
          inputs:
            PathtoPublish: '.'
            ArtifactName: 'security-reports'
```

### Security Policy

- **High**: Fix immediately, block deployment
- **Medium**: Fix before next release
- **Low**: Fix when convenient
- **False Positives**: Suppress with tool-specific configs

---

## Troubleshooting

### Connection Issues

#### Problem: "Authorization exception"
```
Error: Authorization exception - insufficient permissions
```

**Causes**: Invalid token, expired token, insufficient workspace permissions

**Solutions**:
```bash
# Check token validity
databricks workspace list /

# Verify environment variables
echo $DATABRICKS_TOKEN
echo $DATABRICKS_HOST

# Generate new token:
# 1. Go to Databricks Settings → User → Developer
# 2. Click "Generate new token"
# 3. Copy token to .env or Azure DevOps secret
```

#### Problem: "Cannot connect to Databricks workspace"
```
Error: Failed to connect to Databricks workspace
```

**Check Host Format**:
```bash
# ❌ WRONG
DATABRICKS_HOST=my-workspace.databricks.com

# ✅ CORRECT
DATABRICKS_HOST=https://my-workspace.cloud.databricks.com
```

**Test Connection**:
```bash
curl -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  https://your-workspace.cloud.databricks.com/api/2.0/workspace/list \
  -d '{"path":"/"}'
```

#### Problem: "HTTP path not found"
```
Error: The provided HTTP path does not exist or is not enabled
```

**Solutions**:
```bash
# List warehouses
databricks sql warehouses list

# Get HTTP path from output:
# Format: /sql/1.0/warehouses/{warehouse-id}

# Turn on warehouse if off
databricks sql warehouses start {warehouse-id}
```

### dbt Issues

#### Problem: "Schema file is not valid"
```
Error: Invalid schema.yml format
```

**Validate YAML**:
```bash
cd dbt
dbt parse --show-resource-specification

# Check for:
# - Inconsistent indentation (use spaces, not tabs)
# - Missing colons after keys
# - Extra spaces in quotes
```

#### Problem: "Source not found"
```
Error: Source 'raw.customers' not found
```

**Check**:
```bash
# Verify table exists
databricks sql execute --query "SELECT * FROM raw.customers LIMIT 1"

# Verify source definition in schema.yml
grep -A 5 "raw:" dbt/models/schema.yml

# Load test data if missing
python scripts/test_data_load.py
```

#### Problem: "Unique constraint violation"
```
Test failed: unique constraint violated in 'dim_customers'
```

**Find Duplicates**:
```sql
SELECT customer_id, COUNT(*)
FROM raw.customers
GROUP BY customer_id
HAVING COUNT(*) > 1;

-- Remove duplicates in staging model:
SELECT DISTINCT * FROM raw.customers
```

### Pipeline Issues

#### Problem: "Pipeline fails on variable substitution"
```
Error: Variable 'DATABRICKS_HOST' is not set
```

**Fix**:
1. Go to Pipelines → Library → Variable groups
2. Verify variable names match pipeline (case-sensitive)
3. Ensure group is linked to pipeline
4. Check syntax: `$(VARNAME)` in YAML

#### Problem: "Pipeline times out"
```
Error: Job timed out after 3600 seconds
```

**Increase Timeout**:
```yaml
- task: PythonScript@0
  timeoutInMinutes: 120  # Increase from default 60
```

#### Problem: "pip install fails"
```
Error: Failed to install packages
```

**Solutions**:
```bash
# Clear cache and reinstall
pip install --cache-dir /tmp/pip-cache -r requirements.txt

# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Check requirements.txt syntax
pip check requirements.txt
```

### Bundle Issues

#### Problem: "Bundle validation fails"
```
Error: Validation failed: resource XXX has invalid configuration
```

**Debug**:
```bash
# Validate bundle
databricks bundle validate --target dev -v

# View configuration
databricks bundle show --target dev

# Check for:
# - Invalid variable references: ${var.xxx}
# - Missing required fields
# - Type mismatches
```

#### Problem: "Resource already exists"
```
Error: Resource 'dbt-run-job' already exists
```

**Solutions**:
```bash
# Check existing resources
databricks jobs list --name-regex "dbt-run"

# Delete old resource
databricks jobs delete --job-id <id>

# Or use unique names per environment:
# ✅ dbt-run-dev, dbt-run-staging, dbt-run-prod
```

#### Problem: "Cluster failed to start"
```
Error: Cluster instance not available
```

**Solutions**:
- Check instance type availability in region
- Reduce cluster size (fewer workers)
- Try different node type
- Check AWS/Azure quota

### Security Scanning Issues

#### Problem: "Bandit reports secrets"
```
Issue: Hardcoded password found in scripts/deploy.py
```

**Fix**:
```python
# ❌ WRONG
password = "mypassword123"

# ✅ CORRECT
password = os.getenv("DATABASE_PASSWORD")
```

#### Problem: "Semgrep detects SQL injection risk"
```
Issue: Potential SQL injection in dbt model
```

**Fix**:
```sql
-- ❌ WRONG
SELECT * FROM customers WHERE id = {{ customer_id }}

-- ✅ CORRECT (dbt handles parameterization)
SELECT * FROM {{ source('raw', 'customers') }}
WHERE id = {{ customer_id }}
```

#### Problem: "detect-secrets finds credentials"
```
Issue: AWS_ACCESS_KEY found in .env file
```

**Fix**:
```bash
# Add to .gitignore
echo ".env" >> .gitignore

# Remove from git history
git rm --cached .env
git commit -m "Remove sensitive file"
```

### Performance Issues

#### dbt run is slow
```bash
# Profile the run
dbt run --explain

# Optimize:
# 1. Use views for staging (lighter weight)
# 2. Use incremental models for large fact tables
# 3. Add indexes to join columns
# 4. Check Databricks query history for slow SQL
```

#### Cluster is unresponsive
```bash
# Check cluster logs
databricks clusters events list --cluster-id <id>

# Increase workers
# Edit databricks_bundles/prod/databricks.yml:
num_workers: 8  # Increase from 4

# Redeploy
databricks bundle deploy --target prod
```

### Debugging Techniques

**Enable dbt Debug Mode**:
```bash
dbt run --debug --select <model>
# Output: dbt/logs/dbt.log
```

**Check Compiled SQL**:
```bash
cat dbt/target/compiled/project/models/marts/dim_customers.sql
```

**Review dbt Artifacts**:
```bash
# Model dependencies
cat dbt/target/manifest.json | jq '.nodes' | head

# Run results
cat dbt/target/run_results.json | jq '.results'
```

**Verbose Logging**:
```bash
dbt run -vv --debug
databricks_client = WorkspaceClient(logging_level='DEBUG')
```

---

## Best Practices

### Version Control & Branching

**Strategy**:
- `main`: Production-ready code, auto-deploys to staging
- `develop`: Integration branch for features (optional)
- `feature/*`: Individual feature branches

**Workflow**:
```bash
# Create feature branch
git checkout -b feature/customer-fact-table

# Make changes
# ... edit models, tests, etc ...

# Test locally
make test
make security

# Commit
git add .
git commit -m "Add customer fact table with tests"

# Push and create PR
git push origin feature/customer-fact-table
```

### Code Review Process

1. Create pull request
2. CI pipeline validates (auto)
3. Team reviews code
4. At least 1 approval required
5. Merge to main
6. CD pipeline auto-deploys

### Documentation Standards

**Model Documentation**:
```yaml
models:
  - name: dim_customers
    description: Customer dimension table
    columns:
      - name: customer_id
        description: Unique customer identifier
        tests:
          - unique
          - not_null
```

**Comment Complex Logic**:
```sql
-- Generate fact records for each order with calculated metrics
{{ config(materialized='table') }}

SELECT
    -- Customer and order identifiers
    {{ dbt_utils.generate_surrogate_key(['customer_id', 'order_id']) }} as customer_order_key,
    customer_id,
    order_id,
    
    -- Metrics
    total_amount,
    ...
```

### Testing Requirements

**Mandatory Tests**:
- Primary keys: `unique` + `not_null`
- Foreign keys: `relationships` test
- Critical columns: Data type validation

**Optional Tests**:
- Accepted values (enums/categories)
- Freshness checks (for source data)
- Row count thresholds
- Custom business logic

**Test Coverage Goal**: 80%+ of columns have at least one test

### Model Materialization Guidelines

| Scenario | Materialization | Reason |
|----------|-----------------|--------|
| Source layer (raw) | External | Source system |
| Staging (clean) | View | Lightweight, always current |
| Intermediate (join) | View | Temporary, support main models |
| Fact tables > 1M rows | Incremental | Faster updates |
| Fact tables < 1M rows | Table | Simpler, fast queries |
| Dimension tables | Table | Reference data, stable |
| Reference/lookup | Seed (CSV) | Static, version controlled |

### Performance Optimization

**Indexing (Databricks)**:
```sql
CREATE DATABRICKS INDEX idx_customer_id 
ON dim_customers(customer_id);
```

**Partitioning (for large tables)**:
```yaml
{{ config(
    materialized='table',
    partition_by=['month'],
    cluster_by=['customer_id']
) }}
```

**Incremental Models** (for fact tables):
```sql
{{ config(
    materialized='incremental',
    unique_key='order_id'
) }}

SELECT *
FROM source
{% if execute %}
    WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

**Statistics**:
```sql
-- Add post-hook to refresh stats
ANALYZE TABLE {{ this }} COMPUTE STATISTICS;
```

### Monitoring & Observability

**Check Model Performance**:
- Databricks Job UI: Track run duration
- dbt profiles: Run times per model
- dbt docs: Lineage and dependencies

**Set Alerts**:
- Pipeline failures (Azure DevOps)
- Test failures (PR comments)
- Long-running models (> 2x average)

**Health Checks**:
```bash
# Run regularly
make debug              # Connection test
dbt parse              # Syntax validation
dbt compile            # Full compilation
```

### Security Best Practices

1. **Never commit secrets**:
   - Use `.env` files (add to `.gitignore`)
   - Store credentials in deployment tools
   - Use environment variables in pipelines

2. **Principle of Least Privilege**:
   - Service accounts with minimal permissions
   - Separate credentials per environment
   - Rotate tokens frequently

3. **Code Review Security**:
   - Review for hardcoded secrets
   - Check SQL injection risks
   - Validate dependency versions

4. **Audit & Monitoring**:
   - Enable Databricks audit logs
   - Monitor failed authentication attempts
   - Review job history regularly

5. **Data Governance**:
   - Document data sensitivity levels
   - Implement row-level security where needed
   - Mask PII in non-prod environments

### Team Communication

**Document Changes**:
- PR descriptions: What & why
- Commit messages: Clear, concise
- Model docs: Update `schema.yml`

**Slack/Email Updates**:
- Deployment notifications
- Pipeline failures
- Breaking changes

**Runbooks**:
- Common troubleshooting steps
- Emergency contact info
- Incident response procedures

---

## Quick Reference

### Common Commands
```bash
make help                              # Show all commands
make setup && make install             # Initial setup
make deps && make run                  # Run models
make test && make security             # Test & scan
make docs                              # Generate docs

python scripts/deploy.py --target dev  # Deploy to dev
```

### Environment Setup
```bash
cp .env.example .env
# Edit .env with credentials
export $(cat .env | xargs)
```

### Validate Locally
```bash
dbt debug --profiles-dir dbt     # Connection
dbt parse --profiles-dir dbt     # Syntax
dbt run --select tag:staging     # Run subset
dbt test                         # Test data
bandit -r scripts/               # Security
```

### Troubleshooting
```bash
make debug                        # Connection test
dbt logs --tail                  # View latest logs
dbt docs serve                   # View lineage
databricks bundle validate       # Bundle check
```

---

**Last Updated**: Feb 15, 2026 | **Version**: 1.0

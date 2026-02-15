# DBT Databricks Asset Bundle with Azure DevOps & GitHub Actions CI/CD

Production-ready dbt + Databricks Asset Bundle with dual CI/CD support (Azure DevOps & GitHub Actions), enterprise monitoring, data governance, compliance, and automated security scanning.

## 🚀 Quick Start

### Local Setup (5 minutes)
```bash
# Clone & setup
git clone <repo-url> && cd DBT-Databricks
python -m venv venv && source venv/bin/activate  # or: venv\Scripts\activate on Windows
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Databricks credentials

# Test connection
cd dbt && dbt debug --profiles-dir .
```

### First Run
```bash
# Install dependencies
make deps

# Run models
make run

# Run tests
make test

# View docs locally
make docs
```

## 📁 Project Structure

```
DBT-Databricks/
├── README.md                           # This file - quick start & overview
├── OPERATIONS.md                      # Deployment, troubleshooting, best practices
├── ENTERPRISE_FEATURES.md             # Enterprise modules documentation
├── ENTERPRISE_DEPLOYMENT_GUIDE.md     # Enterprise deployment instructions
├── GITHUB_ACTIONS_SETUP.md            # GitHub Actions workflow setup guide
├── WHATS_NEW.md                       # Feature changelog
├── ENHANCEMENT_SUMMARY.md             # Summary of enterprise enhancements
├── azure-pipelines.yml                # Azure DevOps consolidated CI/CD pipeline
├── requirements.txt                   # Python dependencies (dbt, SDK, SAST, enterprise tools)
├── .env.example                       # Environment variables template
├── Makefile                           # Common commands (make run, make test, etc.)
├── .secrets.baseline                  # Secrets detection baseline
│
├── dbt/                               # dbt project root
│   ├── dbt_project.yml               # dbt configuration
│   ├── profiles.yml                  # Database connections (dev/staging/prod)
│   ├── models/                       # Data models (3-layer architecture)
│   │   ├── staging/                  # Layer 1: Clean & normalize
│   │   ├── intermediate/             # Layer 2: Transform & join
│   │   └── marts/                    # Layer 3: Facts & dimensions
│   ├── tests/                        # Data quality tests
│   ├── macros/                       # Reusable SQL functions
│   ├── data/                         # Reference/seed data (CSV)
│   └── schema.yml                    # Source definitions & tests
│
├── databricks.yml                     # Root DAB configuration
├── databricks_bundles/                # Environment-specific DAB configs
│   ├── dev/
│   ├── staging/
│   └── prod/
│
├── azure-pipelines.yml                # Azure DevOps CI/CD (root level)
│
├── .github/                           # GitHub Actions & configuration
│   └── workflows/
│       └── dbt-databricks.yml        # Consolidated GitHub Actions CI/CD
│
├── scripts/                           # Automation scripts
│   ├── deploy.py                     # Multi-environment deployment + telemetry + audit
│   └── test_data_load.py             # Sample data loader
│
├── monitoring/                        # Enterprise monitoring module
│   ├── telemetry.py                  # TelemetryClient, HealthCheck, PerformanceMonitor
│   └── monitoring_config.yaml        # Health check, alert, and SLA definitions
│
├── governance/                        # Enterprise data governance module
│   ├── data_governance.py            # Classification, PII detection, SLA framework
│   ├── data_classification.yaml      # Table sensitivity mappings & PII types
│   └── retention_policies.yaml       # Data lifecycle (active → warm → cold → archived)
│
├── compliance/                        # Enterprise compliance & audit module
│   ├── audit_logging.py              # Audit logger, compliance reports (GDPR/CCPA/SOX/HIPAA)
│   └── compliance_frameworks.yaml    # Compliance requirements & reporting config
│
└── .security/                         # Security configurations
    ├── bandit.yaml                   # Python security rules
    └── semgrep.yml                   # SQL/infrastructure scanning rules
```

### Updated Key Sections:
- **Root Level**: `azure-pipelines.yml` (Azure DevOps) - consolidated CI/CD
- **GitHub**: `.github/workflows/dbt-databricks.yml` (GitHub Actions) - consolidated CI/CD
- **Enterprise Modules**: Monitoring, Governance, Compliance with configuration files
- **Documentation**: Added enterprise guides and feature documentation
- **Configuration**: Added monitoring, governance, and compliance YAML files

## 🏗️ Architecture

### Data Medallion Layers
- **Bronze (Raw)**: Unmodified source data
- **Silver (Staging)**: Cleaned, standardized views
- **Gold (Marts)**: Business-ready fact & dimension tables

```
Raw Sources → Staging Views → Intermediate Views → Fact/Dimension Tables → BI Tools
```

### Multi-Environment Setup
| Env | Schema | Cluster | Use Case |
|-----|--------|---------|----------|
| dev | dev_analytics | 1 worker | Development & testing |
| staging | staging_analytics | 2 workers | Pre-production validation |
| prod | prod_analytics | 4 workers | Production analytics |

### CI/CD Pipeline Flow
```
Push Code
    ↓
CI Pipeline (Auto - Azure DevOps or GitHub Actions)
├─ Health Check (Databricks connectivity)
├─ Setup environment
├─ Validate dbt config
├─ Run tests (modified models)
├─ Security scanning (SAST: Bandit, Semgrep, pip-audit, detect-secrets)
├─ SQL linting (sqlfluff)
└─ Generate documentation
    ↓
For Pull Requests: CI stops here
For Main Branch Pushes: Continue to CD
    ↓
CD Pipeline (Auto on main - staging)
├─ Deploy to staging environment
├─ Run full dbt + all tests
├─ Run monitoring health checks
├─ Deploy DAB (Databricks Asset Bundle)
    ↓
Manual Approval Gate
(Requires human review of staging results)
    ↓
CD Pipeline (Manual trigger - production)
├─ Deploy to production
├─ Run production validation tests
├─ Log all operations to audit trail
└─ Complete compliance reporting
```

**Dual CI/CD Support**:
- **Azure DevOps**: `azure-pipelines.yml` (root level)
- **GitHub Actions**: `.github/workflows/dbt-databricks.yml`

## 🔒 Security Features

### SAST Integration
The project includes static application security testing:

**Python Security (Bandit)**
- Detects hardcoded secrets, insecure functions
- Runs on all Python scripts
- Fails pipeline on high severity issues

**SQL Security (Semgrep)**
- Detects SQL injection risks
- Identifies insecure patterns
- Validates dbt model security

**Secrets Detection (Detect Secrets)**
- Detects exposed credentials
- Scans commits for accidental secrets
- Prevents pipeline execution with found secrets

**Dependency Scanning**
- Checks for vulnerable packages
- Runs `pip-audit` on requirements
- Alerts on outdated dependencies

Enable security checks in CI pipeline:
```bash
# Python security
bandit -r scripts/

# SQL/dbt security
semgrep --config p/databricks dbt/models/

# Check dependencies
pip-audit

# Detect secrets
detect-secrets scan
```

## 📊 Common Commands

### Development
```bash
make help              # All available commands
make setup             # Initialize environment
make install           # Install dependencies
make deps              # Install dbt packages
make run              # Run all models
make test             # Run data quality tests
make lint             # Check SQL quality
make docs             # Generate documentation
make security         # Run security scanning
```

### Deployment
```bash
python scripts/deploy.py --target dev         # Deploy to dev
python scripts/deploy.py --target staging     # Deploy to staging
python scripts/deploy.py --target prod        # Deploy to production
```

### Debugging
```bash
make debug            # Test Databricks connection
dbt parse            # Validate dbt project
dbt compile          # Compile templates
make security-audit  # Run all security checks
```

## ⚙️ Configuration

### Environment Variables (`.env`)
```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/warehouse-id
DATABRICKS_TOKEN=your-pat-token

# Staging & production separate credentials
DATABRICKS_HOST_STAGING=...
DATABRICKS_TOKEN_STAGING=...
```

### dbt profiles (dev/staging/prod)
Edit `dbt/profiles.yml` for each environment's connection details.

### Databricks Bundle (environment-specific)
Each environment has its own config in `databricks_bundles/{env}/databricks.yml`:
- Cluster configuration
- Job definitions
- Environment variables

## 🧪 Testing

### dbt Tests
```bash
# All tests
dbt test

# Specific model
dbt test --select dim_customers

# By tag
dbt test --select tag:critical
```

### Data Quality
- Unique & not null constraints
- Referential integrity (relationships)
- Custom business logic tests
- Freshness checks

Define tests in `dbt/models/schema.yml`

## 📚 Documentation

**Main Documentation**
- [README.md](README.md) - This file (overview & quick start)
- [OPERATIONS.md](OPERATIONS.md) - Setup, configuration, and troubleshooting

**Enterprise Features** (if enabled)
- [ENTERPRISE_FEATURES.md](ENTERPRISE_FEATURES.md) - Complete enterprise module reference
- [ENTERPRISE_DEPLOYMENT_GUIDE.md](ENTERPRISE_DEPLOYMENT_GUIDE.md) - Enterprise deployment steps
- [WHATS_NEW.md](WHATS_NEW.md) - Feature changelog
- [ENHANCEMENT_SUMMARY.md](ENHANCEMENT_SUMMARY.md) - Summary of enterprise enhancements

**CI/CD Documentation**
- `.azure-pipelines/` - Azure DevOps pipeline (consolidated)
- [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) - GitHub Actions workflow setup

**See Also**
- `dbt/models/schema.yml` - Model documentation
- `dbt/` folder - Example models with comments
- Generated docs: `make docs` then `dbt docs serve`

## 🔧 Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| dbt | 1.5+ | Data transformation & testing |
| Databricks | Latest | Data warehouse & asset bundles |
| Python | 3.9+ | Orchestration, enterprise modules, scripts |
| Azure DevOps | Cloud | CI/CD pipelines (consolidated) |
| GitHub Actions | Cloud | CI/CD workflows (consolidated) |
| Monitoring | App Insights, Datadog | Telemetry, health checks, performance |
| Data Governance | Custom | Classification, PII detection, SLA framework |
| Compliance | Custom | GDPR, CCPA, SOX, HIPAA audit logging & reports |
| Bandit | 1.7+ | Python security scanning |
| Semgrep | Latest | SQL/infrastructure scanning |
| pip-audit | Latest | Dependency vulnerability scanning |
| detect-secrets | Latest | Secret detection |
| sqlfluff | Latest | SQL linting & formatting |

## 📖 Next Steps

1. **Clone & Setup**: Follow Quick Start above
2. **Customize Models**: Edit `dbt/models/` for your data
3. **Configure CI/CD**: Choose one or both:
   - **Azure DevOps**: Push repository and configure pipeline from `azure-pipelines.yml`
   - **GitHub Actions**: Push to GitHub; workflows auto-activate from `.github/workflows/`
4. **Set Up Environments**: Configure Databricks connections in `.env`
5. **Deploy**: Run `python scripts/deploy.py --target dev`
6. **Enable SAST**: Security scanning runs automatically in CI/CD
7. **(Optional) Enable Enterprise Features**: See [ENTERPRISE_DEPLOYMENT_GUIDE.md](ENTERPRISE_DEPLOYMENT_GUIDE.md)

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes to models/tests
3. Test locally: `make test && make security`
4. Commit: `git add . && git commit -m "Add feature"`
5. Push: `git push origin feature/my-feature`
6. Create PR for code review
7. After approval, merge to main

## 🐛 Troubleshooting

See [OPERATIONS.md](OPERATIONS.md) for:
- Connection issues
- Pipeline failures
- Data quality test failures
- Performance optimization
- Security scanning errors

Quick fixes:
```bash
# Test Databricks connection
make debug

# Validate dbt project
dbt parse --profiles-dir dbt

# Check for security issues
make security-audit
```





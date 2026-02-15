# DBT Databricks Asset Bundle with Azure DevOps CI/CD & SAST

Production-ready dbt + Databricks Asset Bundle + Azure DevOps integration with automated security scanning and SAST.

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
├── README.md                    # This file - quick start & overview
├── OPERATIONS.md               # Deployment, troubleshooting, best practices
├── requirements.txt            # Python dependencies (dbt, SDK, SAST tools)
├── .env.example               # Environment variables template
├── Makefile                   # Common commands (make run, make test, etc.)
│
├── dbt/                       # dbt project root
│   ├── dbt_project.yml       # dbt configuration
│   ├── profiles.yml          # Database connections (dev/staging/prod)
│   ├── models/               # Data models (3-layer architecture)
│   │   ├── staging/          # Layer 1: Clean & normalize
│   │   ├── intermediate/     # Layer 2: Transform & join
│   │   └── marts/            # Layer 3: Facts & dimensions
│   ├── tests/                # Data quality tests
│   ├── macros/               # Reusable SQL functions
│   ├── data/                 # Reference/seed data (CSV)
│   └── schema.yml            # Source definitions & tests
│
├── databricks.yml            # Root DAB configuration
├── databricks_bundles/       # Environment-specific configs
│   ├── dev/
│   ├── staging/
│   └── prod/
│
├── .azure-pipelines/         # CI/CD pipeline definitions
│   └── azure-pipelines.yml  # Consolidated CI/CD pipeline (PR & deployment)
│
├── scripts/                  # Automation scripts
│   ├── deploy.py            # Multi-environment deployment
│   └── test_data_load.py    # Sample data loader
│
└── .security/               # Security configurations
    ├── bandit.yaml         # Python security rules
    └── semgrep.yml         # SQL/infrastructure scanning
```

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
Push to GitHub/ADO
    ↓
CI Pipeline (Auto)
├─ Setup environment
├─ Validate dbt config
├─ Run tests (modified models)
├─ Security scanning (SAST)
├─ SQL linting
└─ Publish artifacts
    ↓
Manual Code Review
    ↓
Merge to main
    ↓
CD Pipeline (Auto)
├─ Deploy to staging
├─ Run full dbt + tests
├─ Deploy DAB
    ↓
Manual Approval
    ↓
├─ Deploy to production
└─ Run production validation
```

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
- [OPERATIONS.md](OPERATIONS.md) - Setup guide, deployment, troubleshooting

**See Also**
- `dbt/models/schema.yml` - Model documentation
- `dbt/` folder - Example models with comments
- Generated docs: `make docs` then `dbt docs serve`

## 🔧 Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| dbt | 1.5+ | Data transformation & testing |
| Databricks | Latest | Data warehouse & asset bundles |
| Python | 3.9+ | Orchestration & scripts |
| Azure DevOps | Cloud | CI/CD pipelines |
| Bandit | 1.7+ | Python security scanning |
| Semgrep | Latest | SQL/infrastructure scanning |
| pip-audit | Latest | Dependency vulnerability scanning |
| detect-secrets | Latest | Secret detection |

## 📖 Next Steps

1. **Clone & Setup**: Follow Quick Start above
2. **Customize Models**: Edit `dbt/models/` for your data
3. **Configure Azure DevOps**: Create pipelines from `.azure-pipelines/` files
4. **Set Up Environments**: Configure Databricks connections in `.env`
5. **Deploy**: Run `python scripts/deploy.py --target dev`
6. **Enable SAST**: Configure security scanning in pipeline

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

## 📞 Support

- **Docs**: [dbt](https://docs.getdbt.com), [Databricks](https://docs.databricks.com)
- **Issues**: Check OPERATIONS.md troubleshooting section
- **Team**: Contact data engineering (@channel)

## 📜 License

[Your License Here]

---

**Status**: ✅ Production Ready | **Last Updated**: Feb 15, 2026

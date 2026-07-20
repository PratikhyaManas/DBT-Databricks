.PHONY: help setup install test run clean docs deploy lint deps parse security security-audit bandit semgrep detect-secrets pip-audit pipeline-list pipeline-dev pipeline-staging pipeline-prod pipeline-run

PYTHON := python3
DBT_PATH := dbt
PROFILE_DIR := $(DBT_PATH)

help:
	@echo "Databricks dbt Project - Available Commands"
	@echo "==========================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup       - Create virtual environment and install dependencies"
	@echo "  make install     - Install Python dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make deps        - Install dbt dependencies"
	@echo "  make parse       - Parse dbt project (validate syntax)"
	@echo "  make run         - Run all dbt models"
	@echo "  make test        - Run dbt tests"
	@echo "  make lint        - Run SQL linting"
	@echo "  make docs        - Generate dbt documentation"
	@echo ""
	@echo "Security & SAST:"
	@echo "  make security        - Run basic security checks"
	@echo "  make security-audit  - Run all security checks (full audit)"
	@echo "  make bandit          - Python security scanning"
	@echo "  make semgrep         - SQL/dbt security scanning"
	@echo "  make detect-secrets  - Detect hardcoded secrets"
	@echo "  make pip-audit       - Check for vulnerable dependencies"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-dev      - Deploy to dev environment"
	@echo "  make deploy-staging  - Deploy to staging environment"
	@echo "  make deploy-prod     - Deploy to production environment"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean           - Clean dbt artifacts"
	@echo "  make debug           - Debug dbt connection"
	@echo "  make load-test-data  - Load sample test data"
	@echo ""

setup:
	$(PYTHON) -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate (or venv\Scripts\activate on Windows)"
	make install

install:
	pip install --upgrade pip
	pip install -r requirements.txt

deps:
	cd $(DBT_PATH) && dbt deps --profiles-dir $(PROFILE_DIR)

parse:
	cd $(DBT_PATH) && dbt parse --profiles-dir $(PROFILE_DIR)

run:
	cd $(DBT_PATH) && dbt run --profiles-dir $(PROFILE_DIR)

test:
	cd $(DBT_PATH) && dbt test --profiles-dir $(PROFILE_DIR)

lint:
	sqlfluff vet --dialect databricks $(DBT_PATH)/models/

docs:
	cd $(DBT_PATH) && dbt docs generate --profiles-dir $(PROFILE_DIR)
	@echo "📖 Documentation generated in $(DBT_PATH)/target/"

debug:
	cd $(DBT_PATH) && dbt debug --profiles-dir $(PROFILE_DIR)

# Security & SAST Commands
security:
	@echo "🔒 Running basic security checks..."
	$(PYTHON) -m bandit -r scripts/ --severity-level medium
	@echo "✅ Basic security checks completed"

security-audit:
	@echo "🔒 Running full security audit..."
	make bandit
	make semgrep
	make detect-secrets
	make pip-audit
	@echo "✅ Full security audit completed"

bandit:
	@echo "Running Bandit (Python security)..."
	$(PYTHON) -m bandit -r scripts/ -f txt
	@echo "✅ Bandit completed"

semgrep:
	@echo "Running Semgrep (SQL security)..."
	semgrep --config p/databricks $(DBT_PATH)/models/ --json || true
	@echo "✅ Semgrep completed"

detect-secrets:
	@echo "Running detect-secrets..."
	detect-secrets scan --baseline .secrets.baseline
	@echo "✅ Secret detection completed"

pip-audit:
	@echo "Running pip-audit (dependency scanning)..."
	pip-audit
	@echo "✅ Dependency audit completed"

clean:
	rm -rf $(DBT_PATH)/target/
	rm -rf $(DBT_PATH)/dbt_packages/
	rm -rf $(DBT_PATH)/logs/
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned dbt artifacts"

deploy-dev:
	$(PYTHON) scripts/deploy.py --target dev

deploy-staging:
	$(PYTHON) scripts/deploy.py --target staging

deploy-prod:
	$(PYTHON) scripts/deploy.py --target prod

pipeline-list:
	$(PYTHON) scripts/metadata_pipeline.py --list-pipelines

pipeline-dev:
	$(PYTHON) scripts/metadata_pipeline.py --pipeline full_deploy --target dev

pipeline-staging:
	$(PYTHON) scripts/metadata_pipeline.py --pipeline full_deploy --target staging

pipeline-prod:
	$(PYTHON) scripts/metadata_pipeline.py --pipeline full_deploy --target prod

pipeline-run:
	$(PYTHON) scripts/metadata_pipeline.py --pipeline $(PIPELINE) --target $(TARGET)

load-test-data:
	$(PYTHON) scripts/test_data_load.py

.DEFAULT_GOAL := help

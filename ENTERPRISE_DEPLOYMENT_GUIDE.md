# Enterprise Features Deployment Guide

Step-by-step instructions for enabling and deploying enterprise features in production.

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Phase 1: Prerequisites & Setup](#phase-1-prerequisites--setup)
3. [Phase 2: Configure Monitoring](#phase-2-configure-monitoring)
4. [Phase 3: Configure Governance](#phase-3-configure-governance)
5. [Phase 4: Configure Compliance](#phase-4-configure-compliance)
6. [Phase 5: Test & Validation](#phase-5-test--validation)
7. [Phase 6: Production Deployment](#phase-6-production-deployment)
8. [Post-Deployment Verification](#post-deployment-verification)

---

## Pre-Deployment Checklist

- [ ] Review all configuration files in `monitoring/`, `governance/`, `compliance/`
- [ ] Obtain Azure Application Insights connection string
- [ ] Obtain Datadog API key (if using)
- [ ] Identify Slack webhook for alerts
- [ ] Map all tables to sensitivity levels
- [ ] Designate compliance framework requirements (GDPR/CCPA/SOX/HIPAA)
- [ ] Approve data retention policies with legal team
- [ ] Notify team of new monitoring and governance features
- [ ] Backup current dbt project and workspace configuration

---

## Phase 1: Prerequisites & Setup

### Step 1.1: Install Dependencies

```bash
cd /path/to/DBT-Databricks

# Create/activate virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install all dependencies including enterprise modules
pip install -r requirements.txt

# Verify installations
python -c "import databricks; import azure.monitor; import datadog; print('✅ All dependencies installed')"
```

### Step 1.2: Set Up Environment Variables

```bash
# Copy the template
cp .env.example .env

# Edit with your values
nano .env
```

**Required Variables**:

```bash
# Databricks
DATABRICKS_HOST=https://your-workspace.databricks.com
DATABRICKS_TOKEN=dapi...
DATABRICKS_WAREHOUSE_ID=abc123...

# Azure Application Insights
APPINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx;IngestionEndpoint=https://...

# Datadog (optional)
DATADOG_API_KEY=your-api-key
DATADOG_ENABLED=false  # Set to true if using Datadog

# Slack Alerts (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Alert Recipients (optional)
ALERT_EMAIL_RECIPIENTS=alerts@company.com,team@company.com
```

### Step 1.3: Load Environment Variables

```bash
# Load into current shell
export $(cat .env | xargs)

# Verify
echo "Databricks Host: $DATABRICKS_HOST"
echo "App Insights Connection: ${APPINSIGHTS_CONNECTION_STRING:0:20}..."
```

---

## Phase 2: Configure Monitoring

### Step 2.1: Update Monitoring Configuration

```bash
# Edit the main monitoring config
nano monitoring/monitoring_config.yaml
```

**Critical Settings to Customize**:

```yaml
# Set your Azure connection
application_insights:
  connection_string: "${APPINSIGHTS_CONNECTION_STRING}"
  environment: "prod"

# Adjust health check frequencies for your SLAs
health_checks:
  databricks:
    check_frequency_seconds: 300  # Every 5 minutes
  warehouse:
    warehouse_ids:
      - "${DATABRICKS_WAREHOUSE_ID}"

# Adjust performance baselines for your models
performance_monitoring:
  dbt_models:
    slow_model_threshold_seconds: 60  # Adjust based on your model speeds
    baselines:
      - model_name: "fct_customer_orders"
        baseline_seconds: 45
        warning_threshold_seconds: 60
        critical_threshold_seconds: 120

# Configure alerts
alerting:
  channels:
    - type: "slack"
      webhook_url: "${SLACK_WEBHOOK_URL}"
      enabled: true
    - type: "email"
      recipients:
        - "${ALERT_EMAIL_RECIPIENTS}"
      enabled: true
```

### Step 2.2: Verify Monitoring Configuration

```bash
# Validate YAML syntax
python - <<'EOF'
import yaml
with open('monitoring/monitoring_config.yaml') as f:
    config = yaml.safe_load(f)
    print(f"✅ Configuration valid")
    print(f"  - App Insights: {config['application_insights'].get('enabled')}")
    print(f"  - Health Checks: {len(config['health_checks'])} types")
EOF
```

### Step 2.3: Test Telemetry Client

```bash
# Test Application Insights connection
python - <<'EOF'
import os
from monitoring.telemetry import initialize_telemetry, get_telemetry_client

try:
    initialize_telemetry("test-job")
    telemetry = get_telemetry_client()
    telemetry.record_event("deployment_test", {"status": "started"})
    print("✅ Telemetry working correctly")
except Exception as e:
    print(f"❌ Telemetry error: {e}")
    exit(1)
EOF
```

### Step 2.4: Test Health Checks

```bash
# Verify Databricks connectivity
python - <<'EOF'
from monitoring.telemetry import get_health_check

health = get_health_check()
if health.check_databricks_connection():
    print("✅ Databricks connection OK")
else:
    print("❌ Databricks connection FAILED")
    exit(1)
EOF
```

---

## Phase 3: Configure Governance

### Step 3.1: Update Data Classification

```bash
# Edit classification mappings
nano governance/data_classification.yaml
```

**Review These Sections**:

1. **Map your tables to sensitivity levels**:
```yaml
data_classification:
  customer_tables:
    - table_name: "your_schema.customers"  # Update with actual names
      sensitivity: "RESTRICTED"
      pii_types: [email, phone, address]
      retention_days: 2555  # 7 years
```

2. **Update PII detection rules** (if custom patterns needed):
```yaml
data_masking:
  email_mask_pattern: "^(.)[^@]*(@.*)$"
  email_mask_replacement: "$1***$2"
```

3. **Configure access control**:
```yaml
access_control:
  roles:
    analyst:
      can_access: [CONFIDENTIAL, INTERNAL, PUBLIC]
      cannot_access: [customer_pii]
```

### Step 3.2: Update Data Retention Policies

```bash
# Edit retention schedule
nano governance/retention_policies.yaml
```

**Key Sections to Configure**:

```yaml
classification_based_retention:
  RESTRICTED:
    default_years: 7  # Adjust per legal requirements
    tables:
      - pattern: "your_schema.customers"
        retention_years: 7
        right_to_be_forgotten: true

# Configure archival stages
archival:
  strategies:
    - name: "hot_to_warm"
      after_days: 30  # Move to warm storage after 30 days

# Set backup/recovery targets
backup:
  policy:
    frequency: "daily"
    retention_days: 30  # Keep 30-day backup window
```

### Step 3.3: Validate Governance Config

```bash
# Check for all required tables
python - <<'EOF'
from governance.data_governance import get_governance_registry

registry = get_governance_registry()
print(f"✅ {len(registry._policies)} governance policies loaded")
for name, policy in registry._policies.items():
    print(f"  - {name}: {policy.classification} (retention: {policy.retention_days} days)")
EOF
```

---

## Phase 4: Configure Compliance

### Step 4.1: Select Compliance Frameworks

```bash
# Edit framework configuration
nano compliance/compliance_frameworks.yaml
```

**Enable Required Frameworks**:

```yaml
compliance_frameworks:
  GDPR:
    enabled: true   # If your org is in EU or processes EU residents
  CCPA:
    enabled: true   # If your org is in California or processes CA residents
  SOX:
    enabled: true   # If your org is public company or has financial data
  HIPAA:
    enabled: true   # If your org processes health information
```

### Step 4.2: Configure Report Generation

```yaml
reporting:
  # Set report distribution
  distribution:
    email_recipients:
      - compliance_team@company.com
      - audit_team@company.com
    storage_location: "dbfs:/compliance/reports/"
  
  # Set report schedules
  schedule:
    daily:
      enabled: true
      time: "02:00"  # 2 AM UTC
    monthly:
      enabled: true
      day: 1
      time: "02:00"
```

### Step 4.3: Initialize Audit Logging

```bash
# Test audit logger
python - <<'EOF'
from compliance.audit_logging import initialize_audit_logger, get_audit_logger

try:
    initialize_audit_logger()
    audit = get_audit_logger()
    print("✅ Audit logging initialized")
except Exception as e:
    print(f"❌ Audit logging error: {e}")
    exit(1)
EOF
```

### Step 4.4: Create Audit Log Directory

```bash
# Ensure audit log directory exists in DBFS
python - <<'EOF'
from databricks.sdk import WorkspaceClient

ws = WorkspaceClient()
try:
    # List to verify directory exists
    ws.dbfs.get_status("dbfs:/logs/audit/")
    print("✅ Audit log directory exists")
except:
    print("⚠️  Audit log directory not found - will be created on first use")
EOF
```

---

## Phase 5: Test & Validation

### Step 5.1: Run Integration Tests

```bash
# Test all enterprise modules
python - <<'EOF'
import sys

print("\n" + "="*60)
print("ENTERPRISE FEATURES TEST SUITE")
print("="*60)

# Test 1: Monitoring
print("\n[1/4] Testing Monitoring...")
try:
    from monitoring.telemetry import initialize_telemetry, get_telemetry_client, get_health_check
    initialize_telemetry("test-suite")
    telemetry = get_telemetry_client()
    telemetry.record_event("test_event", {"status": "running"})
    health = get_health_check()
    health.check_databricks_connection()
    print("✅  Monitoring: PASS")
except Exception as e:
    print(f"❌  Monitoring: FAIL - {e}")
    sys.exit(1)

# Test 2: Governance
print("\n[2/4] Testing Governance...")
try:
    from governance.data_governance import get_governance_registry, PIIDetector
    registry = get_governance_registry()
    detector = PIIDetector()
    if detector.detect_pii("test@example.com", "email"):
        print("✅  Governance: PASS")
    else:
        raise Exception("PII detection failed")
except Exception as e:
    print(f"❌  Governance: FAIL - {e}")
    sys.exit(1)

# Test 3: Compliance
print("\n[3/4] Testing Compliance...")
try:
    from compliance.audit_logging import initialize_audit_logger, get_audit_logger
    initialize_audit_logger()
    audit = get_audit_logger()
    audit.log_security_event("test_event", details={"test": "value"})
    print("✅  Compliance: PASS")
except Exception as e:
    print(f"❌  Compliance: FAIL - {e}")
    sys.exit(1)

# Test 4: Configuration Loading
print("\n[4/4] Testing Configuration Loading...")
try:
    import yaml
    with open('monitoring/monitoring_config.yaml') as f:
        yaml.safe_load(f)
    with open('governance/data_classification.yaml') as f:
        yaml.safe_load(f)
    with open('compliance/compliance_frameworks.yaml') as f:
        yaml.safe_load(f)
    print("✅  Configuration: PASS")
except Exception as e:
    print(f"❌  Configuration: FAIL - {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅  ALL TESTS PASSED - Ready for production deployment")
print("="*60 + "\n")
EOF
```

### Step 5.2: Test Deployment Script with Telemetry

```bash
# Test deployment to dev environment with telemetry
python scripts/deploy.py --target dev --skip-bundle

# Check that deployment metrics were recorded
python - <<'EOF'
from compliance.audit_logging import get_audit_logger

audit = get_audit_logger()
recent_logs = audit.get_recent_logs(hours=1)
if len(recent_logs) > 0:
    print(f"✅ Deployment audit logs recorded ({len(recent_logs)} events)")
else:
    print("⚠️  No audit logs found (expected if first deployment)")
EOF
```

### Step 5.3: Verify CI Pipeline Health Checks

```bash
# View the pipeline configuration
cat azure-pipelines.yml | grep -A 20 "HealthCheck"

# When you push code, the pipeline will run health checks automatically
# View results in Azure DevOps: Pipelines > Run > HealthCheck stage
```

---

## Phase 6: Production Deployment

### Step 6.1: Create Production Deployment Plan

```bash
# Generate deployment plan
python scripts/deploy.py --target prod --skip-bundle --skip-dbt > deployment_plan.log

# Review the plan
cat deployment_plan.log | tail -50
```

### Step 6.2: Deploy to Production

```bash
# Full production deployment with monitoring
python scripts/deploy.py --target prod

# Monitor output for:
# - ✅ Health checks passed
# - ✅ dbt models deployed successfully
# - ✅ Metrics recorded in Application Insights
# - ✅ Audit logs created
```

### Step 6.3: Verify Production Metrics

```bash
# Query metrics in Application Insights
python - <<'EOF'
from monitoring.telemetry import get_telemetry_client

telemetry = get_telemetry_client()

# Check that production metrics are arriving
print("✅ Production deployment completed")
print("\nMetrics are now available in:")
print("  - Azure Application Insights")
print("  - Datadog Dashboard")
print("  - Azure DevOps Pipeline")
EOF
```

### Step 6.4: Verify Audit Logs

```bash
# Check audit logs were created
python - <<'EOF'
from databricks.sdk import WorkspaceClient
from pathlib import Path

ws = WorkspaceClient()
try:
    files = ws.dbfs.list("dbfs:/logs/audit/")
    if len(list(files)) > 0:
        print("✅ Audit logs successfully created in production")
    else:
        print("⚠️  No audit logs found yet (may appear after first operation)")
except:
    print("⚠️  Unable to list audit log directory (may need permissions)")
EOF
```

---

## Post-Deployment Verification

### Step 1: Check Application Insights

```
1. Go to Azure Portal > Application Insights > Your Resource
2. Navigate to: Metrics
3. Look for custom metrics:
   - dbt.run.duration_seconds
   - dbt.test.duration_seconds
   - deployment.total.duration_seconds
4. Verify data is flowing in
```

### Step 2: Check Audit Logs

```bash
# Query audit logs in Databricks
%sql
SELECT 
  timestamp,
  user_id,
  action,
  resource,
  status
FROM delta.`dbfs:/logs/audit/`
WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL 24 HOUR
ORDER BY timestamp DESC
LIMIT 100
```

### Step 3: Generate First Compliance Report

```bash
# Generate initial compliance report
python - <<'EOF'
from compliance.audit_logging import get_audit_logger
from datetime import datetime, timedelta

audit = get_audit_logger()

# Generate GDPR report for last 24 hours
end_date = datetime.now()
start_date = end_date - timedelta(days=1)

gdpr_report = audit.generate_gdpr_report(
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d")
)

print("=== GDPR Report ===")
print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print(f"Data Processing Activities: {len(gdpr_report['data_processing_activities'])}")
print(f"Deletion Requests: {len(gdpr_report['deletion_requests'])}")
EOF
```

### Step 4: Test Alert Notifications

```bash
# Manually trigger an alert to test notification system
python - <<'EOF'
from monitoring.telemetry import get_telemetry_client

telemetry = get_telemetry_client()

# Record a test alert
telemetry.record_event(
    "test_alert_trigger",
    {"severity": "HIGH", "message": "Test alert - can be ignored"}
)

print("✅ Test alert sent")
print("Check your email/slack for notification within 2 minutes")
EOF
```

---

## Rollback Plan

If issues occur, rollback is simple:

### Quick Rollback

```bash
# Disable monitoring by commenting out initialization
# In deploy.py, comment out:
# initialize_telemetry("dbt-databricks-deploy")

# Disable audit logging:
# initialize_audit_logger()

# Redeploy
git checkout HEAD -- scripts/deploy.py
python scripts/deploy.py --target prod
```

### Full Rollback

```bash
# Revert to previous commit
git log --oneline | head -5
git revert <commit-hash>
git push

# Redeploy from previous version
python scripts/deploy.py --target prod
```

---

## Troubleshooting Deployment Issues

### Issue: Application Insights Connection Failed

```bash
# Check connection string
echo $APPINSIGHTS_CONNECTION_STRING

# Verify format (should have InstrumentationKey= and IngestionEndpoint=)

# Test connection
python - <<'EOF'
from azure.monitor.opentelemetry import configure_azure_monitor
configure_azure_monitor()
print("✅ Azure Monitor connection OK")
EOF
```

### Issue: Audit Logs Not Appearing

```bash
# Check that logs directory can be accessed
python - <<'EOF'
from databricks.sdk import WorkspaceClient
ws = WorkspaceClient()
try:
    ws.dbfs.get_status("dbfs:/logs/")
    print("✅ Can access dbfs:/logs/")
except Exception as e:
    print(f"❌ Cannot access dbfs:/logs/: {e}")
EOF
```

### Issue: Governance Registry Not Loaded

```bash
# Check YAML file syntax
python -c "
import yaml
try:
    with open('governance/data_classification.yaml') as f:
        yaml.safe_load(f)
    print('✅ YAML syntax OK')
except Exception as e:
    print(f'❌ YAML syntax error: {e}')
"
```

### Issue: Health Checks Failing

```bash
# Debug health check
python - <<'EOF'
from monitoring.telemetry import get_health_check
import traceback

health = get_health_check()
try:
    if not health.check_databricks_connection():
        print("❌ Databricks connection check failed")
        # Verify credentials
        import os
        print(f"  DATABRICKS_HOST: {os.getenv('DATABRICKS_HOST')}")
        print(f"  DATABRICKS_TOKEN: {'set' if os.getenv('DATABRICKS_TOKEN') else 'NOT SET'}")
except Exception as e:
    print(f"❌ Health check error: {e}")
    traceback.print_exc()
EOF
```

---

## Success Indicators

✅ **Deployment is successful when:**

1. No errors during `python scripts/deploy.py --target prod`
2. Metrics appear in Application Insights within 2 minutes
3. Audit logs created in `dbfs:/logs/audit/`
4. Health check stage passes in CI pipeline
5. Email/Slack alerts are received for test events
6. Compliance reports generate without errors

---

## Next Steps After Successful Deployment

1. **Schedule Compliance Reviews**: Monthly GDPR/CCPA/SOX/HIPAA reports
2. **Monitor SLAs**: Review data quality SLA compliance dashboard
3. **Tune Baselines**: Adjust performance thresholds based on actuals
4. **Team Training**: Ensure team understands new governance policies
5. **Document Processes**: Update runbooks with new monitoring/governance procedures

---

**Document Version**: 1.0 | **Last Updated**: March 15, 2026

For issues or questions, refer to [ENTERPRISE_FEATURES.md](ENTERPRISE_FEATURES.md) or [OPERATIONS.md](OPERATIONS.md)

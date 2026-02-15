# GitHub Actions Workflows Setup Guide

## Overview

This repository includes GitHub Actions workflows equivalent to the Azure DevOps pipeline. They provide automated CI/CD for your dbt and Databricks projects.

## Workflow Structure

**Workflow File**: `.github/workflows/dbt-databricks.yml` (consolidated CI/CD)

The repository uses a single, consolidated GitHub Actions workflow that handles both CI and CD:

### CI Jobs (Run on all branches & PRs)

1. **health-check**: Verify Databricks connectivity and warehouse availability
2. **setup**: Install dependencies
3. **validate**: Validate dbt project configuration
4. **test**: Run dbt models and data quality tests
5. **security**: SAST scanning (Bandit, Semgrep, detect-secrets, pip-audit)
6. **lint**: SQL code quality checks (sqlfluff)
7. **documentation**: Generate dbt documentation
8. **ci-status**: Overall CI status check

**Triggers**:
- Push to `main`, `develop`, or `feature/*` branches
- Pull requests to `main` or `develop`

### CD Jobs (Run only on main branch push, after successful CI)

1. **deploy-staging**: Deploy to staging environment (automatic)
   - Install dependencies
   - Run dbt models
   - Execute data quality tests
   - Deploy Databricks Asset Bundle
   - Requires environment: `staging`
   
2. **approve-production**: Manual approval gate for production
   - Requires environment approval
   - Requires environment: `production-approval`
   
3. **deploy-production**: Deploy to production (after approval)
   - Install dependencies
   - Run dbt models in production
   - Execute production tests
   - Deploy production DAB
   - Requires environment: `production`

**Triggers**:
- Only runs on push to `main` branch (not on PRs)
- Conditional: `if: github.ref == 'refs/heads/main' && github.event_name == 'push'`

## Required GitHub Secrets

Add these secrets in your GitHub repository settings: **Settings > Secrets and variables > Actions**

### Development/CI Secrets:
```
DATABRICKS_HOST
DATABRICKS_HTTP_PATH
DATABRICKS_TOKEN
```

### Staging Secrets:
```
DATABRICKS_HOST_STAGING
DATABRICKS_HTTP_PATH_STAGING
DATABRICKS_TOKEN_STAGING
```

### Production Secrets:
```
DATABRICKS_HOST_PROD
DATABRICKS_HTTP_PATH_PROD
DATABRICKS_TOKEN_PROD
```

### Workspace URLs (Optional):
```
DATABRICKS_WORKSPACE_URL          # Staging workspace URL
DATABRICKS_WORKSPACE_URL_PROD      # Production workspace URL
```

### Setting Secrets in GitHub:

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Navigate to **Secrets and variables > Actions**
4. Click **New repository secret**
5. Enter secret name and value
6. Repeat for all required secrets

## GitHub Environments Setup

To enable the approval gates for production, set up GitHub Environments:

### 1. Create Staging Environment

1. Go to **Settings > Environments**
2. Click **New environment** and name it `staging`
3. (Optional) Configure deployment protection rules:
   - Go to environment settings
   - Enable "Require reviewers"
   - Add team/users who can approve staging deployments

### 2. Create Production-Approval Environment

1. Click **New environment** and name it `production-approval`
2. Enable "Require reviewers"
3. Add users who can approve production deployments
4. Set required reviewers (1-10)

### 3. Create Production Environment

1. Click **New environment** and name it `production`
2. Enable "Require reviewers"
3. Add production deployment approvers
4. (Optional) Add additional protection rules

### Environment Protection Rules

For each environment, you can configure:
- **Required reviewers**: Specific people who must approve
- **Deployment branches**: Limit deployments to specific branches (e.g., main only)
- **Automatic execution**: Immediate or with approval requirement

### Recommended Setup:

**Staging**:
- Required reviewers: 1 (data engineer)
- Deployment branch: main only
- Auto-approve: No (require manual approval)

**Production-Approval**:
- Required reviewers: 2 (principal engineer + manager)
- Deployment branch: main only

**Production**:
- Required reviewers: 1 (ops team)
- Deployment branch: main only

## Workflow Execution

### CI Pipeline Execution

When you push code to a branch or create a pull request:

1. GitHub automatically triggers the CI workflow
2. All seven CI jobs run in parallel (with dependencies respected)
3. Results appear in the PR checks section
4. Merge is blocked if any required checks fail

View results:
- Go to **Actions** tab
- Click the workflow run name
- View individual job logs

### CD Pipeline Execution

When code is merged to `main`:

1. CI workflow runs first
2. If CI passes, CD workflow automatically starts
3. **Staging deployment** begins immediately
4. Once staging succeeds, **approval gate** waits for review
5. After reviewer approval, **production deployment** executes

### Manual Workflow Dispatch

You can manually trigger workflows:

1. Go to **Actions** tab
2. Select workflow (CI or CD)
3. Click **Run workflow**
4. Select branch
5. Click **Run workflow**

## Job Dependencies

### CI Workflow Dependencies:
```
health-check
↓
setup
↓
validate
↓
test
↓
documentation

security (parallel with others)
lint (parallel with others)

ci-status (waits for all)
```

### CD Workflow Dependencies:
```
deploy-staging
↓
approve-production
↓
deploy-production
```

## Monitoring & Troubleshooting

### View Workflow Runs

1. Go to **Actions** tab
2. Click on desired workflow
3. Select a run
4. Click on individual jobs to view logs

### Common Issues

**Secrets not found**:
- Ensure secret names match exactly (case-sensitive)
- Verify secrets are in repository (not organization level)
- Wait 60 seconds after adding secret before running workflow

**Databricks connection fails**:
- Verify `DATABRICKS_TOKEN` is correct
- Check `DATABRICKS_HOST` format (https://...)
- Ensure IP allowlisting isn't blocking GitHub

**Approval gate not appearing**:
- Verify `staging` environment exists
- Check that required reviewers are configured
- Ensure workflow push is to `main` branch

**Jobs not starting**:
- Check branch protection rules
- Verify workflow syntax (run `actions/workflow-lint`)
- Check if runner is available

## Performance Optimization

### Caching

The workflows use GitHub Actions caching for pip packages:

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.9'
    cache: 'pip'  # Automatically caches pip packages
```

This speeds up subsequent runs by ~60%.

### Parallel Execution

Security and Lint jobs run in parallel with other jobs:

```yaml
security:
  runs-on: ubuntu-latest
  continue-on-error: true  # Don't block if security scan passes
```

### Resource Management

- **Ubuntu Latest**: Standard 2-core runner
- **Timeout**: 360 minutes per job (default)
- **Artifact retention**: 90 days (default)

## Artifact Storage

Workflows generate artifacts:

- **security-reports**: Bandit, Semgrep, pip-audit results
- **dbt-artifacts**: dbt documentation, target files

View artifacts:
1. Go to **Actions** tab
2. Click workflow run
3. Scroll to **Artifacts** section
4. Download desired artifacts

Artifacts expire after 90 days by default.

## Maintenance

### Update Dependencies

Periodically update action versions:

```bash
# Current versions used
actions/checkout@v4
actions/setup-python@v4
actions/upload-artifact@v3
```

Check for updates:
- Visit action source: `github.com/actions/<action-name>/releases`
- Update version in workflow file

### Monitor Workflow Health

- Watch **Insights > All workflows** for trends
- Alert on repeated failures
- Review security scan results regularly

## Integration with Azure DevOps

Both Azure DevOps and GitHub Actions pipelines:
- ✅ Run identical CI checks
- ✅ Deploy to same Databricks workspaces
- ✅ Use same dbt profiles and configurations
- ✅ Generate same artifacts

**Note**: Use one as primary CI/CD and disable the other to avoid duplicate executions.

## Next Steps

1. **Add secrets** to GitHub repository
2. **Create environments** (staging, production-approval, production)
3. **Configure protection rules** for production
4. **Test CI workflow** by creating a test branch
5. **Review workflow runs** in Actions tab
6. **Monitor logs** for any issues

## Useful Commands

### Validate Workflow Syntax

```bash
# GitHub CLI
gh workflow validate .github/workflows/dbt-databricks.yml
```

### List Workflow Runs

```bash
gh run list --workflow=dbt-databricks.yml
```

### View Workflow Details

```bash
gh run view <run-id>
```

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Environment Protection Rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Secrets Management](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

# GitHub Actions Cloud Run Deployment Troubleshooting Guide

This guide helps diagnose and fix common Cloud Run deployment failures, based on real troubleshooting experiences.

## Quick Diagnosis Commands

When a deployment fails, run these commands first to gather information:

```bash
# 1. Check recent workflow runs
gh run list --limit 5

# 2. Get the latest failed run logs
gh run view [RUN_ID] --log

# 3. Check current Cloud Run service status
gcloud run services describe basketball-stats --region=us-west1 --format="get(status.conditions[0].type,status.conditions[0].status)"

# 4. Check Cloud Run container logs (replace revision name)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=basketball-stats AND resource.labels.revision_name=basketball-stats-00XXX-XXX" --limit=20 --format="table(timestamp,severity,textPayload)" --freshness=10m

# 5. Check service configuration
gcloud run services describe basketball-stats --region=us-west1 --format="get(spec.template.spec.containers[0].env,spec.template.spec.containers[0].args)"
```

## Common Issues and Solutions

### 1. Container Startup Timeout

**Symptoms:**
- Error: "Revision is not ready and cannot serve traffic"
- "Container failed to start and listen on the port defined by PORT=8000"
- Long deployment time followed by failure

**Common Causes:**

#### A. Wrong Container Command/Args
```bash
# Check if service has incorrect args
gcloud run services describe basketball-stats --region=us-west1 --format="get(spec.template.spec.containers[0].args)"

# If it shows something like "basketball-stats;init-db", the service is running CLI commands instead of the web server
# Fix by redeploying with empty args:
gcloud run deploy basketball-stats \
  --image us-west1-docker.pkg.dev/basketball-stats-461220/basketball-stats/basketball-stats-app:latest \
  --region us-west1 \
  --args=""
```

#### B. Missing Environment Variables
```bash
# Check required environment variables
gcloud run services describe basketball-stats --region=us-west1 --format="get(spec.template.spec.containers[0].env)"

# Required variables for production:
# - ENVIRONMENT=production
# - SECRET_KEY (from GitHub secrets)
# - DATABASE_URL (for Cloud SQL connection)
```

#### C. Database Connection Issues
```bash
# Check if app is trying to connect to wrong database
# Look for SQLite vs PostgreSQL errors in logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=basketball-stats" --limit=30 --format="value(textPayload)" --freshness=10m | grep -E "(sqlite|postgresql|database|connection)"
```

### 2. Database Migration Issues

**Symptoms:**
- Migration job succeeds but app fails to start
- "Applying migrations to database" in app container logs
- Database connection errors during startup

**Solution:**
Migrations should only run in the dedicated migration job, not during app startup.

```bash
# Check if migration job exists and is working
gcloud run jobs describe basketball-stats-migrate --region=us-west1

# Check migration job logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=basketball-stats-migrate" --limit=10 --format="table(timestamp,severity,textPayload)" --freshness=30m
```

### 3. Missing GitHub Secrets

**Symptoms:**
- Environment validation errors
- "SECRET_KEY environment variable must be set"

**Solution:**
```bash
# Check current secrets
gh secret list

# Add missing secrets
gh secret set SECRET_KEY --body "$(openssl rand -hex 32)"
gh secret set DATABASE_URL --body "postgresql://postgres:your_password@10.89.16.2:5432/basketball_stats"
```

### 4. Image Build Issues

**Symptoms:**
- Deployment uses old image
- Missing dependencies or files

**Solution:**
```bash
# Check if latest image was built and pushed
gcloud artifacts docker images list us-west1-docker.pkg.dev/basketball-stats-461220/basketball-stats/basketball-stats-app --limit=5

# Force rebuild by pushing a new commit or manually trigger workflow
gh workflow run deploy.yml
```

## Deployment Workflow Troubleshooting

### Check Workflow Status
```bash
# List recent workflow runs
gh run list --workflow=deploy.yml --limit=10

# View specific run details
gh run view [RUN_ID] --log

# Check if workflow is using correct secrets
gh secret list
```

### Common Workflow Fixes

1. **Migration Job Updates**: The workflow updates the migration job before running migrations to ensure it uses the latest image.

2. **Environment Variables**: Ensure all required secrets are set in GitHub repository settings.

3. **Service Account Permissions**: The GitHub Actions service account needs proper permissions for Cloud Run and Cloud SQL.

## Testing Fixes Locally

Before deploying, test the app locally:

```bash
# Test FastAPI app imports
python -c "from app.web_ui.api import app; print('FastAPI app imported successfully')"

# Test with production environment
ENVIRONMENT=production SECRET_KEY=test DATABASE_URL=sqlite:///test.db python -c "from app.web_ui.api import app; print('Production mode works')"

# Run startup regression tests
pytest tests/integration/test_season_management_regression.py -v
pytest tests/unit/web_ui/test_fastapi_startup.py -v
```

## Prevention

### Required Tests
Add these tests to catch deployment issues early:

1. **FastAPI Startup Tests**: Verify app can start without side effects
2. **Environment Variable Tests**: Test with production settings
3. **Container Simulation Tests**: Test actual deployment scenarios

### Required GitHub Secrets
- `SECRET_KEY`: Session security (auto-generated)
- `DATABASE_URL`: Cloud SQL connection string
- `DB_PASSWORD`: Database password (if needed)

### Deployment Checklist
- [ ] All required secrets are set
- [ ] Migration job runs successfully before app deployment
- [ ] App container uses correct command (uvicorn, not CLI)
- [ ] Environment variables are properly set
- [ ] Health endpoint responds correctly

## Emergency Recovery

If deployment is completely broken:

```bash
# 1. Rollback to previous working revision
gcloud run services update-traffic basketball-stats --region=us-west1 --to-revisions=basketball-stats-00XXX-XXX=100

# 2. Or redeploy with known working configuration
gcloud run deploy basketball-stats \
  --image us-west1-docker.pkg.dev/basketball-stats-461220/basketball-stats/basketball-stats-app:latest \
  --region us-west1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars="ENVIRONMENT=production,SECRET_KEY=[SECRET],DATABASE_URL=[DB_URL]"
```

## Key Lessons Learned

1. **Container Args Matter**: Always check if the service is running the correct command
2. **Environment Consistency**: App and migration job need consistent DATABASE_URL
3. **Test Deployment Changes**: Changes to workflow or infrastructure should be tested
4. **Monitor Logs**: Cloud Run logs contain the real error details
5. **Separation of Concerns**: Web app startup should never run database migrations

## Contact and Resources

- **Cloud Run Documentation**: https://cloud.google.com/run/docs/troubleshooting
- **GitHub Actions Logs**: Use `gh run view [ID] --log` for detailed error information
- **Cloud Logging**: https://console.cloud.google.com/logs/ for real-time container logs
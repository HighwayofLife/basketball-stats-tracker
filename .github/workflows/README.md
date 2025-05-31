# GitHub Actions Workflows

This directory contains the CI/CD workflows for the Basketball Stats Tracker project.

## Workflows

### 1. PR Validation (`pr-validation.yml`)
**Trigger**: Pull requests to main/master branches

**Purpose**: Comprehensive validation of pull requests before merging

**Jobs**:
- **Docker Build Validation**: Ensures the Docker image can be built successfully
- **Code Quality**: Runs Ruff linter and formatter checks
- **Unit Tests**: Runs unit tests with coverage reporting
- **Integration Tests**: Runs integration tests with PostgreSQL
- **UI Tests**: Runs full-stack UI validation tests
- **Security Scan**: Runs Trivy vulnerability scanner
- **Test Results Summary**: Publishes combined test results

**Features**:
- Parallel job execution for faster feedback
- Test result publishing with detailed reports
- Coverage reporting to Codecov (if configured)
- Docker layer caching for faster builds
- Artifact uploads for test results and logs

### 2. Continuous Integration (`ci.yml`)
**Trigger**: Pushes to non-main branches

**Purpose**: Quick feedback for development branches

**Jobs**:
- **Quick Test Suite**: Runs linter and unit tests
- **Docker Build Test**: Validates Docker build

### 3. Build and Deploy (`deploy.yml`)
**Trigger**: 
- Pushes to main/master branches
- Manual workflow dispatch

**Purpose**: Production deployment pipeline

**Jobs**:
- **Validate Configuration**: Checks required GCP secrets
- **Build and Deploy**: 
  - Builds production Docker image
  - Pushes to Google Artifact Registry
  - Runs database migrations
  - Updates Cloud Run service

### 4. Test Report (`test-report.yml`)
**Trigger**: Completion of PR Validation or CI workflows

**Purpose**: Generate detailed test reports for pull requests

## Configuration

### Required Secrets

For PR validation and CI:
- None required (uses GitHub-hosted runners)

For deployment:
- `WIF_PROVIDER`: Workload Identity Federation provider
- `WIF_SERVICE_ACCOUNT`: Service account for GCP authentication

### Environment Variables

- `PYTHON_VERSION`: Python version for tests (default: 3.11)
- `PROJECT_ID`: GCP project ID (for deployment)
- `REGION`: GCP region (for deployment)

## Test Coverage

The workflows provide comprehensive test coverage:
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test database operations and service integrations
- **UI Tests**: Test the web interface functionality
- **Security Scanning**: Check for vulnerabilities in dependencies and code

## Optimization Features

1. **Caching**:
   - pip package caching
   - Docker layer caching with GitHub Actions cache
   
2. **Parallel Execution**:
   - Tests run in parallel where possible
   - Independent jobs for faster feedback

3. **Conditional Steps**:
   - Artifact uploads only on failure for debugging
   - Service cleanup in all cases

## Adding New Tests

To add new test categories:
1. Add test files to appropriate directories (`tests/unit/`, `tests/integration/`)
2. Tests will automatically be picked up by the workflows
3. For new test types, update the pytest commands in the workflows

## Troubleshooting

### Test Failures
- Check the test results in the GitHub Actions UI
- Download test artifacts for detailed logs
- Docker logs are captured on UI test failures

### Docker Build Issues
- Check the build logs in the Docker Build Validation job
- Ensure Dockerfile syntax is correct
- Verify build arguments are properly set

### Coverage Reports
- Coverage reports are generated for unit and integration tests
- Upload to Codecov requires `CODECOV_TOKEN` secret (optional)
#!/bin/bash
# Temporary script to run season migration using existing infrastructure

set -e

PROJECT_ID="basketball-stats-461220"
REGION="us-west1"
IMAGE_URL="us-west1-docker.pkg.dev/$PROJECT_ID/basketball-stats/basketball-stats-app:latest"

echo "🔄 Running season migration in production..."

# Temporarily update the migration job to run season migration instead of alembic
gcloud run jobs update basketball-stats-migrate \
  --image="$IMAGE_URL" \
  --args="python,scripts/migrate_seasons_production.py" \
  --region="$REGION" \
  --project="$PROJECT_ID"

echo "📦 Updated migration job configuration"

# Execute the migration
echo "🚀 Executing season migration..."
EXECUTION_NAME=$(gcloud run jobs execute basketball-stats-migrate \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format="get(metadata.name)")

echo "📋 Migration execution: $EXECUTION_NAME"

# Monitor the execution
echo "⏱️  Monitoring execution..."
for i in {1..60}; do
  STATUS=$(gcloud run jobs executions describe "$EXECUTION_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="get(status.conditions[0].type)")
  
  if [ "$STATUS" = "Completed" ]; then
    echo "✅ Season migration completed successfully!"
    break
  elif [ "$STATUS" = "Failed" ]; then
    echo "❌ Season migration failed!"
    echo "📋 Recent logs:"
    gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=basketball-stats-migrate" \
      --limit=20 \
      --format="table(timestamp,severity,textPayload)" \
      --project="$PROJECT_ID"
    exit 1
  fi
  
  echo "⏳ Waiting for migration to complete... ($i/60)"
  sleep 10
done

# Restore the original migration job configuration
echo "🔧 Restoring original migration job configuration..."
gcloud run jobs update basketball-stats-migrate \
  --image="$IMAGE_URL" \
  --args="alembic,upgrade,heads" \
  --region="$REGION" \
  --project="$PROJECT_ID"

echo "✅ Migration job restored to original configuration"
echo "🎉 Season migration process completed!"
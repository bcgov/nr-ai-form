#!/usr/bin/env bash
# Starts the client profile sync Container Apps Job (infra/client_profiles.tf) and waits for it.
# Run by .deployer_aca.yml after a successful "terragrunt apply". Skips quietly when the job
# does not exist (environments without client_profiles_json, i.e. everything except prod).
#
# Expected env vars: stack_prefix, app_env, repo_name  (az CLI already logged in)
set -euo pipefail

JOB_NAME="${stack_prefix}-${app_env}-cp-sync"
RG_NAME="${repo_name}-${app_env}"
export AZURE_EXTENSION_USE_DYNAMIC_INSTALL=yes_without_prompt

if ! az containerapp job show -n "$JOB_NAME" -g "$RG_NAME" --query name -o tsv > /dev/null 2>&1; then
  echo "No client profile sync job ($JOB_NAME) in $RG_NAME - skipping."
  exit 0
fi

echo "Starting $JOB_NAME..."
EXECUTION=$(az containerapp job start -n "$JOB_NAME" -g "$RG_NAME" --query name -o tsv | tr -d '\r')
echo "Execution: $EXECUTION"

# Job timeout is 600s; allow a little more for scheduling.
for _ in $(seq 1 72); do
  STATUS=$(az containerapp job execution show -n "$JOB_NAME" -g "$RG_NAME" --job-execution-name "$EXECUTION" \
    --query properties.status -o tsv | tr -d '\r')
  echo "  status: $STATUS"
  case "$STATUS" in
    Succeeded)
      echo "Client profiles synced to Cosmos."
      exit 0 ;;
    Failed|Stopped|Degraded)
      echo "::error::Client profile sync $EXECUTION ended with status $STATUS."
      echo "Logs: Log Analytics -> ContainerAppConsoleLogs_CL | where ContainerJobName_s == '$JOB_NAME'"
      exit 1 ;;
  esac
  sleep 10
done

echo "::error::Client profile sync $EXECUTION did not finish in time."
exit 1

#!/bin/bash

REPO_DIR="/home/bsc/MLOps_diploma_app"
LOG_FILE="webhook_redeploy.log"
TARGET_DIR="devops"

echo "$(date): Pulling latest changes from GitHub..." >> "$LOG_FILE"

cd "$REPO_DIR" && git fetch origin main >> "$LOG_FILE" 2>&1

# Check if there are changes in the devops directory
if git diff --name-only FETCH_HEAD HEAD | grep -q "^${TARGET_DIR}/"; then
    echo "$(date): Changes detected in the '${TARGET_DIR}' directory. Redeploying..." >> "$LOG_FILE"
    
    git reset --hard HEAD >> "$LOG_FILE" 2>&1
    git pull origin main >> "$LOG_FILE" 2>&1
    
    ./redeploy_model.sh >> "$LOG_FILE" 2>&1
    
    echo "$(date): Redeployment completed successfully." >> "$LOG_FILE"
else
    echo "$(date): No changes detected in the '${TARGET_DIR}' directory. Skipping redeployment." >> "$LOG_FILE"
fi
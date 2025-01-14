#!/bin/bash

# Variables
REPO_DIR="/home/bsc/MLOps_diploma_app"
LOG_FILE="/home/bsc/MLOps_diploma_app/devops/webhook_redeploy.log"
TARGET_DIR="devops"
REDEPLOY_SCRIPT="/home/bsc/MLOps_diploma_app/devops/redeploy_model.sh"

# Logging the start of the process
echo "$(date): Pulling latest changes from GitHub..." >> "$LOG_FILE"

# Navigate to the repo and fetch the latest changes
cd "$REPO_DIR" && git fetch origin main >> "$LOG_FILE" 2>&1

# Check for changes in the target directory
if [[ "$CHANGED_FILES" == *"$TARGET_DIR/"* ]]; then
    echo "$(date): Changes detected in the '${TARGET_DIR}' directory. Redeploying..." >> "$LOG_FILE"
    
    # Reset and pull the latest changes
    git reset --hard FETCH_HEAD >> "$LOG_FILE" 2>&1
    
    # Run the redeployment script
    bash "$REDEPLOY_SCRIPT" >> "$LOG_FILE" 2>&1
    
    echo "$(date): Redeployment completed successfully." >> "$LOG_FILE"
else
    echo "$(date): No changes detected in the '${TARGET_DIR}' directory. Skipping redeployment." >> "$LOG_FILE"
fi

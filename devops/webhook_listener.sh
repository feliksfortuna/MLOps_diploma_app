#!/bin/bash

# Variables
REPO_DIR="/home/bsc/MLOps_diploma_app"
LOG_FILE="webhook_redeploy.log"
TARGET_DIR="devops"
REDEPLOY_SCRIPT="./redeploy_model.sh"

# Logging the start of the process
echo "$(date): Pulling latest changes from GitHub..." >> "$LOG_FILE"

# Navigate to the repo and fetch the latest changes
cd "$REPO_DIR" && git fetch origin main >> "$LOG_FILE" 2>&1

# Get the latest commit hash on the remote branch
LATEST_REMOTE_COMMIT=$(git rev-parse origin/main)

# Get the latest local commit hash before pulling
LATEST_LOCAL_COMMIT=$(git rev-parse HEAD)

# Check for changes in the target directory between the two commits
if git diff --name-only "$LATEST_LOCAL_COMMIT" "$LATEST_REMOTE_COMMIT" | grep -q "^${TARGET_DIR}/"; then
    echo "$(date): Changes detected in the '${TARGET_DIR}' directory. Redeploying..." >> "$LOG_FILE"
    
    # Reset and pull the latest changes
    git reset --hard origin/main >> "$LOG_FILE" 2>&1
    
    # Run the redeployment script
    bash "$REDEPLOY_SCRIPT" >> "$LOG_FILE" 2>&1
    
    echo "$(date): Redeployment completed successfully." >> "$LOG_FILE"
else
    echo "$(date): No changes detected in the '${TARGET_DIR}' directory. Skipping redeployment." >> "$LOG_FILE"
fi

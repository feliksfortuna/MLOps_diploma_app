#!/bin/bash

# Get the absolute path of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$SCRIPT_DIR/webhook_redeploy.log"
MLOPS_DIR="$REPO_DIR/mlops"
COMMON_DIR="$REPO_DIR/common"
DEVOPS_DIR="$REPO_DIR/devops"
FRONTEND_DIR="$REPO_DIR/common/app-frontend"

# Logging function
log_message() {
    echo "$(date): $1" >> "$LOG_FILE"
}

# Error handling function
handle_error() {
    log_message "ERROR: $1"
    exit 1
}

# Navigate to the repo and fetch the latest changes
cd "$REPO_DIR" || handle_error "Failed to navigate to $REPO_DIR"

# Store the current commit hash before pulling
OLD_HASH=$(git rev-parse HEAD)

# Fetch and reset to origin/main to ensure we have the latest changes
git fetch origin main >> "$LOG_FILE" 2>&1 || handle_error "Failed to fetch from git"
git reset --hard origin/main >> "$LOG_FILE" 2>&1 || handle_error "Failed to reset to origin/main"

# Get new commit hash
NEW_HASH=$(git rev-parse HEAD)

# Get changed files between the old and new commit
CHANGED_FILES=$(git diff --name-only $OLD_HASH $NEW_HASH)
log_message "Changed files between $OLD_HASH and $NEW_HASH: $CHANGED_FILES"

# Function to check if directory has changes
has_changes() {
    local dir=$1
    echo "$CHANGED_FILES" | grep -q "^${dir}/"
}

# Handle MLOps directory changes
if has_changes "mlops"; then
    log_message "Changes detected in MLOps directory. Redeploying..."
    cd "$MLOPS_DIR" || handle_error "Failed to navigate to MLOps directory"
    
    # Kill existing processes
    pkill -f "gunicorn.*:5010" || true
    pkill -f "model_deploy_zero_downtime.sh" || true
    sleep 2

    # Start new processes
    nohup ./model_deploy_zero_downtime.sh > deployment_output.log 2>&1 &
    nohup gunicorn -w 1 -b 0.0.0.0:5010 model_server:app --timeout 300 > server.log 2>&1 &
    log_message "MLOps services redeployed"
fi

# Handle Common directory changes (Frontend)
if has_changes "common"; then
    log_message "Changes detected in Common directory. Redeploying frontends..."
    cd "$FRONTEND_DIR" || handle_error "Failed to navigate to Common directory"
    
    # Create separate directories for each frontend
    mkdir -p mlops-app devops-app
    
    # Deploy MLOps Frontend
    log_message "Redeploying MLOps frontend..."
    cd "$FRONTEND_DIR/mlops-app" || handle_error "Failed to navigate to MLOps app directory"
    rm -rf .next
    cp -r ../next-mlops/* .
    pm2 delete mlops 2>/dev/null || true
    NODE_ENV=production pm2 start "/home/bsc/.bun/bin/bun next start -p 3001" --name mlops
    
    # Deploy DevOps Frontend
    log_message "Redeploying DevOps frontend..."
    cd "$FRONTEND_DIR/devops-app" || handle_error "Failed to navigate to DevOps app directory"
    rm -rf .next
    cp -r ../next-devops/* .
    pm2 delete devops 2>/dev/null || true
    NODE_ENV=production pm2 start "/home/bsc/.bun/bin/bun next start -p 3002" --name devops
    
    log_message "Frontend services redeployed"
fi

# Handle DevOps directory changes
if has_changes "devops"; then
    log_message "Changes detected in DevOps directory. Redeploying..."
    cd "$DEVOPS_DIR" || handle_error "Failed to navigate to DevOps directory"
    bash ./redeploy_model.sh >> "$LOG_FILE" 2>&1
    log_message "DevOps services redeployed"
fi

log_message "Webhook processing completed"
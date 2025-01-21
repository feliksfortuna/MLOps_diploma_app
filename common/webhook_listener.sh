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
    # Force write to disk
    sync
}

# Error handling function
handle_error() {
    log_message "ERROR: $1"
    exit 1
}

# Function to ensure filesystem sync
force_sync() {
    sync
    sleep 2  # Give the filesystem time to catch up
}

# Function to ensure git operations are complete
wait_for_git() {
    local timeout=30
    local count=0
    while [ -f "$REPO_DIR/.git/index.lock" ] || [ -f "$REPO_DIR/.git/refs/heads/main.lock" ]; do
        sleep 1
        count=$((count + 1))
        if [ $count -ge $timeout ]; then
            handle_error "Git operation timed out after $timeout seconds"
        fi
        log_message "Waiting for git locks to clear... ($count seconds)"
    done
    force_sync
}

# Navigate to the repo
cd "$REPO_DIR" || handle_error "Failed to navigate to $REPO_DIR"

# Store the current commit hash
OLD_HASH=$(git rev-parse HEAD)
log_message "Current commit hash: $OLD_HASH"

# Fetch latest changes
log_message "Fetching latest changes..."
git fetch --prune origin >> "$LOG_FILE" 2>&1 || handle_error "Failed to fetch from git"
wait_for_git

# Reset to origin/main
log_message "Resetting to origin/main..."
git reset --hard origin/main >> "$LOG_FILE" 2>&1 || handle_error "Failed to reset to origin/main"
wait_for_git

# Get new commit hash and verify changes
NEW_HASH=$(git rev-parse HEAD)
log_message "New commit hash: $NEW_HASH"

# Get changed files between the old and new commit
CHANGED_FILES=$(git diff --name-only $OLD_HASH $NEW_HASH)
log_message "Changed files between $OLD_HASH and $NEW_HASH: $CHANGED_FILES"

# Function to check if directory has changes
has_changes() {
    local dir=$1
    echo "$CHANGED_FILES" | grep -q "^${dir}/"
}

# Function to ensure directory content is ready
verify_changes() {
    local dir=$1
    local max_attempts=10
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if git diff --quiet HEAD; then
            force_sync
            return 0
        fi
        log_message "Waiting for changes to settle in $dir (attempt $attempt)"
        sleep 2
        ((attempt++))
    done
    
    handle_error "Changes in $dir did not settle after $max_attempts attempts"
}

# Handle MLOps directory changes
if has_changes "mlops"; then
    log_message "Changes detected in MLOps directory. Waiting for changes to sync..."
    verify_changes "$MLOPS_DIR"
    
    cd "$MLOPS_DIR" || handle_error "Failed to navigate to MLOps directory"
    force_sync  # Ensure files are synced before deployment
    
    log_message "Stopping existing MLOps services..."
    pkill -f "gunicorn.*:5010" || true
    pkill -f "model_deploy_zero_downtime.sh" || true
    sleep 5  # Give processes time to stop completely

    log_message "Starting MLOps services..."
    nohup ./model_deploy_zero_downtime.sh > deployment_output.log 2>&1 &
    sleep 10  # Give the deployment script more time to initialize
    
    # Verify deployment script is running
    if ! pgrep -f "model_deploy_zero_downtime.sh" > /dev/null; then
        handle_error "Deployment script failed to start"
    fi
    
    nohup gunicorn -w 1 -b 0.0.0.0:5010 model_server:app --timeout 300 > server.log 2>&1 &
    sleep 5  # Give gunicorn time to start
    
    # Verify gunicorn is running
    if ! pgrep -f "gunicorn.*:5010" > /dev/null; then
        handle_error "Gunicorn failed to start"
    fi
    
    log_message "MLOps services redeployed successfully"
fi

# Handle Frontend changes
if has_changes "common"; then
    log_message "Changes detected in Common directory. Waiting for changes to sync..."
    verify_changes "$COMMON_DIR"
    
    cd "$FRONTEND_DIR" || handle_error "Failed to navigate to Frontend directory"
    force_sync  # Ensure files are synced before deployment
    
    log_message "Stopping existing frontend services..."
    pm2 delete mlops 2>/dev/null || true
    pm2 delete devops 2>/dev/null || true
    sleep 3  # Give PM2 time to clean up

    # MLOps Frontend
    log_message "Deploying MLOps frontend..."
    # rm -rf mlops-app
    # mkdir -p mlops-app/.next
    # cp -r .next-mlops/* mlops-app/.next/ || handle_error "Failed to copy MLOps build files"
    force_sync
    
    # cd mlops-app || handle_error "Failed to navigate to MLOps app directory"
    NODE_ENV=production pm2 start "/home/bsc/.bun/bin/bun next start ./.next-mlops -p 3001" --name mlops
    sleep 3
    
    # Verify MLOps frontend is running
    if ! pm2 pid mlops > /dev/null; then
        handle_error "MLOps frontend failed to start"
    fi

    # DevOps Frontend
    cd "$FRONTEND_DIR" || handle_error "Failed to navigate back to Frontend directory"
    log_message "Deploying DevOps frontend..."
    # rm -rf devops-app
    # mkdir -p devops-app/.next
    # cp -r .next-devops/* devops-app/.next/ || handle_error "Failed to copy DevOps build files"
    force_sync
    
    # cd devops-app || handle_error "Failed to navigate to DevOps app directory"
    NODE_ENV=production pm2 start "/home/bsc/.bun/bin/bun next start ./.next-devops -p 3002" --name devops
    sleep 3
    
    # Verify DevOps frontend is running
    if ! pm2 pid devops > /dev/null; then
        handle_error "DevOps frontend failed to start"
    fi
    
    log_message "Frontend services redeployed successfully"
fi

# Handle DevOps directory changes
if has_changes "devops"; then
    log_message "Changes detected in DevOps directory. Waiting for changes to sync..."
    verify_changes "$DEVOPS_DIR"
    
    cd "$DEVOPS_DIR" || handle_error "Failed to navigate to DevOps directory"
    force_sync  # Ensure files are synced before deployment
    
    bash ./redeploy_model.sh >> "$LOG_FILE" 2>&1
    sleep 5  # Give the deployment time to complete
    
    log_message "DevOps services redeployed successfully"
fi

log_message "Webhook processing completed successfully"
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

# Function to wait for git operations to complete
wait_for_git() {
    local max_attempts=30
    local attempt=1
    while [[ -f "$REPO_DIR/.git/index.lock" ]] && [[ $attempt -le $max_attempts ]]; do
        log_message "Waiting for git operations to complete (attempt $attempt)"
        sleep 1
        ((attempt++))
    done
}

# Function to verify directory contents
verify_directory() {
    local dir=$1
    local required_file=$2
    local max_attempts=30
    local attempt=1
    
    while [[ ! -f "$dir/$required_file" ]] && [[ $attempt -le $max_attempts ]]; do
        log_message "Waiting for $required_file in $dir (attempt $attempt)"
        sleep 1
        ((attempt++))
    done
    
    if [[ ! -f "$dir/$required_file" ]]; then
        handle_error "Required file $required_file not found in $dir after $max_attempts attempts"
    fi
}

# Navigate to the repo and fetch the latest changes
cd "$REPO_DIR" || handle_error "Failed to navigate to $REPO_DIR"

# Store the current commit hash before pulling
OLD_HASH=$(git rev-parse HEAD)

# Fetch and reset to origin/main to ensure we have the latest changes
git fetch origin main >> "$LOG_FILE" 2>&1 || handle_error "Failed to fetch from git"
wait_for_git
git reset --hard origin/main >> "$LOG_FILE" 2>&1 || handle_error "Failed to reset to origin/main"
wait_for_git

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
    sleep 5  # Give the deployment script time to initialize
    nohup gunicorn -w 1 -b 0.0.0.0:5010 model_server:app --timeout 300 > server.log 2>&1 &
    log_message "MLOps services redeployed"
fi

# Handle Common directory changes (Frontend)
if has_changes "common"; then
    log_message "Changes detected in Common directory. Redeploying frontends..."
    cd "$FRONTEND_DIR" || handle_error "Failed to navigate to Common directory"
    
    # Stop existing PM2 processes
    pm2 delete mlops 2>/dev/null || true
    pm2 delete devops 2>/dev/null || true
    sleep 2

    # Create separate directories for each frontend
    rm -rf mlops-app devops-app
    mkdir -p mlops-app devops-app
    
    # Deploy MLOps Frontend
    log_message "Deploying MLOps frontend..."
    cd "$FRONTEND_DIR/mlops-app" || handle_error "Failed to navigate to MLOps app directory"
    mkdir -p .next
    cp -r ../next-mlops/* .next/ || handle_error "Failed to copy MLOps build files"
    verify_directory ".next" "build-manifest.json"
    
    log_message "Starting MLOps frontend..."
    NODE_ENV=production pm2 start "/home/bsc/.bun/bin/bun next start -p 3001" --name mlops
    sleep 3
    
    # Deploy DevOps Frontend
    log_message "Deploying DevOps frontend..."
    cd "$FRONTEND_DIR/devops-app" || handle_error "Failed to navigate to DevOps app directory"
    mkdir -p .next
    cp -r ../next-devops/* .next/ || handle_error "Failed to copy DevOps build files"
    verify_directory ".next" "build-manifest.json"
    
    log_message "Starting DevOps frontend..."
    NODE_ENV=production pm2 start "/home/bsc/.bun/bin/bun next start -p 3002" --name devops
    sleep 3
    
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
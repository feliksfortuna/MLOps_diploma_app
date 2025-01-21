#!/bin/bash

# Get the absolute path of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$SCRIPT_DIR/webhook_redeploy.log"
MLOPS_DIR="$REPO_DIR/mlops"
COMMON_DIR="$REPO_DIR/common"
DEVOPS_DIR="$REPO_DIR/devops"

# Logging function
log_message() {
    echo "$(date): $1" >> "$LOG_FILE"
    sync
}

# Error handling function
handle_error() {
    log_message "ERROR: $1"
    exit 1
}

# Function to check if directory has changes
has_changes() {
    local dir=$1
    git diff --name-only HEAD@{1} HEAD | grep -q "^${dir}/"
}

# Check if webhook server itself changed
if has_changes "common"; then
    log_message "Webhook scripts changed, restarting webhook server..."
    pkill -f "python.*webhook_server.py" || true
    cd "$SCRIPT_DIR" || handle_error "Failed to navigate to script directory"
    nohup python webhook_server.py > webhook_server.log 2>&1 &
    log_message "Webhook server restarted"


    # Log the changes
    log_message "Changes detected in Common directory. Waiting for changes to sync..."
    verify_changes "$COMMON_DIR"

    # Stop existing frontend services
    log_message "Stopping existing frontend services..."
    pm2 delete mlops 2>/dev/null || true
    pm2 delete devops 2>/dev/null || true
    sleep 3  # Allow PM2 to clean up

    # MLOps Frontend Deployment
    log_message "Deploying MLOps frontend..."
    cd "$COMMON_DIR/mlops-frontend" || handle_error "Failed to navigate to MLOps app directory"
    force_sync

    # Start MLOps Frontend
    pm2 start "/home/bsc/.bun/bin/bun next start -p 3001" --name mlops

    # Verify MLOps frontend is running
    if ! pm2 pid mlops > /dev/null; then
        handle_error "MLOps frontend failed to start"
    fi

    # DevOps Frontend Deployment
    log_message "Deploying DevOps frontend..."
    cd "$COMMON_DIR/devops" || handle_error "Failed to navigate to DevOps app directory"
    force_sync

    # Start DevOps Frontend
    pm2 start "/home/bsc/.bun/bin/bun next start -p 3002" --name devops

    # Verify DevOps frontend is running
    if ! pm2 pid devops > /dev/null; then
        handle_error "DevOps frontend failed to start"
    fi

    log_message "Frontend services redeployed successfully"
fi

# Handle MLOps directory changes
if has_changes "mlops"; then
    log_message "Changes detected in MLOps directory..."
    
    cd "$MLOPS_DIR" || handle_error "Failed to navigate to MLOps directory"
    
    log_message "Stopping existing MLOps services..."
    pkill -f "gunicorn.*:5010" || true
    pkill -f "model_deploy_zero_downtime.sh" || true
    sleep 5

    log_message "Starting MLOps services..."
    nohup ./model_deploy_zero_downtime.sh > deployment_output.log 2>&1 &
    sleep 10
    
    if ! pgrep -f "model_deploy_zero_downtime.sh" > /dev/null; then
        handle_error "Deployment script failed to start"
    fi
    
    nohup gunicorn -w 1 -b 0.0.0.0:5010 model_server:app --timeout 300 > server.log 2>&1 &
    sleep 5
    
    if ! pgrep -f "gunicorn.*:5010" > /dev/null; then
        handle_error "Gunicorn failed to start"
    fi
    
    log_message "MLOps services redeployed successfully"
fi

# Handle DevOps directory changes
if has_changes "devops"; then
    log_message "Changes detected in DevOps directory..."
    cd "$DEVOPS_DIR" || handle_error "Failed to navigate to DevOps directory"
    bash ./redeploy_model.sh >> "$LOG_FILE" 2>&1
    log_message "DevOps services redeployed"
fi

log_message "Webhook processing completed successfully"
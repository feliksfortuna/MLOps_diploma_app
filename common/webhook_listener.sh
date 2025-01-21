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


    # log_message "Changes detected in Common directory. Waiting for changes to sync..."
#     verify_changes "$COMMON_DIR"
    
#     cd "$FRONTEND_DIR" || handle_error "Failed to navigate to Frontend directory"
#     force_sync  # Ensure files are synced before deployment
    
#     log_message "Stopping existing frontend services..."
#     pm2 delete mlops 2>/dev/null || true
#     pm2 delete devops 2>/dev/null || true
#     sleep 3  # Give PM2 time to clean up

#     # MLOps Frontend
#     log_message "Deploying MLOps frontend..."
#     # Create fresh directories for MLOps
#     rm -rf mlops-app
#     mkdir -p mlops-app/.next
    
#     # Copy the entire pre-built directory including static files
#     cp -r .next-mlops/* mlops-app/.next || handle_error "Failed to copy MLOps build files"
#     cp -r .next-mlops/.next mlops-app/ || handle_error "Failed to copy MLOps .next directory"
#     cp -r .next-mlops/public mlops-app/ || handle_error "Failed to copy MLOps public directory"
#     force_sync
    
#     cd mlops-app || handle_error "Failed to navigate to MLOps app directory"
#     NODE_ENV=production pm2 start "/home/bsc/.bun/bin/bun next start -p 3001" --name mlops
#     sleep 3
    
#     # Verify MLOps frontend is running
#     if ! pm2 pid mlops > /dev/null; then
#         handle_error "MLOps frontend failed to start"
#     fi

#     # DevOps Frontend
#     cd "$FRONTEND_DIR" || handle_error "Failed to navigate back to Frontend directory"
#     log_message "Deploying DevOps frontend..."
#     # Create fresh directories for DevOps
#     rm -rf devops-app
#     mkdir -p devops-app
    
#     # Copy the entire pre-built directory including static files
#     cp -r .next-devops/* devops-app/ || handle_error "Failed to copy DevOps build files"
#     cp -r .next-devops/.next devops-app/ || handle_error "Failed to copy DevOps .next directory"
#     cp -r .next-devops/public devops-app/ || handle_error "Failed to copy DevOps public directory"
#     force_sync
    
#     cd devops-app || handle_error "Failed to navigate to DevOps app directory"
#     NODE_ENV=production pm2 start "/home/bsc/.bun/bin/bun next start -p 3002" --name devops
#     sleep 3
    
#     # Verify DevOps frontend is running
#     if ! pm2 pid devops > /dev/null; then
#         handle_error "DevOps frontend failed to start"
#     fi
    
#     log_message "Frontend services redeployed successfully"
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
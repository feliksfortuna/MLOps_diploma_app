#!/bin/bash

# Get the absolute path of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$SCRIPT_DIR/webhook_redeploy.log"
MLOPS_DIR="$REPO_DIR/mlops"
COMMON_DIR="$REPO_DIR/common"
DEVOPS_DIR="$REPO_DIR/devops"

WEBHOOK_SERVER="http://127.0.0.1:8000"

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

# -----------------------------------------------------------------------------
# Helper functions for MLOps and DevOps backend deployments
# so we can reuse them.
# -----------------------------------------------------------------------------
redeploy_mlops_backend() {
    log_message "Redeploying MLOps backend..."
    cd "$MLOPS_DIR" || handle_error "Failed to navigate to MLOps directory"

    local start_time=$(date +%s)

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
    
    nohup gunicorn -w 2 -b 0.0.0.0:5010 model_server:app --timeout 300 > server.log 2>&1 &
    sleep 5
    
    if ! pgrep -f "gunicorn.*:5010" > /dev/null; then
        handle_error "Gunicorn failed to start"
    fi

    log_message "MLOps backend redeployed successfully"

    # Calculate and post MLOps deployment time
    local end_time=$(date +%s)
    local elapsed=$(( end_time - start_time ))
    log_message "MLOps deploy time: ${elapsed}s"

    # POST to the webhook server to record MLOps deploy time
    curl -X POST "${WEBHOOK_SERVER}/observe_mlops_deploy?time=${elapsed}" \
         --silent --output /dev/null || log_message "Failed to post MLOps deploy time"
}

redeploy_devops_backend() {
    log_message "Redeploying DevOps backend..."
    cd "$DEVOPS_DIR" || handle_error "Failed to navigate to DevOps directory"

    local start_time=$(date +%s)

    nohup ./redeploy_model.sh > redeploy.log 2>&1 &

    wait_for_redeploy() {
      for i in {1..20}; do
        # If the script is done, break
        if ! pgrep -f "redeploy_model.sh" > /dev/null; then
          break
        fi
        sleep 2
      done
    }
    wait_for_redeploy

    log_message "DevOps backend redeployed"

    local end_time=$(date +%s)
    local elapsed=$(( end_time - start_time ))
    log_message "DevOps deploy time: ${elapsed}s"

    # POST to the webhook server to record DevOps deploy time
    curl -X POST "${WEBHOOK_SERVER}/observe_devops_deploy?time=${elapsed}" \
         --silent --output /dev/null || log_message "Failed to post DevOps deploy time"
}

# -----------------------------------------------------------------------------
# Main Script
# -----------------------------------------------------------------------------

# Check if Common changed
if has_changes "common"; then
    log_message "Changes detected in Common directory..."

    # 1) Restart the Webhook Server via systemd
    log_message "Restarting webhook server..."
    SUDO_PASSWORD=$(cat /home/bsc/.sudo_password)
    if echo "$SUDO_PASSWORD" | sudo -S systemctl restart myservice; then
        log_message "Successfully restarted myservice via systemctl."
    else
        log_message "Failed to restart myservice."
    fi

    # 2) Stop existing frontends
    log_message "Stopping existing frontend services..."
    pm2 delete mlops 2>/dev/null || true
    pm2 delete devops 2>/dev/null || true
    sleep 3

    # 3) Redeploy MLOps Frontend
    log_message "Deploying MLOps frontend..."
    cd "$COMMON_DIR/mlops-frontend" || handle_error "Failed to navigate to MLOps app directory"
    force_sync
    pm2 start "/home/bsc/.bun/bin/bun next start -p 3001" --name mlops
    if ! pm2 pid mlops > /dev/null; then
        handle_error "MLOps frontend failed to start"
    fi

    # 4) Redeploy DevOps Frontend
    log_message "Deploying DevOps frontend..."
    cd "$COMMON_DIR/devops-frontend" || handle_error "Failed to navigate to DevOps app directory"
    force_sync
    pm2 start "/home/bsc/.bun/bin/bun next start -p 3002" --name devops
    if ! pm2 pid devops > /dev/null; then
        handle_error "DevOps frontend failed to start"
    fi

    # 5) Also redeploy MLOps backend
    redeploy_mlops_backend

    # 6) Also redeploy DevOps backend
    redeploy_devops_backend

    log_message "All common-based redeployments done successfully"
fi

# Handle MLOps directory changes (if they didn't come from common)
if has_changes "mlops"; then
    log_message "Changes detected in MLOps directory..."
    redeploy_mlops_backend
fi

# Handle DevOps directory changes (if they didn't come from common)
if has_changes "devops"; then
    log_message "Changes detected in DevOps directory..."
    redeploy_devops_backend
fi

log_message "Webhook processing completed successfully"
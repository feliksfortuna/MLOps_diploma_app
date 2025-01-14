#!/bin/bash

MODEL_URI="models:/Race prediction@production"
PORT_OLD=5006
PORT_NEW=5007
LOG_DIR="/tmp/mlflow_logs"
MODEL_FILE="${LOG_DIR}/current_model.txt"

export MLFLOW_TRACKING_URI="http://seito.lavbic.net:5000"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to get current model metadata using mlflow CLI
get_model_metadata() {
    # Using serve command instead of predict to be more reliable
    local output
    output=$(mlflow models serve --help 2>&1 | grep -A2 "MODEL_URI")
    if [ -n "$output" ]; then
        echo "$output"
    else
        return 1
    fi
}

# Function to start mlflow models serve on a given port
start_mlflow_server() {
    local port="$1"
    local log_file="${LOG_DIR}/mlflow_${port}.log"
    local pid_file="${LOG_DIR}/mlflow_${port}.pid"
    
    echo "Starting mlflow models serve on port $port..."
    
    # Print debug info
    echo "Debug: Starting server with following parameters:"
    echo "MODEL_URI: $MODEL_URI"
    echo "Port: $port"
    echo "Log file: $log_file"
    
    # Start the server with full error output
    mlflow models serve -m "$MODEL_URI" \
        --host "0.0.0.0" \
        --port "$port" \
        --no-conda > "$log_file" 2>&1 &
    
    local pid=$!
    echo "Debug: Initial PID: $pid"
    
    # Wait a moment for the process to start
    sleep 5
    
    # Check process and log file for errors
    if ! ps -p $pid > /dev/null; then
        echo "Debug: Process $pid is not running"
        echo "Last few lines of log file:"
        tail -n 10 "$log_file"
        return 1
    fi
    
    # Check if port is actually being used
    if ! nc -z localhost "$port"; then
        echo "Debug: Port $port is not in use"
        echo "Last few lines of log file:"
        tail -n 10 "$log_file"
        kill $pid 2>/dev/null || true
        return 1
    fi
    
    echo $pid > "$pid_file"
    echo $pid
    return 0
}

# Function to stop mlflow server
stop_mlflow_server() {
    local port=$1
    local pid_file="${LOG_DIR}/mlflow_${port}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null; then
            echo "Stopping mlflow server on port $port (PID: $pid)..."
            kill $pid
            sleep 2
            # Force kill if still running
            if ps -p $pid > /dev/null; then
                kill -9 $pid
            fi
        fi
        rm "$pid_file"
    fi
}

update_nginx_proxy() {
    local port="$1"
    echo "Updating Nginx to route traffic to port $port..."
    
    # Use sudo with explicit command paths
    if sudo /usr/bin/sed -i "s/proxy_pass http:\/\/localhost:[0-9]*/proxy_pass http:\/\/localhost:$port/" /etc/nginx/sites-available/mlflow && \
       sudo /usr/sbin/nginx -t && \
       sudo /bin/systemctl reload nginx; then
        echo "Nginx updated and reloaded successfully."
        return 0
    else
        echo "Failed to reload Nginx. Keeping the current server."
        return 1
    fi
}

# Wait the server to be ready
wait_for_server() {
    local port="$1"
    local max_retries=30
    local retries=0
    local log_file="${LOG_DIR}/mlflow_${port}.log"
    
    echo "Waiting for mlflow server to start on port ${port}..."
    while [ $retries -lt $max_retries ]; do
        if ! ps -p $(cat "${LOG_DIR}/mlflow_${port}.pid" 2>/dev/null) > /dev/null 2>&1; then
            echo "Debug: MLflow process is not running"
            echo "Last few lines of log file:"
            tail -n 10 "$log_file"
            return 1
        fi
        
        if nc -z localhost "${port}"; then
            echo "Debug: Port ${port} is now available"
            if curl -s "http://localhost:${port}/ping" > /dev/null 2>&1; then
                echo "Mlflow server started successfully on port ${port}."
                return 0
            else
                echo "Debug: Server not responding to ping"
            fi
        fi
        retries=$((retries + 1))
        sleep 2
    done
    
    echo "Error: Mlflow server failed to start on port ${port}."
    echo "Full log file contents:"
    cat "$log_file"
    return 1
}

# Cleanup function
cleanup() {
    echo "Cleaning up servers..."
    stop_mlflow_server $PORT_OLD
    stop_mlflow_server $PORT_NEW
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGINT SIGTERM

# Start the initial server
echo "Starting initial deployment..."
PID_OLD=$(start_mlflow_server $PORT_OLD)
if [ -z "$PID_OLD" ] || ! wait_for_server $PORT_OLD; then
    echo "Initial server failed to start. Exiting."
    cleanup
    exit 1
fi

if ! update_nginx_proxy $PORT_OLD; then
    echo "Failed to update Nginx configuration. Exiting."
    cleanup
    exit 1
fi

# Store initial model metadata
get_model_metadata > "$MODEL_FILE"
echo "Initial model deployed successfully."

# Main loop
while true; do
    echo "Checking for model updates..."
    
    # Get current model metadata
    NEW_METADATA=$(get_model_metadata)
    OLD_METADATA=$(cat "$MODEL_FILE")
    
    # Compare with stored metadata
    if [ "$NEW_METADATA" != "$OLD_METADATA" ]; then
        echo "Model update detected."
        
        # Toggle ports for new deployment
        if [ "$PORT_OLD" -eq 5006 ]; then
            PORT_NEW=5007
        else
            PORT_NEW=5006
        fi
        
        # Start new server
        PID_NEW=$(start_mlflow_server $PORT_NEW)
        if [ -n "$PID_NEW" ] && wait_for_server $PORT_NEW; then
            if update_nginx_proxy $PORT_NEW; then
                echo "Switching traffic to new server on port $PORT_NEW."
                stop_mlflow_server $PORT_OLD
                echo "Old server on port $PORT_OLD stopped."
                PORT_OLD=$PORT_NEW
                PID_OLD=$PID_NEW
                echo "$NEW_METADATA" > "$MODEL_FILE"
                echo "Updated to new model version"
            else
                echo "Failed to update Nginx. Stopping new server."
                stop_mlflow_server $PORT_NEW
            fi
        else
            echo "New server failed to start. Keeping the old server."
            stop_mlflow_server $PORT_NEW
        fi
    else
        echo "No model updates detected."
    fi
    
    sleep 60
done

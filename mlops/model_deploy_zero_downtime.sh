#!/bin/bash

MODEL_URI="models:/Race prediction@production"
PORT_OLD=5006
PORT_NEW=5007
LOG_DIR="/tmp/mlflow_logs"
MODEL_FILE="${LOG_DIR}/current_model.txt"
VENV_PATH="/home/bsc/mlflow-env"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export MLFLOW_TRACKING_URI="http://seito.lavbic.net:5000"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to setup environment
setup_environment() {
    echo "Setting up Python environment..."
    if [ ! -d "$VENV_PATH" ]; then
        echo "Error: Virtual environment not found at $VENV_PATH"
        return 1
    fi
    
    source "${VENV_PATH}/bin/activate"
    
    if ! python -c "import mlflow" 2>/dev/null; then
        echo "Error: MLflow not found in Python environment"
        return 1
    fi
    
    return 0
}

# Function to get current model metadata using Python script
get_model_metadata() {
    python "${SCRIPT_DIR}/check_model_version.py"
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
    echo "Python executable: $(which python)"
    echo "MLflow version: $(python -c 'import mlflow; print(mlflow.__version__)')"
    
    # Start the server with worker timeout and retries
    GUNICORN_CMD_ARGS="--timeout 120 --workers 1 --threads 4 --backlog 2048 --max-requests 1000 --max-requests-jitter 50" \
    mlflow models serve -m "$MODEL_URI" \
        --host "0.0.0.0" \
        --port "$port" \
        --no-conda > "$log_file" 2>&1 &
    
    local pid=$!
    echo "Debug: Initial PID: $pid"
    
    # Wait for the process to start
    sleep 10
    
    # Check process and log file for errors
    if ! ps -p $pid > /dev/null; then
        echo "Debug: Process $pid is not running"
        echo "Error in log file:"
        tail -n 20 "$log_file"
        return 1
    fi
    
    # Check if port is actually being used
    if ! nc -z localhost "$port"; then
        echo "Debug: Port $port is not in use"
        echo "Error in log file:"
        tail -n 20 "$log_file"
        kill $pid 2>/dev/null || true
        return 1
    fi
    
    # Additional check - try to get a response from the server
    sleep 5
    if ! curl -s "http://localhost:${port}/ping" > /dev/null; then
        echo "Debug: Server not responding to ping"
        echo "Error in log file:"
        tail -n 20 "$log_file"
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

# Function to update nginx proxy
update_nginx_proxy() {
    local port="$1"
    echo "Updating Nginx to route traffic to port $port..."
    
    if echo "$SUDO_PASSWORD" | sudo -S /usr/bin/sed -i "s/proxy_pass http:\/\/localhost:[0-9]*/proxy_pass http:\/\/localhost:$port/" /etc/nginx/sites-available/mlflow && \
       echo "$SUDO_PASSWORD" | sudo -S /usr/sbin/nginx -t && \
       echo "$SUDO_PASSWORD" | sudo -S /bin/systemctl reload nginx; then
        echo "Nginx updated and reloaded successfully."
        return 0
    else
        echo "Failed to reload Nginx. Keeping the current server."
        return 1
    fi
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

# Setup Python environment
if ! setup_environment; then
    echo "Failed to set up Python environment. Exiting."
    exit 1
fi

# Start the initial server
echo "Starting initial deployment..."
PID_OLD=$(start_mlflow_server $PORT_OLD)
if [ -z "$PID_OLD" ]; then
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
    if [ $? -ne 0 ]; then
        echo "Failed to get model metadata. Will retry in next iteration."
        sleep 60
        continue
    fi
    
    OLD_METADATA=$(cat "$MODEL_FILE")
    
    # Compare with stored metadata
    if [ "$NEW_METADATA" != "$OLD_METADATA" ]; then
        echo "Model update detected."
        echo "New metadata: $NEW_METADATA"
        echo "Old metadata: $OLD_METADATA"
        
        # Toggle ports for new deployment
        if [ "$PORT_OLD" -eq 5006 ]; then
            PORT_NEW=5007
        else
            PORT_NEW=5006
        fi
        
        # Start new server
        PID_NEW=$(start_mlflow_server $PORT_NEW)
        if [ -n "$PID_NEW" ]; then
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
    
    sleep 20
done
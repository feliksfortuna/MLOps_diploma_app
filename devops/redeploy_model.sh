#!/bin/bash

# Variables
PORT=15000
APP="model_server:app"
LOG_FILE="/home/bsc/MLOps_diploma_app/devops/server.log"

# Function to stop existing Gunicorn process
stop_server() {
    echo "Stopping existing Gunicorn server on port $PORT..."
    pid=$(lsof -t -i:$PORT -sTCP:LISTEN)
    if [ -n "$pid" ]; then
        kill -15 "$pid" && echo "Server stopped."
        sleep 2
    else
        echo "No server running on port $PORT."
    fi
    
    # Double-check if the process is still running and force kill if necessary
    if nc -z localhost $PORT; then
        echo "Port $PORT is still in use. Forcibly killing the process..."
        pkill -f "gunicorn -w 1 -b 0.0.0.0:$PORT" && echo "Forcibly killed the server."
        sleep 2
    fi
}

# Function to start Gunicorn server
start_server() {
    echo "Starting Gunicorn server on port $PORT..."
    nohup gunicorn -w 1 -b 0.0.0.0:$PORT --chdir /home/bsc/MLOps_diploma_app/devops $APP > "$LOG_FILE" 2>&1 &
    sleep 2
    if nc -z localhost $PORT; then
        echo "Server started successfully. Logs are being written to $LOG_FILE"
    else
        echo "Failed to start the server."
    fi
}

# Main script logic
stop_server
start_server

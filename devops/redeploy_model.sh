#!/bin/bash

# Variables
PORT=6000
APP="model_server:app"
LOG_FILE="server.log"

# Function to stop existing Gunicorn process
stop_server() {
    echo "Stopping existing Gunicorn server on port $PORT..."
    pid=$(lsof -t -i:$PORT -sTCP:LISTEN)
    if [ -n "$pid" ]; then
        kill -15 "$pid" && echo "Server stopped."
    else
        echo "No server running on port $PORT."
    fi
}

# Function to start Gunicorn server
start_server() {
    echo "Starting Gunicorn server on port $PORT..."
    nohup gunicorn -w 1 -b 0.0.0.0:$PORT $APP > "$LOG_FILE" 2>&1 &
    sleep 2  # Wait briefly to ensure the server starts
    if nc -z localhost $PORT; then
        echo "Server started successfully. Logs are being written to $LOG_FILE"
    else
        echo "Failed to start the server."
    fi
}

# Main script logic
stop_server
start_server

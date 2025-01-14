#!/bin/bash

# Variables
PORT=6000
APP="model_server:app"
LOG_FILE="server.log"

# Function to stop existing Gunicorn process
stop_server() {
    echo "Stopping existing Gunicorn server on port $PORT..."
    pkill -f "gunicorn -w 1 -b 0.0.0.0:$PORT" && echo "Server stopped."
}

# Function to start Gunicorn server
start_server() {
    echo "Starting Gunicorn server on port $PORT..."
    nohup gunicorn -w 1 -b 0.0.0.0:$PORT $APP > $LOG_FILE 2>&1 &
    echo "Server started. Logs are being written to $LOG_FILE"
}

# Main script logic
stop_server
start_server

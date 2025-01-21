# webhook_server.py
from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import os
import logging
from logging.handlers import RotatingFileHandler
import time

# Set up logging
logging.basicConfig(
    handlers=[
        RotatingFileHandler(
            'webhook_server.log',
            maxBytes=10000000,  # 10MB
            backupCount=5
        )
    ],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": [
    "http://localhost",
    "http://seito.lavbic.net",
    "https://ultimate-krill-officially.ngrok-free.app"
]}})

def update_repo():
    """First phase: Just update the repository"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        repo_dir = os.path.dirname(current_dir)
        
        # Execute git commands directly
        subprocess.run(['git', 'fetch', '--prune', 'origin'], 
                     cwd=repo_dir, check=True)
        subprocess.run(['git', 'reset', '--hard', 'origin/main'], 
                     cwd=repo_dir, check=True)
        return True
    except Exception as e:
        logging.error(f"Error updating repository: {str(e)}", exc_info=True)
        return False

def restart_services():
    """Second phase: Restart services with new code"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, 'webhook_listener.sh')
        
        if not os.access(script_path, os.X_OK):
            os.chmod(script_path, 0o755)
        
        subprocess.Popen(
            [script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=current_dir
        )
        return True
    except Exception as e:
        logging.error(f"Error restarting services: {str(e)}", exc_info=True)
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Phase 1: Update repository
        logging.info("Phase 1: Updating repository")
        if not update_repo():
            return jsonify({
                'status': 'error',
                'message': 'Failed to update repository'
            }), 500
        
        # Small delay to ensure filesystem sync
        time.sleep(2)
        
        # Phase 2: Restart services with new code
        logging.info("Phase 2: Restarting services")
        if not restart_services():
            return jsonify({
                'status': 'error',
                'message': 'Failed to restart services'
            }), 500
        
        return jsonify({
            'status': 'success',
            'message': 'Webhook processed successfully'
        }), 200
        
    except Exception as e:
        logging.error(f"Error in webhook endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    logging.info("Starting webhook server")
    app.run(host='0.0.0.0', port=8000)
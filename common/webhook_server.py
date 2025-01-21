# webhook_server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import logging
from logging.handlers import RotatingFileHandler

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

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Get absolute path to the webhook listener script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, 'webhook_listener.sh')
        
        # Make webhook_listener.sh executable if it isn't already
        if not os.access(script_path, os.X_OK):
            os.chmod(script_path, 0o755)
            logging.info(f"Made {script_path} executable")
        
        # Execute the webhook listener script
        logging.info("Starting webhook listener script")
        subprocess.Popen(
            [script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=current_dir
        )
        
        logging.info("Webhook listener script started successfully")
        return jsonify({
            'status': 'success',
            'message': 'Webhook received and processing started'
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
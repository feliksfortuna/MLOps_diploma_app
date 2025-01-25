from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import os
import logging
from logging.handlers import RotatingFileHandler
from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log, RetryError

# Configuration
LOG_FILE = os.getenv('WEBHOOK_LOG_FILE', 'webhook_server.log')
MAX_RETRIES = int(os.getenv('WEBHOOK_MAX_RETRIES', 5))
RETRY_WAIT = int(os.getenv('WEBHOOK_RETRY_WAIT', 2))
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8000))
SCRIPT_NAME = os.getenv('WEBHOOK_SCRIPT_NAME', 'webhook_listener.sh')

# Set up logging
logging.basicConfig(
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=10_000_000,
            backupCount=5
        )
    ],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": [
    "http://seito.lavbic.net",
    "https://ultimate-krill-officially.ngrok-free.app"
]}})

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_fixed(RETRY_WAIT),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def update_repo():
    """Update the repository with retries."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(current_dir)
    
    try:
        logger.info("Fetching latest changes from origin...")
        subprocess.run(['git', 'fetch', '--prune', 'origin'],
                       cwd=repo_dir, check=True, capture_output=True, text=True)
        logger.info("Resetting repository to match origin/main...")
        subprocess.run(['git', 'reset', '--hard', 'origin/main'],
                       cwd=repo_dir, check=True, capture_output=True, text=True)
        logger.info("Repository updated successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error updating repository: {e.stderr}")
        raise

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_fixed(RETRY_WAIT),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def restart_services():
    """Restart services with retries."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, SCRIPT_NAME)
    
    try:
        if not os.access(script_path, os.X_OK):
            logger.info(f"Making script executable: {script_path}")
            os.chmod(script_path, 0o755)

        logger.info("Executing restart script...")
        process = subprocess.Popen(
            [script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=current_dir
        )
        _, stderr = process.communicate()
        if process.returncode != 0:
            logger.error(f"Restart script failed: {stderr.decode().strip()}")
            raise RuntimeError(f"Restart script error: {stderr.decode().strip()}")

        logger.info("Services restarted successfully.")
        return True
    except Exception as e:
        logger.error(f"Error restarting services: {str(e)}")
        raise

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Phase 1: Update repository
        logger.info("Phase 1: Updating repository...")
        try:
            update_repo()
        except RetryError as e:
            logger.error(f"Failed to update repository after {MAX_RETRIES} attempts.")
            return jsonify({
                'status': 'error',
                'message': 'Failed to update repository after multiple retries.'
            }), 500

        # Phase 2: Restart services
        logger.info("Phase 2: Restarting services...")
        try:
            restart_services()
        except RetryError as e:
            logger.error(f"Failed to restart services after {MAX_RETRIES} attempts.")
            return jsonify({
                'status': 'error',
                'message': 'Failed to restart services after multiple retries.'
            }), 500

        return jsonify({
            'status': 'success',
            'message': 'Webhook processed successfully.'
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in webhook endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred: ' + str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    logger.info(f"Starting webhook server on port {WEBHOOK_PORT}")
    app.run(host='0.0.0.0', port=WEBHOOK_PORT)
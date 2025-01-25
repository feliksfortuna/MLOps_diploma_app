from flask import Flask, request, jsonify
from flask_cors import CORS
import model_redeployment
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError

# Configuration
APP_HOST = "localhost"
APP_PORT = 10000
MAX_RETRIES = 5
RETRY_WAIT = 2

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://ultimate-krill-officially.ngrok-free.app"]}})

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# Retry decorator for redeployment logic
@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_fixed(RETRY_WAIT))
def safe_redeploy_model(index):
    """
    Calls the model_redeployment.redeploy_model function with retries.
    """
    logger.info(f"Attempting model redeployment for index: {index} (retryable)")
    try:
        result = model_redeployment.redeploy_model(index)
        logger.info(f"Model redeployment succeeded for index: {index}")
        return result
    except Exception as e:
        logger.error(f"Error during model redeployment (index={index}): {e}")
        raise

@app.route('/retrain', methods=['POST'])
def retrain():
    try:
        # Parse and validate the JSON request
        data = request.get_json(force=True)
        if not data or 'index' not in data:
            logger.error("Invalid or missing 'index' in request.")
            return jsonify({"error": "Invalid or missing 'index'. It must be provided."}), 400

        index = data.get('index')
        if not isinstance(index, int):
            logger.error(f"Invalid index type: {type(index)}. Expected an integer.")
            return jsonify({"error": "Invalid 'index'. It must be an integer."}), 400

        logger.info(f"Received retraining request for index: {index}")

        # Call the redeployment function with retries
        try:
            result = safe_redeploy_model(index)
        except RetryError as retry_error:
            logger.error(f"Model redeployment failed after {MAX_RETRIES} attempts: {retry_error}")
            return jsonify({
                "error": f"Model redeployment failed after {MAX_RETRIES} attempts.",
                "details": str(retry_error)
            }), 500

        # If successful, return the result
        return jsonify({
            "message": "Model redeployed successfully.",
            "result": result
        }), 200

    except Exception as e:
        # Catch any unexpected server-side errors
        logger.error(f"Unexpected error in /retrain: {str(e)}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    logger.info(f"Starting Flask server on {APP_HOST}:{APP_PORT}")
    app.run(host=APP_HOST, port=APP_PORT)
from flask import Flask, request, jsonify
from flask_cors import CORS
import model_redeployment
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost", "http://seito.lavbic.net", "http://192.168.5.178", "http://127.0.0.1:4040"]}})

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

@app.route('/retrain', methods=['POST'])
def retrain():
    # Get the index from the request
    try:
        data = request.get_json(force=True)
        index = data.get('index')

        if index is None:
            logging.error("Index not provided in request.")
            return jsonify({"error": "Index not provided"}), 400

        logging.info(f"Received retraining request for index: {index}")

        # Call the function from model_redeployment with the index
        result = model_redeployment.redeploy_model(index)

        logging.info(f"Model retraining completed successfully for index: {index}")
        return jsonify({"message": "Model redeployed successfully", "result": result}), 200

    except Exception as e:
        logging.error(f"Error during retraining: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="localhost", port=10000)

import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import data_process
import pandas as pd
import numpy as np
import os
import json

# Define paths of files
rider_names_path = "/home/bsc/MLOps_diploma_app/mlops/rider_names_test.npy"
data_path = "/home/bsc/MLOps_diploma_app/mlops/X_test.npy"
image_dir = "/home/bsc/MLOps_diploma_app/common/images"
race_names_path = "/home/bsc/MLOps_diploma_app/common/race_names.csv"

# Initialize logging
logging.basicConfig(
    filename="server.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)
CORS(app)

url = "https://ultimate-krill-officially.ngrok-free.app/retrain"

# Retry decorator with custom settings
@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)
def make_request_with_retries(index):
    try:
        logging.info(f"Attempting to make POST request to {url} with index: {index}")
        response = requests.post(url, json={"index": index})
        response.raise_for_status()
        logging.info("Request successful.")
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to {url} failed: {e}")
        raise

@app.route('/redeploy', methods=['POST'])
def redeploy():
    try:
        logging.info("Received request for /redeploy endpoint.")
        # Get the index from the request
        data = request.get_json(force=True)
        logging.debug(f"Request JSON payload: {data}")
        
        index = data.get('index')
        if index is None:
            logging.warning("Index not provided in request.")
            return jsonify({"error": "Index not provided"}), 400
        
        if not isinstance(index, int):
            logging.warning(f"Invalid index type: {type(index)}. Must be an integer.")
            return jsonify({"error": "Index must be an integer"}), 400

        # Make the request with retries
        response = make_request_with_retries(index)

        # Preprocess the data for later use on server
        logging.info(f"Starting data preprocessing for index: {index}")
        data_process.preprocess_data(index)
        logging.info("Data preprocessing completed successfully.")

        return response.json(), response.status_code

    except requests.exceptions.RequestException as e:
        logging.error(f"RequestException: {e}")
        return jsonify({"error": f"Request failed after retries: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500
    
@app.route('/images/<filename>')
def get_image(filename):
    if os.path.exists(os.path.join(image_dir, filename)):
        return send_from_directory(image_dir, filename)
    else:
        return send_from_directory(image_dir, "unknown.jpg")
    
@app.route('/races')
def get_races():
    race_names = pd.read_csv(race_names_path)
    X_test = np.load(data_path, allow_pickle=True)
    length = len(X_test)
    race_names = race_names.tail(length)
    race_names['name'] = race_names['name'].str.replace('-', ' ').str.title()
    race_names['stage'] = race_names['stage'].str.replace('-', ' ').str.title()

    race_names = race_names.sort_values(['name', 'stage'])

    # reset index in dataframe to current order
    race_names.reset_index(drop=True, inplace=True)
    race_names['index'] = race_names.index

    return jsonify(race_names.to_dict(orient='records')), 200
    
@app.route('/predict', methods=['POST'])
def predict():
    X_test = np.load(data_path, allow_pickle=True)
    rider_names = np.load(rider_names_path, allow_pickle=True)
    try:
        # Parse the incoming request
        data = request.get_json(force=True)
        logging.debug(f"Request JSON payload: {data}")

        # Validate the index parameter
        index = data.get('index')
        if index is None:
            logging.warning("Index not provided in request.")
            return jsonify({"error": "Index not provided"}), 400

        if not isinstance(index, int):
            logging.warning(f"Invalid index type: {type(index)}. Must be an integer.")
            return jsonify({"error": "Index must be an integer"}), 400

        # Ensure index is within bounds
        if index < 0 or index >= len(X_test):
            logging.warning("Index out of bounds.")
            return jsonify({"error": "Invalid index"}), 400

        # Select the data
        race_data = X_test[index].astype(np.float32)
        race_rider_names = rider_names[index]

        # Prepare payload for external service
        payload = {
            "instances": race_data.tolist()
        }

        # Make the prediction
        response = requests.post(
            "http://seito.lavbic.net:5005/invocations",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=600
        )

        if response.status_code != 200:
            logging.error(f"Prediction service returned error: {response.text}")
            return jsonify({"error": "Prediction service error"}), response.status_code

        # Parse predictions
        prediction = response.json()['predictions']

        # Combine predictions with rider names and images
        rider_prediction = [
            {
                "name": name,
                "prediction": float(pred),
                "image_url": os.path.join(f"http://seito.lavbic.net:15000/images/{name}.jpg")
            }
            for name, pred in zip(race_rider_names, prediction) if name != "PAD"
        ]

        # Sort by prediction in descending order
        rider_prediction = sorted(rider_prediction, key=lambda x: x["prediction"], reverse=True)

        return jsonify({"prediction": rider_prediction}), 200

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500


if __name__ == '__main__':
    logging.info("Starting Flask server on 0.0.0.0:5010")
    app.run(host="0.0.0.0", port=5010)
import logging
from threading import Thread
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import data_process
import pandas as pd
import numpy as np
import os
import json
import time

# Prometheus imports
from prometheus_client import Counter, Histogram, generate_latest

rider_names_path = "/home/bsc/MLOps_diploma_app/mlops/rider_names_test.npy"
data_path = "/home/bsc/MLOps_diploma_app/mlops/X_test.npy"
image_dir = "/home/bsc/MLOps_diploma_app/common/images"
race_names_path = "/home/bsc/MLOps_diploma_app/common/race_names.csv"

url = "https://ultimate-krill-officially.ngrok-free.app/retrain"

# Prometheus metrics
REDEPLOY_COUNT = Counter(
    "mlops_redeploy_total",
    "Number of times a redeployment is triggered"
)
REDEPLOY_TIME = Histogram(
    "mlops_redeploy_time_seconds",
    "Time taken for the redeployment process"
)
PREDICT_COUNT = Counter(
    "mlops_predict_total",
    "Total predict calls to MLOps"
)
PREDICT_LATENCY = Histogram(
    "mlops_predict_latency_seconds",
    "Latency of predict calls in MLOps"
)

logging.basicConfig(
    filename="server.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://seito.lavbic.net:3001", "https://ultimate-krill-officially.ngrok-free.app"]}})

@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)
def make_request_with_retries(index):
    logging.info(f"Attempting to make POST request to {url} with index: {index}")
    response = requests.post(url, json={"index": index})
    response.raise_for_status()
    logging.info("Request successful.")
    return response

@app.route('/redeploy', methods=['POST'])
def redeploy():
    start_time = time.time()
    REDEPLOY_COUNT.inc()

    try:
        logging.info("Received request for /redeploy endpoint.")
        data = request.get_json(force=True)
        logging.debug(f"Request JSON payload: {data}")

        index = data.get('index')
        if index is None:
            logging.warning("Index not provided in request.")
            return jsonify({"error": "Index not provided"}), 400

        if not isinstance(index, int):
            logging.warning(f"Invalid index type: {type(index)}. Must be an integer.")
            return jsonify({"error": "Index must be an integer"}), 400

        # Define a function to do heavy lifting
        def run_redeployment(idx, status_container):
            try:
                logging.info(f"Starting redeployment process for index: {idx}")

                # 1) Make the external retraining request
                response = make_request_with_retries(idx)

                # 2) Preprocess the data
                logging.info(f"Starting data preprocessing for index: {idx}")
                data_process.preprocess_data(idx)
                logging.info("Data preprocessing completed successfully.")

                status_container['response'] = response
                status_container['exception'] = None
            except Exception as e:
                logging.error(f"Redeployment failed: {e}")
                status_container['exception'] = e
                status_container['response'] = None

        thread_status = {'response': None, 'exception': None}
        t = Thread(target=run_redeployment, args=(index, thread_status))
        t.start()
        t.join()

        if thread_status['exception'] is not None:
            e = thread_status['exception']
            return jsonify({"error": f"Redeployment failed: {str(e)}"}), 500

        # Redeployment done
        total_time = time.time() - start_time
        REDEPLOY_TIME.observe(total_time)

        return thread_status['response'].json(), thread_status['response'].status_code

    except Exception as e:
        logging.error(f"Unexpected error in /redeploy: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

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

    original_order = race_names.copy()
    sorted_races = race_names.sort_values(['name', 'stage']).reset_index(drop=True)
    original_order['index'] = original_order.apply(
        lambda row: sorted_races[
            (sorted_races['name'] == row['name']) &
            (sorted_races['stage'] == row['stage'])
        ].index[0],
        axis=1
    )
    return jsonify(original_order.to_dict(orient='records')), 200

@app.route('/predict', methods=['POST'])
def predict():
    import time
    start_time = time.time()
    PREDICT_COUNT.inc()

    try:
        X_test = np.load(data_path, allow_pickle=True)
        rider_names = np.load(rider_names_path, allow_pickle=True)

        data = request.get_json(force=True)
        logging.debug(f"Request JSON payload: {data}")

        index = data.get('index')
        if index is None:
            logging.warning("Index not provided in request.")
            return jsonify({"error": "Index not provided"}), 400
        if not isinstance(index, int):
            logging.warning(f"Invalid index type: {type(index)}. Must be an integer.")
            return jsonify({"error": "Index must be an integer"}), 400
        if index < 0 or index >= len(X_test):
            logging.warning("Index out of bounds.")
            return jsonify({"error": "Invalid index"}), 400

        race_data = X_test[index].astype(np.float32)
        race_rider_names = rider_names[index]

        payload = {"instances": race_data.tolist()}

        response = requests.post(
            "http://seito.lavbic.net:5005/invocations",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=600
        )

        if response.status_code != 200:
            logging.error(f"Prediction service returned error: {response.text}")
            return jsonify({"error": "Prediction service error"}), response.status_code

        prediction = response.json()['predictions']
        rider_prediction = [
            {
                "name": name,
                "prediction": float(pred),
                "image_url": os.path.join(f"http://seito.lavbic.net:5010/images/{name}.jpg")
            }
            for name, pred in zip(race_rider_names, prediction) if name != "PAD"
        ]
        rider_prediction = sorted(rider_prediction, key=lambda x: x["prediction"], reverse=True)

        return jsonify({"prediction": rider_prediction}), 200

    except Exception as e:
        logging.error(f"Error in /predict: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
    finally:
        total_latency = time.time() - start_time
        PREDICT_LATENCY.observe(total_latency)

@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200

if __name__ == '__main__':
    logging.info("Starting MLOps API on port 5010")
    app.run(host="0.0.0.0", port=5010)
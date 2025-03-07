import os
import time
import json
import logging
import pickle
from functools import wraps
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError

MODEL_PATH = os.getenv("MODEL_PATH", "/home/bsc/MLOps_diploma_app/devops/model/model.pkl")
RIDER_NAMES_PATH = os.getenv("RIDER_NAMES_PATH", "/home/bsc/MLOps_diploma_app/devops/rider_names_test.npy")
DATA_PATH = os.getenv("DATA_PATH", "/home/bsc/MLOps_diploma_app/devops/X_test.npy")
IMAGE_DIR = os.getenv("IMAGE_DIR", "/home/bsc/MLOps_diploma_app/common/images")
RACE_NAMES_PATH = os.getenv("RACE_NAMES_PATH", "/home/bsc/MLOps_diploma_app/common/race_names.csv")
APP_PORT = int(os.getenv("APP_PORT", 15000))

# Swagger configuration
SWAGGER_URL = '/documentation'
API_URL = '/static/swagger.json'

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "DevOps API Documentation"
    }
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create static folder if it doesn't exist
if not os.path.exists('static'):
    os.makedirs('static')

app = Flask(__name__)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://seito.lavbic.net:3002"]}})

# Swagger specification
swagger_spec = {
    "openapi": "3.0.0",
    "info": {
        "title": "DevOps API",
        "version": "1.0.0",
        "description": "API for DevOps predictions and race information"
    },
    "servers": [
        {
            "url": f"http://seito.lavbic.net:{APP_PORT}",
            "description": "Production server"
        }
    ],
    "paths": {
        "/predict": {
            "post": {
                "summary": "Make predictions for a specific race",
                "description": "Predict race outcomes using the trained model",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "index": {
                                        "type": "integer",
                                        "description": "Race index for prediction"
                                    }
                                },
                                "required": ["index"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful prediction",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "prediction": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {
                                                        "type": "string",
                                                        "description": "Rider name"
                                                    },
                                                    "prediction": {
                                                        "type": "number",
                                                        "description": "Prediction score"
                                                    },
                                                    "image_url": {
                                                        "type": "string",
                                                        "description": "URL to rider's image"
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid input",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "500": {
                        "description": "Server error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/races": {
            "get": {
                "summary": "Get race information",
                "description": "Retrieve information about all races",
                "responses": {
                    "200": {
                        "description": "List of races",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "Race name"
                                            },
                                            "stage": {
                                                "type": "string",
                                                "description": "Race stage"
                                            },
                                            "index": {
                                                "type": "integer",
                                                "description": "Race index"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "500": {
                        "description": "Server error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/images/{filename}": {
            "get": {
                "summary": "Get rider image",
                "description": "Retrieve a rider's image by filename",
                "parameters": [
                    {
                        "name": "filename",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        },
                        "description": "Image filename"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Image file",
                        "content": {
                            "image/*": {
                                "schema": {
                                    "type": "string",
                                    "format": "binary"
                                }
                            }
                        }
                    },
                    "500": {
                        "description": "Server error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/metrics": {
            "get": {
                "summary": "Get Prometheus metrics",
                "description": "Retrieve Prometheus metrics for monitoring",
                "responses": {
                    "200": {
                        "description": "Prometheus metrics",
                        "content": {
                            "text/plain": {
                                "schema": {
                                    "type": "string"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

# Write Swagger specification to file
with open('static/swagger.json', 'w') as f:
    json.dump(swagger_spec, f)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "devops_api_requests_total",
    "Total requests to DevOps API",
    ["endpoint", "method", "status"]
)
REQUEST_LATENCY = Histogram(
    "devops_api_request_latency_seconds",
    "Request latency for DevOps API",
    ["endpoint"]
)

def track_metrics(endpoint_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                response = func(*args, **kwargs)
                status_code = getattr(response, "status_code", 200)
                REQUEST_COUNT.labels(endpoint=endpoint_name, method=request.method, status=status_code).inc()
                return response
            except Exception as e:
                REQUEST_COUNT.labels(endpoint=endpoint_name, method=request.method, status=500).inc()
                raise e
            finally:
                latency = time.time() - start_time
                REQUEST_LATENCY.labels(endpoint=endpoint_name).observe(latency)
        return wrapper
    return decorator

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def load_file_with_retries(filepath, loader_fn):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    logger.info(f"Loading file: {filepath}")
    return loader_fn(filepath)

@app.route("/metrics", methods=["GET"])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST), 200

@app.route('/predict', methods=['POST'])
@track_metrics("predict")
def predict():
    try:
        data = request.get_json(force=True)
        race_index = data.get('index')
        if race_index is None or not isinstance(race_index, int):
            return jsonify({"error": "Invalid or missing 'index'. It must be an integer."}), 400

        # Load data
        rider_names = load_file_with_retries(RIDER_NAMES_PATH, lambda f: np.load(f, allow_pickle=True))
        X_test = load_file_with_retries(DATA_PATH, lambda f: np.load(f, allow_pickle=True))
        if race_index < 0 or race_index >= len(X_test):
            return jsonify({"error": "Index out of bounds."}), 400

        race_data = X_test[race_index].astype(np.float32)

        # Load model
        try:
            with open(MODEL_PATH, 'rb') as f:
                loaded_model = pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return jsonify({"error": "Failed to load the prediction model."}), 500

        # Predict
        try:
            prediction = loaded_model.predict(race_data)
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return jsonify({"error": "Prediction failed due to model issues."}), 500

        race_rider_names = rider_names[race_index]
        rider_prediction = [
            {
                "name": name,
                "prediction": float(pred),
                "image_url": os.path.join(f"http://seito.lavbic.net:15000/images/{name}.jpg")
            }
            for name, pred in zip(race_rider_names, prediction) if name != "PAD"
        ]
        rider_prediction.sort(key=lambda x: x["prediction"], reverse=True)

        return jsonify({"prediction": rider_prediction}), 200

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return jsonify({"error": str(e)}), 500
    except RetryError as e:
        logger.error(f"Retries exceeded: {e}")
        return jsonify({"error": "Failed to load a required file after multiple retries."}), 500
    except Exception as e:
        logger.error(f"Unexpected error in /predict: {e}")
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500

@app.route('/images/<filename>')
@track_metrics("images")
def get_image(filename):
    try:
        filepath = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(filepath):
            logger.warning(f"Image not found: {filename}")
            filepath = os.path.join(IMAGE_DIR, "unknown.jpg")
        return send_from_directory(IMAGE_DIR, os.path.basename(filepath))
    except Exception as e:
        logger.error(f"Error in /images endpoint: {e}")
        return jsonify({"error": "Failed to retrieve the requested image."}), 500

@app.route('/races', methods=['GET'])
@track_metrics("races")
def get_races():
    try:
        race_names = load_file_with_retries(RACE_NAMES_PATH, pd.read_csv)
        X_test = load_file_with_retries(DATA_PATH, lambda f: np.load(f, allow_pickle=True))
        length = len(X_test) - 1
        logger.info(f"Length of X_test: {length}")

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

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return jsonify({"error": str(e)}), 500
    except RetryError as e:
        logger.error(f"Retries exceeded: {e}")
        return jsonify({"error": "Failed to load a required file after multiple retries."}), 500
    except Exception as e:
        logger.error(f"Unexpected error in /races: {e}")
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500

if __name__ == "__main__":
    logger.info(f"Starting DevOps API on port {APP_PORT}")
    app.run(host="0.0.0.0", port=APP_PORT, debug=False)
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import data_process

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
    # Perform the request to the retrain endpoint
    response = requests.post(url, json={"index": index})
    response.raise_for_status()
    return response

@app.route('/redeploy', methods=['POST'])
def redeploy():
    try:
        # Get the index from the request
        data = request.get_json(force=True)
        index = data.get('index')

        if index is None:
            return jsonify({"error": "Index not provided"}), 400
        
        if not isinstance(index, int):
            return jsonify({"error": "Index must be an integer"}), 400

        # Make the request with retries
        response = make_request_with_retries(index)

        # Preprocess the data for later use on server
        data_process.preprocess_data(index)

        return response.json(), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request failed after retries: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5010)
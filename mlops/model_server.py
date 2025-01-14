from flask import Flask, request, jsonify
from flask_cors import CORS
import model_redeployment

app = Flask(__name__)
CORS(app)

@app.route('/redeploy', methods=['POST'])
def redeploy():
    # Get the index from the request
    data = request.get_json(force=True)
    index = data.get('index')

    if index is None:
        return jsonify({"error": "Index not provided"}), 400

    # Call the function from model_redeployment with the index
    try:
        result = model_redeployment.redeploy_model(index)
        return jsonify({"message": "Model redeployed successfully", "result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5010)
from flask import Flask, request, jsonify
import numpy as np
import pickle

# Initialize Flask app
app = Flask(__name__)

# Load the pickled model
model_path = "./model/model.pkl"
with open(model_path, 'rb') as f:
    loaded_model = pickle.load(f)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Parse JSON input
        input_data = request.json["instances"]
        
        # Convert input to numpy array with dtype float32
        input_array = np.array(input_data, dtype=np.float32)
        
        # Make prediction using the loaded model
        prediction = loaded_model.predict(input_array)
        
        # Return the prediction as JSON
        return jsonify({"predictions": prediction.tolist()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000, debug=True)

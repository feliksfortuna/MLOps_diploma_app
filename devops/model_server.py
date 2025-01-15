from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import numpy as np
import pickle
import csv
import os

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Define paths of files
model_path = "./model/model.pkl"
rider_names_path = "./rider_names_test.npy"
data_path = "./X_test.npy"
image_dir = "../common/images"
race_names_path = "../common/race_names.csv"

# Load the pickled model
with open(model_path, 'rb') as f:
    loaded_model = pickle.load(f)

# Load the rider names
rider_names = np.load(rider_names_path, allow_pickle=True)  # Shape: (num_races, num_riders)

# Load the data
X_test = np.load(data_path, allow_pickle=True)  # Shape: (num_races, num_riders, num_features)

# Load the race names data
with open(race_names_path, 'r') as f:
    reader = csv.reader(f)
    next(reader)  # Skip the header
    race_names = [row for row in reader]

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get the index from the POST request
        data = request.get_json(force=True)
        race_index = data['index']

        if race_index < 0 or race_index >= len(X_test):
            return jsonify({"error": "Invalid index"}), 400

        # Get the data for the specified race
        race_data = X_test[race_index].astype(np.float32)  # Shape: (num_riders, num_features)
        
        # Get predictions for all riders in the race
        prediction = loaded_model.predict(race_data)  # Shape: (num_riders,)

        # Get the rider names for the specified race
        race_rider_names = rider_names[race_index]  # Shape: (num_riders,)

        # Combine rider names, predictions, and image paths
        rider_prediction = [
            {
                "name": name,
                "prediction": float(pred),
                "image_url": os.path.join(f"http://seito.lavbic.net:15000/images/{name}.jpg")
            }
            for name, pred in zip(race_rider_names, prediction) if name != "PAD"
        ]


        # Sort the predictions
        rider_prediction = sorted(rider_prediction, key=lambda x: x["prediction"], reverse=True)

        return jsonify({"prediction": rider_prediction})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/images/<filename>')
def get_image(filename):
    if os.path.exists(os.path.join(image_dir, filename)):
        return send_from_directory(image_dir, filename)
    else:
        return send_from_directory(image_dir, "unknown.jpg")
    
@app.route('/races')
def get_races():
    race_names['name'] = race_names['name'].str.replace('-', ' ').str.title()
    race_names['stage'] = race_names['stage'].str.replace('-', ' ').str.title()

    return jsonify(race_names.to_dict(orient='records'))

# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=15000, debug=True)

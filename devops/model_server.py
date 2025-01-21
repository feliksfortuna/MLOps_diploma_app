from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np
import pickle
import os

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://seito.lavbic.net:3002"]}})

# Define paths of files
model_path = "/home/bsc/MLOps_diploma_app/devops/model/model.pkl"
rider_names_path = "/home/bsc/MLOps_diploma_app/devops/rider_names_test.npy"
data_path = "/home/bsc/MLOps_diploma_app/devops/X_test.npy"
image_dir = "/home/bsc/MLOps_diploma_app/common/images"
race_names_path = "/home/bsc/MLOps_diploma_app/common/race_names.csv"

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get the index from the POST request
        data = request.get_json(force=True)
        race_index = data['index']

        if race_index < 0 or race_index >= len(X_test):
            return jsonify({"error": "Invalid index"}), 400
        
        # Load the rider names
        rider_names = np.load(rider_names_path, allow_pickle=True)

        # Load the data
        X_test = np.load(data_path, allow_pickle=True)

        # Get the data for the specified race
        race_data = X_test[race_index].astype(np.float32)  # Shape: (num_riders, num_features)

        # Load the pickled model
        with open(model_path, 'rb') as f:
            loaded_model = pickle.load(f)
        
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
    # Read race names from the file
    race_names = pd.read_csv(race_names_path)

    # Load test data to determine the relevant rows
    X_test = np.load(data_path, allow_pickle=True)
    length = len(X_test)

    # Filter the race names to include only the relevant rows
    race_names = race_names.tail(length)

    # Format the race names and stages
    race_names['name'] = race_names['name'].str.replace('-', ' ').str.title()
    race_names['stage'] = race_names['stage'].str.replace('-', ' ').str.title()

    # Create a copy of the original DataFrame to maintain the initial order
    original_order = race_names.copy()

    # Sort the races by name and stage
    sorted_races = race_names.sort_values(['name', 'stage']).reset_index(drop=True)

    # Map the sorted indices back to the original order
    original_order['index'] = original_order.apply(
        lambda row: sorted_races[(sorted_races['name'] == row['name']) & 
                                 (sorted_races['stage'] == row['stage'])].index[0],
        axis=1
    )

    # Convert to dictionary and return in the original order
    return jsonify(original_order.to_dict(orient='records')), 200

# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=15000, debug=True)

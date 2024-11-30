from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import mlflow.pyfunc

app = Flask(__name__)
CORS(app)

# Load the model
model = mlflow.pyfunc.load_model("model")

@app.route('/predict', methods=['POST'])
async def predict():
    # Get the data from the request
    data = request.get_json(force=True)
    data = pd.DataFrame(data, index=[0])

    # Make a prediction
    prediction = model.predict(data)

    # Return the prediction
    return jsonify(prediction.tolist())
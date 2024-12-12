from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import mlflow.pyfunc

app = Flask(__name__)
CORS(app)

# Set the MLflow tracking URI to your local server
mlflow.set_tracking_uri('http://127.0.0.1:5000')

# Specify the registered model name
model_name = 'latest' 

# Load the latest version of the model from the specified stage
model = mlflow.pyfunc.load_model(model_uri=f'models:/{model_name}/1')

@app.route('/predict', methods=['POST'])
async def predict():
    # Get the data from the request
    data = request.get_json(force=True)
    data = pd.DataFrame(data, index=[0])

    # Make a prediction
    prediction = model.predict(data)

    # Return the prediction
    return jsonify(prediction.tolist())

if __name__ == '__main__':
    app.run(port=5001)
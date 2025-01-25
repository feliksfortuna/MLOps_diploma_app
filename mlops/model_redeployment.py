import mlflow
import mlflow.pytorch
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from mlflow.models.signature import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from torch.utils.data import DataLoader
from model_def import RaceRegressionModel
import get_data

# Set MLflow experiment
mlflow.set_tracking_uri("http://seito.lavbic.net:5000")
mlflow.set_experiment("Race_Prediction_Experiment_I")
client = MlflowClient()

# get the best model id
experiment_name = "Race_Prediction_Experiment_I"
experiment_id = client.get_experiment_by_name(experiment_name).experiment_id
runs = client.search_runs(experiment_id, order_by=["metrics.test_mae ASC"], max_results=1)
best_run = runs[0]

best_params = best_run.data.params
        
# Define the dataset class
class RaceRegressionDataset(torch.utils.data.Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]
    
def retrain():
    # Load the data (adjust file paths as needed)
    X_train = np.load('/Users/feliks/Documents/Faks/Diplomska/App/mlops/X_train.npy', allow_pickle=True)
    y_train = np.load('/Users/feliks/Documents/Faks/Diplomska/App/mlops/y_train.npy', allow_pickle=True)
    X_test = np.load('/Users/feliks/Documents/Faks/Diplomska/App/mlops/X_test.npy', allow_pickle=True)
    y_test = np.load('/Users/feliks/Documents/Faks/Diplomska/App/mlops/y_test.npy', allow_pickle=True)

    # Flatten the data for scikit-learn models
    X_train_flat = X_train.reshape(-1, X_train.shape[2])
    X_test_flat = X_test.reshape(-1, X_test.shape[2])

    # Flatten the targets
    y_train_flat = y_train.flatten()
    y_test_flat = y_test.flatten()

    # Create datasets
    train_dataset = RaceRegressionDataset(X_train_flat, y_train_flat)
    test_dataset = RaceRegressionDataset(X_test_flat, y_test_flat)

    # Create data loaders with the best batch size
    train_loader = DataLoader(train_dataset, batch_size=int(best_params['batch_size']), shuffle=True, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=int(best_params['batch_size']), shuffle=False, num_workers=0)

    # Initialize the model, optimizer, and loss function
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    input_size = X_train_flat.shape[1]

    model = RaceRegressionModel(input_size, int(best_params['hidden_size'])).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=float(best_params['learning_rate']), weight_decay=float(best_params['weight_decay']))

    # Start MLflow run
    with mlflow.start_run(run_name="Retrained Best Model"):
        # Log parameters
        mlflow.log_params(best_params)

        # Training loop
        num_epochs = best_params['num_epochs']
        for epoch in range(int(num_epochs)):
            model.train()
            total_loss = 0
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)

                optimizer.zero_grad()
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * X_batch.size(0)

            average_loss = total_loss / len(train_loader.dataset)
            mlflow.log_metric("train_loss", average_loss, step=epoch)
            print(f"Epoch {epoch + 1}/{num_epochs}, Loss: {average_loss:.4f}")

        # Evaluation on test set
        model.eval()
        y_true_list = []
        y_pred_list = []
        with torch.no_grad():
            for X_batch, y_batch in test_loader:
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)

                outputs = model(X_batch)
                y_true_list.extend(y_batch.cpu().numpy())
                y_pred_list.extend(outputs.cpu().numpy())

        y_true_array = np.array(y_true_list)
        y_pred_array = np.array(y_pred_list)

        # Compute evaluation metrics
        mse = mean_squared_error(y_true_array, y_pred_array)
        mae = mean_absolute_error(y_true_array, y_pred_array)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_true_array, y_pred_array)

        def mean_absolute_percentage_error(y_true, y_pred):
            epsilon = 1e-8  # Avoid division by zero
            mask = np.abs(y_true) > epsilon
            return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

        def symmetric_mean_absolute_percentage_error(y_true, y_pred):
            denominator = (np.abs(y_true) + np.abs(y_pred)) / 2
            diff = np.abs(y_pred - y_true)
            mask = denominator != 0
            return np.mean((diff[mask] / denominator[mask])) * 100

        mape = mean_absolute_percentage_error(y_true_array, y_pred_array)
        smape = symmetric_mean_absolute_percentage_error(y_true_array, y_pred_array)

        # Log metrics
        mlflow.log_metrics({
            'test_mse': mse,
            'test_mae': mae,
            'test_rmse': rmse,
            'test_r2': r2,
            'test_mape': mape,
            'test_smape': smape
        })

        # Log the model
        input_example = X_train_flat[:5].astype(np.float32)
        input_example_tensor = torch.tensor(input_example, dtype=torch.float32).to(device)
        signature = infer_signature(
            input_example,
            model(input_example_tensor).cpu().detach().numpy()
        )
        mlflow.pytorch.log_model(
            pytorch_model=model,
            artifact_path="model",
            input_example=input_example,
            signature=signature
        )
        run = mlflow.active_run()

    print("Training complete. Model and metrics logged to MLflow.")
    return run.info.run_id

def deploy_and_overwrite_model(run_id):
    client = MlflowClient()
    model_name = "Race prediction"

    # Register the new model version
    model_uri = f"runs:/{run_id}/model"
    new_model_version = client.create_model_version(
        name=model_name,
        source=model_uri,
        run_id=run_id
    )

    # Add alias "production" to the new model version
    client.set_registered_model_alias(
        name=model_name,
        alias="production",
        version=new_model_version.version
    )
    print(f"New model version {new_model_version.version} deployed to production with alias 'production'.")

    # Remove alias "production" from old model versions
    for mv in client.search_model_versions(f"name='{model_name}'"):
        if "production" in mv.aliases and mv.version != str(new_model_version.version):
            client.delete_registered_model_alias(
                name=model_name,
                alias="production"
            )
            print(f"Removed 'production' alias from previous model version {mv.version}.")

def redeploy_model(index):
    get_data.preprocess_data(index)
    run_id = retrain()
    deploy_and_overwrite_model(run_id)
    return run_id
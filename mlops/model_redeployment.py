import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, OrdinalEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import mlflow
from mlflow.tracking import MlflowClient
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import mlflow.pytorch
from mlflow.models.signature import infer_signature

merged_data = pd.read_csv('../common/final_data.csv')

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
print("Best Run Parameters:")
print(best_params)

def pad_riders(rider_list, max_riders, pad_value='Unknown'):
        if len(rider_list) < max_riders:
            return rider_list + [pad_value] * (max_riders - len(rider_list))
        else:
            return rider_list[:max_riders]
        
def split_test_train_data(index):
    # Split data into training and testing sets based on 'year'
    train_data = merged_data[merged_data['year'] < 2024]
    test_data = merged_data[merged_data['year'] == 2024]

    # Add data from test set to training set incrementally
    unique_race_names = test_data['name'].unique()
    races_to_move = unique_race_names[:index+1]

    race_data_to_move = test_data[test_data['name'].isin(races_to_move)]
    train_data = pd.concat([train_data, race_data_to_move], ignore_index=True)
    test_data = test_data[~test_data['name'].isin(races_to_move)].reset_index(drop=True)

    return train_data, test_data

def preprocess_data(index):
    # Define feature groups
    race_numerical = [
        'distance', 'vertical_meters', 'speed', 'year', 'score', 'quality', 'ranking'
    ]
    race_categorical = ['name']
    rider_numerical = [
        'weight', 'height', 'one_day', 'gc', 'tt', 'sprint',
        'climber', 'hills', 'age'
    ]
    rider_categorical_low = ['speciality']
    rider_categorical_high = ['nationality', 'team', 'rider_name']

    train_data, test_data = split_test_train_data(index)

    # Determine the maximum number of riders across all races in both training and testing data
    max_riders_train = train_data.groupby(['name', 'year']).size().max()
    max_riders_test = test_data.groupby(['name', 'year']).size().max()
    max_riders = max(max_riders_train, max_riders_test)

    # Create preprocessing pipelines
    race_numeric_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', MinMaxScaler())
    ], memory=None)

    race_categorical_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
        ('onehot', OneHotEncoder(
            drop='first', sparse_output=False, handle_unknown='ignore'
        ))
    ], memory=None)

    rider_numeric_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', MinMaxScaler())
    ], memory=None)

    rider_categorical_low_pipeline = Pipeline([
        ('imputer', SimpleImputer(
            strategy='constant', fill_value='Unknown')),
        ('onehot', OneHotEncoder(
            drop='first', sparse_output=False, handle_unknown='ignore'
        ))
    ], memory=None)

    rider_categorical_high_pipeline = Pipeline([
        ('imputer', SimpleImputer(
            strategy='constant', fill_value='Unknown')),
        ('ordinal', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))
    ], memory=None)

    # Fit pipelines on training data
    race_numeric_pipeline.fit(train_data[race_numerical])
    race_categorical_pipeline.fit(train_data[race_categorical])
    rider_numeric_pipeline.fit(train_data[rider_numerical])
    rider_categorical_low_pipeline.fit(train_data[rider_categorical_low])
    rider_categorical_high_pipeline.fit(train_data[rider_categorical_high])

    # Initialize lists for training data
    races_train = []
    targets_train = []
    rider_names_train = []

    for (race_name, year), group in train_data.groupby(['name', 'year']):
        try:
            # Extract race-level features
            race_num_data = group[race_numerical].iloc[[0]]
            race_cat_data = group[race_categorical].iloc[[0]]

            # Extract rider-level features
            rider_num_data = group[rider_numerical]
            rider_cat_data_low = group[rider_categorical_low]
            rider_cat_data_high = group[rider_categorical_high]

            # Transform features using fitted pipelines
            race_num_processed = race_numeric_pipeline.transform(race_num_data)
            race_cat_processed = race_categorical_pipeline.transform(race_cat_data)
            rider_num_processed = rider_numeric_pipeline.transform(rider_num_data)
            rider_cat_low_processed = rider_categorical_low_pipeline.transform(rider_cat_data_low)
            rider_cat_high_processed = rider_categorical_high_pipeline.transform(rider_cat_data_high)

            # Combine features
            race_features = np.hstack((race_num_processed, race_cat_processed))
            rider_features = np.hstack((rider_num_processed, rider_cat_low_processed, rider_cat_high_processed))

            # Pad or truncate rider_features to max_riders
            n_riders = rider_features.shape[0]
            if n_riders < max_riders:
                pad_width = max_riders - n_riders
                padded_rider_features = np.pad(
                    rider_features,
                    ((0, pad_width), (0, 0)),
                    mode='constant',
                    constant_values=0
                )
            else:
                padded_rider_features = rider_features[:max_riders, :]

            # Create feature matrix by repeating race_features and concatenating with rider_features
            feature_matrix = np.hstack((
                np.tile(race_features, (max_riders, 1)),
                padded_rider_features
            ))

            # Calculate probabilities for first 3 riders and pad or truncate to max_riders
            ranks = group['rank'].values
            padded_probabilities = np.zeros(max_riders)
            probabilities = np.array([np.exp(-ranks[:3]) / np.sum(np.exp(-ranks[:3]))])
            padded_probabilities[0:3] = probabilities

            # Collect rider names and pad or truncate to max_riders
            riders = group['rider_name'].tolist()
            if n_riders < max_riders:
                padded_riders = riders + ['PAD'] * (max_riders - n_riders)
            else:
                padded_riders = riders[:max_riders]

            # Append data to lists
            races_train.append(feature_matrix)
            targets_train.append(padded_probabilities)
            rider_names_train.append(padded_riders)

        except Exception as e:
            print(f"Error processing race {race_name} {year}: {e}")
            continue

    # Initialize lists for test data
    races_test = []
    targets_test = []
    rider_names_test = []

    for (race_name, year), group in test_data.groupby(['name', 'year']):
        try:
            # Extract race-level features
            race_num_data = group[race_numerical].iloc[[0]]
            race_cat_data = group[race_categorical].iloc[[0]]

            # Extract rider-level features
            rider_num_data = group[rider_numerical]
            rider_cat_data_low = group[rider_categorical_low]
            rider_cat_data_high = group[rider_categorical_high]

            # Transform features using pipelines fitted on training data
            race_num_processed = race_numeric_pipeline.transform(race_num_data)
            race_cat_processed = race_categorical_pipeline.transform(race_cat_data)
            rider_num_processed = rider_numeric_pipeline.transform(rider_num_data)
            rider_cat_low_processed = rider_categorical_low_pipeline.transform(rider_cat_data_low)
            rider_cat_high_processed = rider_categorical_high_pipeline.transform(rider_cat_data_high)

            # Combine features
            race_features = np.hstack((race_num_processed, race_cat_processed))
            rider_features = np.hstack((rider_num_processed, rider_cat_low_processed, rider_cat_high_processed))

            # Pad or truncate rider_features to max_riders
            n_riders = rider_features.shape[0]
            if n_riders < max_riders:
                pad_width = max_riders - n_riders
                padded_rider_features = np.pad(
                    rider_features,
                    ((0, pad_width), (0, 0)),
                    mode='constant',
                    constant_values=0
                )
            else:
                padded_rider_features = rider_features[:max_riders, :]

            # Create feature matrix by repeating race_features and concatenating with rider_features
            feature_matrix = np.hstack((
                np.tile(race_features, (max_riders, 1)),
                padded_rider_features
            ))

            # Calculate probabilities for first 3 riders and pad or truncate to max_riders
            ranks = group['rank'].values
            padded_probabilities = np.zeros(max_riders)
            probabilities = np.array([np.exp(-ranks[:3]) / np.sum(np.exp(-ranks[:3]))])
            padded_probabilities[0:3] = probabilities

            # Collect rider names and pad or truncate to max_riders
            riders = group['rider_name'].tolist()
            if n_riders < max_riders:
                padded_riders = riders + ['PAD'] * (max_riders - n_riders)
            else:
                padded_riders = riders[:max_riders]

            # Append data to lists
            races_test.append(feature_matrix)
            targets_test.append(padded_probabilities)
            rider_names_test.append(padded_riders)

        except Exception as e:
            print(f"Error processing race {race_name} {year}: {e}")
            continue
    # Find maximum number of riders across all data
    max_riders = max(
        max(len(riders) for riders in rider_names_train),
        max(len(riders) for riders in rider_names_test)
    )

    # Convert lists to NumPy arrays
    X_train = np.array(races_train)
    y_train = np.array(targets_train)
    rider_names_train = np.array(rider_names_train, dtype=object)

    X_test = np.array(races_test)
    y_test = np.array(targets_test)
    rider_names_test = np.array(rider_names_test, dtype=object)

    # Save the data
    np.save('X_train.npy', X_train)
    np.save('y_train.npy', y_train)
    np.save('rider_names_train.npy', rider_names_train)

    np.save('X_test.npy', X_test)
    np.save('y_test.npy', y_test)
    np.save('rider_names_test.npy', rider_names_test)

    print("Data preprocessing completed and saved.")

# Define the model class
class RaceRegressionModel(nn.Module):
    def __init__(self, input_size, hidden_size=128):
        super(RaceRegressionModel, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        return out.squeeze()

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
    X_train = np.load('X_train.npy', allow_pickle=True)
    y_train = np.load('y_train.npy', allow_pickle=True)
    X_test = np.load('X_test.npy', allow_pickle=True)
    y_test = np.load('y_test.npy', allow_pickle=True)

    # Flatten the data for scikit-learn models
    X_train_flat = X_train.reshape(-1, X_train.shape[2])    # Shape: (num_races_train * max_riders, num_features)
    X_test_flat = X_test.reshape(-1, X_test.shape[2])       # Shape: (num_races_test * max_riders, num_features)

    # Flatten the targets
    y_train_flat = y_train.flatten()  # Shape: (num_races_train * max_riders,)
    y_test_flat = y_test.flatten()    # Shape: (num_races_test * max_riders,)

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

    # Transition the new model version to "Production"
    client.transition_model_version_stage(
        name=model_name,
        version=new_model_version.version,
        stage="Production"
    )
    print(f"New model version {new_model_version.version} deployed to production.")

    # Archive old production model versions
    for mv in client.search_model_versions(f"name='{model_name}'"):
        if mv.current_stage == "Production" and mv.version != str(new_model_version.version):
            client.transition_model_version_stage(
                name=model_name,
                version=mv.version,
                stage="Archived"
            )
            print(f"Archived previous model version {mv.version}.")

def redeploy_model(index):
    preprocess_data(index)
    run_id = retrain()
    deploy_and_overwrite_model(run_id)
    return run_id
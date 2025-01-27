import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from sklearn.metrics import mean_absolute_error
import numpy as np
import pickle
import optuna
import data_process

# Ensure model directory exists
os.makedirs("model", exist_ok=True)

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

class RaceRegressionDataset(torch.utils.data.Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        X = self.X[idx]
        y = self.y[idx]
        return X, y

# Training function
def train_model(model, train_loader, optimizer, criterion, device):
    model.train()
    for X_batch, y_batch in train_loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)

        optimizer.zero_grad()
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)
        loss.backward()
        optimizer.step()

# Evaluation function
def evaluate_model(model, test_loader, device):
    model.eval()
    y_true, y_pred = [], []
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model(X_batch)
            y_true.extend(y_batch.cpu().numpy())
            y_pred.extend(outputs.cpu().numpy())
    mae = mean_absolute_error(y_true, y_pred)
    return mae

# Objective function for Optuna
def objective(trial):
    # Suggest hyperparameters
    hidden_size = trial.suggest_categorical("hidden_size", [64, 128, 256])
    learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-2)
    weight_decay = trial.suggest_float("weight_decay", 1e-6, 1e-3)
    num_epochs = trial.suggest_int("num_epochs", 10, 30)
    batch_size = trial.suggest_categorical("batch_size", [64, 128, 256])

    # Data loaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    input_size = X_train_flat.shape[1]

    # Model, criterion, optimizer
    model = RaceRegressionModel(input_size, hidden_size).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    # Training loop
    for _ in range(num_epochs):
        train_model(model, train_loader, optimizer, criterion, device)

    # Evaluation
    mae = evaluate_model(model, test_loader, device)

    # Save the model for each trial
    model_path = f"/tmp/model_trial_{trial.number}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    # Save the trial's best model path
    trial.set_user_attr("model_path", model_path)

    return mae

# Preprocess data for a specific index
data_process.preprocess_data(23)

X_train = np.load('/Users/feliks/Documents/Faks/Diplomska/App/devops/X_train.npy', allow_pickle=True)
y_train = np.load('/Users/feliks/Documents/Faks/Diplomska/App/devops/y_train.npy', allow_pickle=True)
X_test = np.load('/Users/feliks/Documents/Faks/Diplomska/App/devops/X_test.npy', allow_pickle=True)
y_test = np.load('/Users/feliks/Documents/Faks/Diplomska/App/devops/y_test.npy', allow_pickle=True)

# Flatten the data for PyTorch
X_train_flat = X_train.reshape(-1, X_train.shape[2])
X_test_flat = X_test.reshape(-1, X_test.shape[2])

# Flatten the targets
y_train_flat = y_train.flatten()
y_test_flat = y_test.flatten()

# Prepare datasets
train_dataset = RaceRegressionDataset(X_train_flat, y_train_flat)
test_dataset = RaceRegressionDataset(X_test_flat, y_test_flat)

# Optimize hyperparameters
study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=20)

# Get the best model
best_trial = study.best_trial
best_model_path = best_trial.user_attrs["model_path"]

# Load the best model and save it as model.pkl
with open(best_model_path, "rb") as f:
    best_model = pickle.load(f)

final_model_path = "model/model.pkl"
with open(final_model_path, "wb") as f:
    pickle.dump(best_model, f)

# Delete all temporary models except the best one
for trial in study.trials:
    tmp_path = trial.user_attrs.get("model_path")
    if tmp_path and tmp_path != best_model_path:
        try:
            os.remove(tmp_path)
            print(f"Deleted temporary file: {tmp_path}")
        except Exception as e:
            print(f"Failed to delete {tmp_path}: {e}")

# Print the results
print("Best hyperparameters:", best_trial.params)
print("Best MAE:", best_trial.value)
print(f"Best model saved to {final_model_path}")
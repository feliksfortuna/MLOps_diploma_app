import torch
import torch.nn as nn

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
    
    def predict(self, X):
        self.eval()
        with torch.no_grad():
            X = torch.tensor(X, dtype=torch.float32)
            return self.forward(X).numpy()
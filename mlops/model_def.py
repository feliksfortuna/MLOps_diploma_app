import torch.nn as nn

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
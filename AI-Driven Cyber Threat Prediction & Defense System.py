import pandas as pd
import torch
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
from torch.nn import functional as F
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns

# Load and preprocess dataset
df = pd.read_csv("Friday-WorkingHours-Afternoon-DDos.pcap_ISCX (3).csv")
df.columns = df.columns.str.strip()
df.dropna(inplace=True)
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.fillna(0, inplace=True)

# Encode target labels
le = LabelEncoder()
df['Label'] = le.fit_transform(df['Label'])

# Prepare features and labels
y = torch.tensor(df['Label'].values, dtype=torch.long)
X = df.drop(columns=['Label', 'Flow ID', 'Source IP', 'Destination IP', 'Timestamp'], errors='ignore')
X = X.apply(pd.to_numeric, errors='coerce').fillna(0)
X = StandardScaler().fit_transform(X)
x = torch.tensor(X, dtype=torch.float)

# Create edge index for GCN (sequential)
edge_index = torch.tensor([[i, i + 1] for i in range(len(df) - 1)], dtype=torch.long).t().contiguous()
data = Data(x=x, edge_index=edge_index, y=y)

# Define GCN model
class GCN(torch.nn.Module):
    def __init__(self, num_features, hidden_channels):
        super(GCN, self).__init__()
        self.conv1 = GCNConv(num_features, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, 2)

    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        return x

# Initialize model
model = GCN(num_features=data.num_features, hidden_channels=64)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
criterion = torch.nn.CrossEntropyLoss()

# Train model
losses = []
model.train()
for epoch in range(20):
    optimizer.zero_grad()
    out = model(data)
    loss = criterion(out, data.y)
    loss.backward()
    optimizer.step()
    losses.append(loss.item())
    print(f"Epoch {epoch+1}, Loss: {loss.item():.4f}")

# Save model
torch.save(model.state_dict(), "gnn_zero_day_model.pt")
print("\n✅ Model saved as gnn_zero_day_model.pt")

# Evaluate model
model.eval()
with torch.no_grad():
    pred = model(data)
    pred_classes = pred.argmax(dim=1)

# Classification report
print("\n📊 Classification Report:")
print(classification_report(data.y.numpy(), pred_classes.numpy(), target_names=le.classes_))

# Confusion matrix
cm = confusion_matrix(data.y.numpy(), pred_classes.numpy())
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=le.classes_, yticklabels=le.classes_)
plt.title("Confusion Matrix")
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.tight_layout()
plt.show()

# Loss graph
plt.figure(figsize=(6, 4))
plt.plot(range(1, len(losses)+1), losses, marker='o')
plt.title("Training Loss Over Epochs")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.grid(True)
plt.tight_layout()
plt.show()

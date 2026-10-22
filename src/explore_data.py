from pathlib import Path

import pandas as pd

data_path = Path("data/raw_data/creditcard.csv")
if not data_path.exists():
    data_path = Path("data/raw_data/train.csv")
df = pd.read_csv(data_path)

print("Shape:", df.shape)
print("\nColumns:")
print(df.columns)

print("\nMissing Values:")
print(df.isnull().sum())

print("\nClass Distribution:")
print(df["Class"].value_counts())

print("\nSummary Statistics:")
print(df.describe())

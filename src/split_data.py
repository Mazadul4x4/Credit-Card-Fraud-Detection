import os
import pandas as pd
from sklearn.model_selection import train_test_split

RAW_DATA = "/opt/airflow/data/raw_data/creditcard.csv"
GOOD_DATA = "/opt/airflow/data/good_data"

os.makedirs(GOOD_DATA, exist_ok=True)

df = pd.read_csv(RAW_DATA)

train_df, test_df = train_test_split(
    df,
    test_size=0.2,
    random_state=42,
    stratify=df["Class"],
)

train_df.to_csv(f"{GOOD_DATA}/train.csv", index=False)
test_df.to_csv(f"{GOOD_DATA}/test.csv", index=False)

print("Train shape:", train_df.shape)
print("Test shape:", test_df.shape)
print("Files saved successfully.")
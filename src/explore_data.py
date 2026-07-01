import pandas as pd

df = pd.read_csv("e:/dsp-project/Credit-Card-Fraud-Detection/data/raw_data/creditcard.csv")

print("Shape:", df.shape)
print("\nColumns:")
print(df.columns)

print("\nMissing Values:")
print(df.isnull().sum())

print("\nClass Distribution:")
print(df["Class"].value_counts())

print("\nSummary Statistics:")
print(df.describe())
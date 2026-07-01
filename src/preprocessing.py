import pandas as pd
from sklearn.preprocessing import StandardScaler


def load_data(path):
    """
    Load the dataset from CSV.
    """
    return pd.read_csv(path)


def check_missing_values(df):
    """
    Check for missing values.
    """
    print("Missing Values:")
    print(df.isnull().sum())
    return df


def remove_duplicates(df):
    """
    Remove duplicate rows.
    """
    duplicates = df.duplicated().sum()
    print(f"Duplicate rows: {duplicates}")

    df = df.drop_duplicates()

    return df


def scale_amount(df):
    """
    Scale only the Amount column.
    """

    scaler = StandardScaler()

    df["Amount"] = scaler.fit_transform(df[["Amount"]])

    return df, scaler


def split_features_target(df):
    """
    Split dataset into features (X) and target (y).
    """

    X = df.drop("Class", axis=1)

    y = df["Class"]

    return X, y
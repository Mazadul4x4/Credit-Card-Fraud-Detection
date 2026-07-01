import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler


def load_data(path):
    """Load dataset from CSV."""
    return pd.read_csv(path)


def drop_columns(df):
    columns = [
        "Unnamed: 0",
        "trans_num",
        "first",
        "last",
        "street"
    ]

    existing = [col for col in columns if col in df.columns]
    return df.drop(columns=existing)


def fill_missing(df):
    numeric_cols = df.select_dtypes(include="number").columns
    categorical_cols = df.select_dtypes(include="object").columns

    for col in numeric_cols:
        df[col] = df[col].fillna(df[col].median())

    for col in categorical_cols:
        df[col] = df[col].fillna(df[col].mode()[0])

    return df


def encode(df):
    encoder = LabelEncoder()

    categorical_cols = df.select_dtypes(include="object").columns

    for col in categorical_cols:
        df[col] = encoder.fit_transform(df[col])

    return df


def scale(df, target):
    X = df.drop(target, axis=1)
    y = df[target]

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    return X, y, scaler
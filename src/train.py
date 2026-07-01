import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

from imblearn.over_sampling import SMOTE

from preprocessing import (
    load_data,
    check_missing_values,
    remove_duplicates,
    scale_amount,
    split_features_target,
)

# ----------------------------
# Load Dataset
# ----------------------------

df = load_data("e:\dsp-project\Credit-Card-Fraud-Detection/data/raw_data/creditcard.csv")

# ----------------------------
# Preprocessing
# ----------------------------

df = check_missing_values(df)

df = remove_duplicates(df)

df, scaler = scale_amount(df)

X, y = split_features_target(df)

# ----------------------------
# Train/Test Split
# ----------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y,
)

# ----------------------------
# Handle Class Imbalance
# ----------------------------

smote = SMOTE(random_state=42)

X_train, y_train = smote.fit_resample(
    X_train,
    y_train,
)

# ----------------------------
# Train Model
# ----------------------------

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
)

model.fit(X_train, y_train)

# ----------------------------
# Prediction
# ----------------------------

predictions = model.predict(X_test)

# ----------------------------
# Evaluation
# ----------------------------

print("\nClassification Report\n")

print(classification_report(y_test, predictions))

print("\nConfusion Matrix\n")

print(confusion_matrix(y_test, predictions))

print("\nROC-AUC Score")

print(roc_auc_score(y_test, predictions))

# ----------------------------
# Save Model
# ----------------------------

os.makedirs("models", exist_ok=True)

joblib.dump(model, "models/model.pkl")

joblib.dump(scaler, "models/scaler.pkl")

print("\nModel saved successfully!")
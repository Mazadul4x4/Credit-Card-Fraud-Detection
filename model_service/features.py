"""Feature schema of the model (must match src/fraud_pipeline/schema.py)."""

NUMERIC_FEATURES = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]
CATEGORICAL_FEATURE = "time_period"
TIME_PERIODS = ["night", "morning", "afternoon", "evening"]
FEATURE_COLUMNS = NUMERIC_FEATURES + [CATEGORICAL_FEATURE]

# API/JSON feature name -> database column name.
# "Time" is stored as txn_time because Grafana treats a column named "time" as the time axis.
DB_COLUMN = {"Time": "txn_time", "Amount": "amount", "time_period": "time_period"}
DB_COLUMN.update({f"V{i}": f"v{i}" for i in range(1, 29)})

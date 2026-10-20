"""Single source of truth for the dataset schema used by every script and DAG."""

ID_COLUMN = "transaction_id"
TARGET_COLUMN = "Class"

NUMERIC_FEATURES = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]

# Categorical feature derived from `Time` (hour of the day of the transaction).
# The original Kaggle dataset has no categorical column, but the project needs one
# for the "consistency" validation category and for the drift dashboard (Defense 2).
CATEGORICAL_FEATURE = "time_period"
TIME_PERIODS = ["night", "morning", "afternoon", "evening"]

FEATURE_COLUMNS = NUMERIC_FEATURES + [CATEGORICAL_FEATURE]
REQUIRED_COLUMNS = [ID_COLUMN] + FEATURE_COLUMNS + [TARGET_COLUMN]

# Validation thresholds
MAX_TIME_SECONDS = 172_800  # the dataset covers 2 days of transactions
AMOUNT_OUTLIER_THRESHOLD = 30_000  # max amount in the original dataset is ~25,700
TRANSACTION_ID_REGEX = r"^TX\d{8}$"
NUMERIC_REGEX = r"^[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$"

# Error categories stored in the database (one counter column per category)
ERROR_CATEGORIES = [
    "completeness",
    "validity",
    "consistency",
    "schema",
    "type",
    "duplicate",
    "outlier",
    "format",
]


def time_period_from_seconds(seconds: float) -> str:
    """Map the `Time` column (seconds since the first transaction) to a period of the day."""
    hour = int((float(seconds) % 86_400) // 3_600)
    if hour < 6:
        return "night"
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"

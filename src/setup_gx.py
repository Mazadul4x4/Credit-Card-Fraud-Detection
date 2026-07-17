import great_expectations as gx

from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.core.validation_definition import ValidationDefinition
from great_expectations.checkpoint import Checkpoint

# -------------------------------------------------
# Connect to GX project
# -------------------------------------------------

context = gx.get_context(
    mode="file",
    project_root_dir="/opt/airflow/src/gx/gx",
)

print("Connected to Great Expectations")

# -------------------------------------------------
# Create or load datasource
# -------------------------------------------------

datasource = context.data_sources.add_or_update_pandas(
    name="pandas"
)

print("Datasource ready.")

# -------------------------------------------------
# Get or create asset
# -------------------------------------------------

try:
    asset = datasource.get_asset("creditcard_csv")
    print("Asset already exists.")

except Exception:

    asset = datasource.add_csv_asset(
        name="creditcard_csv",
        filepath_or_buffer="/opt/airflow/data/good_data/train.csv",
    )

    print("Asset created.")

# -------------------------------------------------
# Batch Definition
# -------------------------------------------------

try:
    batch_definition = asset.get_batch_definition("whole_file")
    print("Batch Definition already exists.")
except Exception:
    batch_definition = asset.add_batch_definition(
        name="whole_file"
    )
    print("Batch Definition created.")

# -------------------------------------------------
# Expectation Suite
# -------------------------------------------------

try:
    suite = context.suites.get("creditcard_suite")
    print("Expectation Suite already exists.")
except Exception:
    suite = ExpectationSuite(
        name="creditcard_suite"
    )

    context.suites.add(suite)

    print("Expectation Suite created.")

# -------------------------------------------------
# Validation Definition
# -------------------------------------------------

try:
    validation_definition = context.validation_definitions.get(
        "creditcard_validation"
    )

    print("Validation Definition already exists.")

except Exception:

    validation_definition = ValidationDefinition(
        name="creditcard_validation",
        data=batch_definition,
        suite=suite,
    )

    context.validation_definitions.add(
        validation_definition
    )

    print("Validation Definition created.")

# -------------------------------------------------
# Checkpoint
# -------------------------------------------------

try:
    checkpoint = context.checkpoints.get(
        "creditcard_checkpoint"
    )

    print("Checkpoint already exists.")

except Exception:

    checkpoint = Checkpoint(
        name="creditcard_checkpoint",
        validation_definitions=[
            validation_definition
        ],
    )

    context.checkpoints.add(checkpoint)

    print("Checkpoint created.")

print()
print("GX setup completed successfully.")
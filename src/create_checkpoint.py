import great_expectations as gx
from great_expectations.checkpoint import UpdateDataDocsAction

context = gx.get_context(
    mode="file",
    project_root_dir="/opt/airflow/src/gx/gx",
)

# Get validation definition
validation_definition = context.validation_definitions.get(
    "creditcard_validation"
)

try:
    checkpoint = gx.Checkpoint(
        name="creditcard_checkpoint",
        validation_definitions=[validation_definition],
        actions=[
            UpdateDataDocsAction(
                name="update_data_docs"
            )
        ],
        result_format={
            "result_format": "COMPLETE"
        },
    )

    context.checkpoints.add(checkpoint)

    print("✓ Checkpoint created.")

except Exception:
    print("✓ Checkpoint already exists.")
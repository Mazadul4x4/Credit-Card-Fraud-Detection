import great_expectations as gx

context = gx.get_context(
    mode="file",
    project_root_dir="/opt/airflow/src/gx/gx",
)

# Get datasource
datasource = context.data_sources.get("pandas")

# Get asset
asset = datasource.get_asset("creditcard_dataframe")

# Get batch definition
batch_definition = asset.get_batch_definition(
    "creditcard_batch"
)

# Get expectation suite
suite = context.suites.get("creditcard_suite")

# Create validation definition
try:
    validation_definition = gx.ValidationDefinition(
        name="creditcard_validation",
        data=batch_definition,
        suite=suite,
    )

    context.validation_definitions.add(validation_definition)

    print("✓ Validation Definition created.")

except Exception:
    validation_definition = context.validation_definitions.get(
        "creditcard_validation"
    )

    print("✓ Validation Definition already exists.")
import great_expectations as gx

# Connect to the GX project
context = gx.get_context(
    mode="file",
    project_root_dir="/opt/airflow/src/gx/gx",
)

print("Connected to Great Expectations!")

# -----------------------------
# Create Pandas datasource
# -----------------------------
try:
    datasource = context.data_sources.add_pandas("pandas")
    print("✓ Pandas datasource created.")
except Exception:
    datasource = context.data_sources.get("pandas")
    print("✓ Pandas datasource already exists.")

# -----------------------------
# Create dataframe asset
# -----------------------------
try:
    asset = datasource.add_dataframe_asset(
        name="creditcard_dataframe"
    )
    print("✓ Dataframe asset created.")
except Exception:
    asset = datasource.get_asset("creditcard_dataframe")
    print("✓ Dataframe asset already exists.")

# -----------------------------
# Create batch definition
# -----------------------------
try:
    batch_definition = asset.add_batch_definition_whole_dataframe(
        "creditcard_batch"
    )
    print("✓ Batch definition created.")
except Exception:
    batch_definition = asset.get_batch_definition(
        "creditcard_batch"
    )
    print("✓ Batch definition already exists.")

print("\nGX setup finished successfully!")
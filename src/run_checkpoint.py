import pandas as pd
import great_expectations as gx

context = gx.get_context(
    mode="file",
    project_root_dir="/opt/airflow/src/gx/gx",
)

# Load checkpoint
checkpoint = context.checkpoints.get("creditcard_checkpoint")

# Read a sample of your dataset
df = pd.read_csv("/opt/airflow/data/good_data/train.csv").head(100)

# Run validation
result = checkpoint.run()

print("Validation Success:", result.success)

# Build Data Docs
context.build_data_docs()

print("Data Docs generated successfully!")
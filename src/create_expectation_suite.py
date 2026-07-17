import great_expectations as gx

context = gx.get_context(
    mode="file",
    project_root_dir="/opt/airflow/src/gx/gx",
)

# Create or load the suite
try:
    suite = gx.ExpectationSuite(name="creditcard_suite")
    suite = context.suites.add(suite)
    print("✓ Expectation Suite created.")
except Exception:
    suite = context.suites.get("creditcard_suite")
    print("✓ Expectation Suite already exists.")

print(suite)

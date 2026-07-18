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

# Add expectations
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToNotBeNull(
        column="Class"
    )
)

suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeInSet(
        column="Class",
        value_set=[0, 1],
    )
)

suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="Amount",
        min_value=0,
    )
)

suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="Time",
        min_value=0,
    )
)

context.suites.add_or_update(suite)

print("✓ Expectations saved successfully.")
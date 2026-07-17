import great_expectations as gx

context = gx.get_context(
    mode="file",
    project_root_dir="/opt/airflow/src/gx/gx",
)

# Load the existing suite
suite = context.suites.get("creditcard_suite")

# Clear existing expectations if you rerun the script
suite.expectations = []

# -------------------------------------------------
# Required columns
# -------------------------------------------------
suite.add_expectation(
    gx.expectations.ExpectColumnToExist(column="Amount")
)

suite.add_expectation(
    gx.expectations.ExpectColumnToExist(column="Class")
)

# -------------------------------------------------
# Amount validation
# -------------------------------------------------
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToNotBeNull(
        column="Amount"
    )
)

suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="Amount",
        min_value=0,
    )
)

# -------------------------------------------------
# Class validation
# -------------------------------------------------
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeInSet(
        column="Class",
        value_set=[0, 1],
    )
)

# Save the suite
context.suites.add_or_update(suite)

print("Expectation Suite updated successfully!")
print(f"Number of expectations: {len(suite.expectations)}")
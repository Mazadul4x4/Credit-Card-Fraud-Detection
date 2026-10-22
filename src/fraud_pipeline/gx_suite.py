"""Builds the Great Expectations expectation suite.

Every expectation carries `meta.category`, which is how validation results are mapped
to the error categories saved in the database.

Error types covered (8):
    completeness  - null value in a required column            (row)
    validity      - Time / Amount outside the valid range        (row)
    consistency   - time_period / Class not in the allowed set   (row)
    schema        - required column missing                      (file)
    type          - text such as "abc" in a numeric column       (row)
    duplicate     - duplicated transaction_id                    (row)
    outlier       - Amount above a realistic maximum             (row)
    format        - transaction_id not matching TX + 8 digits    (row)
"""

import great_expectations as gx

from fraud_pipeline.gx_custom import ExpectColumnValuesToBeNumericBetween
from fraud_pipeline.schema import (
    AMOUNT_OUTLIER_THRESHOLD,
    CATEGORICAL_FEATURE,
    ID_COLUMN,
    MAX_TIME_SECONDS,
    NUMERIC_FEATURES,
    NUMERIC_REGEX,
    REQUIRED_COLUMNS,
    TARGET_COLUMN,
    TIME_PERIODS,
    TRANSACTION_ID_REGEX,
)

SUITE_NAME = "creditcard_suite"


def _meta(category: str) -> dict:
    return {"category": category}


def build_expectations() -> list:
    expectations = [
        # schema (file level)
        gx.expectations.ExpectTableColumnsToMatchSet(
            column_set=REQUIRED_COLUMNS, exact_match=False, meta=_meta("schema")
        ),
    ]

    # completeness: no nulls in any required column
    for column in REQUIRED_COLUMNS:
        expectations.append(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=column, meta=_meta("completeness"))
        )

    # type: numeric columns must contain numbers
    for column in NUMERIC_FEATURES:
        expectations.append(
            gx.expectations.ExpectColumnValuesToMatchRegex(
                column=column, regex=NUMERIC_REGEX, meta=_meta("type")
            )
        )

    expectations += [
        # validity: values inside the valid range
        ExpectColumnValuesToBeNumericBetween(
            column="Time", min_value=0, max_value=MAX_TIME_SECONDS, meta=_meta("validity")
        ),
        ExpectColumnValuesToBeNumericBetween(column="Amount", min_value=0, meta=_meta("validity")),
        # consistency: categorical values in the allowed list
        gx.expectations.ExpectColumnValuesToBeInSet(
            column=CATEGORICAL_FEATURE, value_set=TIME_PERIODS, meta=_meta("consistency")
        ),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column=TARGET_COLUMN, value_set=["0", "1"], meta=_meta("consistency")
        ),
        # duplicate primary keys
        gx.expectations.ExpectColumnValuesToBeUnique(column=ID_COLUMN, meta=_meta("duplicate")),
        # statistical outliers
        ExpectColumnValuesToBeNumericBetween(
            column="Amount", max_value=AMOUNT_OUTLIER_THRESHOLD, meta=_meta("outlier")
        ),
        # format mismatch (regex)
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column=ID_COLUMN, regex=TRANSACTION_ID_REGEX, meta=_meta("format")
        ),
    ]
    return expectations


def build_suite() -> gx.ExpectationSuite:
    suite = gx.ExpectationSuite(name=SUITE_NAME)
    for expectation in build_expectations():
        suite.add_expectation(expectation)
    return suite

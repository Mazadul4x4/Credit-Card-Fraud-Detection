"""Custom Great Expectations expectation.

Ingested files are read as text so that a value such as "abc" in a numeric column
can be reported row by row (type category). The built-in ExpectColumnValuesToBeBetween
cannot compare text with numbers, so this expectation converts each value to a number
first and only checks the range of values that ARE numbers. Values that are not numbers
are reported by the type expectation instead, so a row is never counted twice for the
same problem.

This module must be imported before the expectation suite is loaded.
"""

from typing import Optional

import pandas as pd
from great_expectations.execution_engine import PandasExecutionEngine
from great_expectations.expectations.expectation import ColumnMapExpectation
from great_expectations.expectations.metrics import (
    ColumnMapMetricProvider,
    column_condition_partial,
)


class ColumnValuesNumericBetween(ColumnMapMetricProvider):
    condition_metric_name = "column_values.numeric_between"
    condition_value_keys = ("min_value", "max_value")

    @column_condition_partial(engine=PandasExecutionEngine)
    def _pandas(cls, column, min_value=None, max_value=None, **kwargs):
        numbers = pd.to_numeric(column, errors="coerce")
        in_range = pd.Series(True, index=column.index)
        if min_value is not None:
            in_range &= numbers >= min_value
        if max_value is not None:
            in_range &= numbers <= max_value
        # Non-numeric values are the type expectation's job, not this one.
        return numbers.isna() | in_range


class ExpectColumnValuesToBeNumericBetween(ColumnMapExpectation):
    """Expect numeric values of a (possibly text) column to be between min_value and max_value."""

    min_value: Optional[float] = None
    max_value: Optional[float] = None

    map_metric = "column_values.numeric_between"
    success_keys = ("min_value", "max_value", "mostly")

"""Create or update the Great Expectations project used by the ingestion DAG.

Creates: pandas datasource -> dataframe asset -> batch definition,
the expectation suite (built from fraud_pipeline/gx_suite.py), the validation
definition and the checkpoint (with the UpdateDataDocsAction).

Run automatically by the `airflow-init` container. Manual run:
    docker compose run --rm tools python src/setup_gx.py
"""

import argparse

from fraud_pipeline.validation import GX_PROJECT_ROOT, get_context, setup_context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=GX_PROJECT_ROOT)
    args = parser.parse_args()

    context = get_context(args.project_root)
    setup_context(context)
    suite = context.suites.get("creditcard_suite")
    print(f"GX project ready at {args.project_root} ({len(suite.expectations)} expectations)")


if __name__ == "__main__":
    main()

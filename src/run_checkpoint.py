"""Run checkpoint and generate Data Docs."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.gx_validator import validate_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GX checkpoint on a file")
    parser.add_argument("--file", default="data/good_data/test.csv", help="File to validate")
    args = parser.parse_args()

    file_to_validate = Path(args.file)
    if not file_to_validate.exists():
        alt = Path("data/raw_data/creditcard.csv")
        if alt.exists():
            file_to_validate = alt

    logger.info(f"Validating file: {file_to_validate}")
    results = validate_file(file_to_validate)
    logger.info(f"Validation success: {results['validation_success']}")
    logger.info(f"Criticality: {results['criticality']}")
    logger.info(f"Data Docs report: {results['report_file']}")


if __name__ == "__main__":
    main()

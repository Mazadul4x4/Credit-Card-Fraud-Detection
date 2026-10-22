"""Update or add expectations to creditcard_suite."""

from __future__ import annotations

import logging

from src.gx_validator import configure_suite, get_gx_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    context = get_gx_context()
    suite = configure_suite(context)
    logger.info(f"Expectation Suite updated successfully! Number of expectations: {len(suite.expectations)}")


if __name__ == "__main__":
    main()

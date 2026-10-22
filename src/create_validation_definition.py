"""Create validation definition for creditcard data."""

from __future__ import annotations

import logging

from src.gx_validator import configure_suite, get_gx_context, setup_checkpoint_for_dataframe

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    context = get_gx_context()
    suite = configure_suite(context)
    checkpoint = setup_checkpoint_for_dataframe(context, suite)
    logger.info(f"Validation definition and checkpoint ready: {checkpoint.name}")


if __name__ == "__main__":
    main()

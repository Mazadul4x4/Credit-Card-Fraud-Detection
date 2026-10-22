"""Model loading. Defense 1: from a file. (Defense 2 adds loading from the MLflow registry.)"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib

logger = logging.getLogger("uvicorn.error")


def load_model_from_file(model_path: str, metadata_path: str):
    """Return (model, version) or (None, None) if the file does not exist."""
    path = Path(model_path)
    if not path.exists():
        logger.warning("Model file not found: %s (train it with src/train.py)", path)
        return None, None

    model = joblib.load(path)
    version = None
    meta = Path(metadata_path)
    if meta.exists():
        version = json.loads(meta.read_text()).get("model_version")
    if not version:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        version = "file-" + mtime.strftime("%Y%m%d%H%M%S")
    logger.info("Model %s loaded from %s", version, path)
    return model, version

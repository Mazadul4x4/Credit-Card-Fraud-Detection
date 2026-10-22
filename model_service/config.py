import os
import socket
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

raw_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql://dsp:yourRealPassword123@localhost:5432/dsp_app",
)

# Automatically resolve between Docker network 'db' and local host 'localhost'
if "@db:" in raw_db_url or "@db/" in raw_db_url:
    try:
        socket.gethostbyname("db")
        DATABASE_URL = raw_db_url
    except Exception:
        # Running locally outside docker network
        DATABASE_URL = raw_db_url.replace("@db:", "@localhost:").replace("@db/", "@localhost/")
else:
    DATABASE_URL = raw_db_url

MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")

# Candidate model paths for local and Docker environments
DEFAULT_MODEL_PATH = os.getenv(
    "MODEL_PATH",
    str(Path(__file__).resolve().parent.parent / "models" / "fraud_model.joblib"),
)

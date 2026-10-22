import os

from dotenv import load_dotenv

load_dotenv()

# Never hardcode credentials: the connection string comes from the environment (.env)
DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/fraud_model.joblib")
MODEL_METADATA_PATH = os.getenv("MODEL_METADATA_PATH", "/app/models/model_metadata.json")

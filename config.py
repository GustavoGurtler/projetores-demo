import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("APP_SECRET_KEY", "reservas-projetor-dev-secret")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "reservas.db")
    DEMO_DATA_ENABLED = os.environ.get("DEMO_DATA_ENABLED", "1").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    DEMO_MAX_RECORDS = int(os.environ.get("DEMO_MAX_RECORDS", "80"))
    DEMO_RATE_LIMIT_REQUESTS = int(os.environ.get("DEMO_RATE_LIMIT_REQUESTS", "40"))
    DEMO_RATE_LIMIT_WINDOW_SECONDS = int(
        os.environ.get("DEMO_RATE_LIMIT_WINDOW_SECONDS", "600")
    )
    DEMO_RESET_INTERVAL_HOURS = int(os.environ.get("DEMO_RESET_INTERVAL_HOURS", "6"))
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "1").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5001"))

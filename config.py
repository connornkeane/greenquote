import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-nano")
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", os.path.join(BASE_DIR, "data", "greenquote.db")
    )
    GEOCODE_URL = os.environ.get(
        "GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search"
    )
    FORECAST_URL = os.environ.get(
        "FORECAST_URL", "https://api.open-meteo.com/v1/forecast"
    )
    BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "Plainsview Lawn & Landscape")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 64 * 1024


def check_config(config):
    if not config.get("SECRET_KEY") or len(config["SECRET_KEY"]) < 16:
        raise RuntimeError(
            "SECRET_KEY is missing or too short. Copy .env.example to .env and set it."
        )

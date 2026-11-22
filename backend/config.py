import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent
_root_dir = _backend_dir.parent

# Load .env from backend folder, project root, and cwd
load_dotenv(_backend_dir / ".env")
load_dotenv(_root_dir / ".env")
load_dotenv()


import re


def _clean_mongo_uri(uri: str | None) -> str:
    if not uri:
        return "mongodb://localhost:27017/"
    cleaned = uri.strip().strip("'\"")
    # Auto-clean accidental angle brackets around username or password, e.g. <sarthakkambli56_db_user>
    cleaned = re.sub(r"://<([^>]+)>:", r"://\1:", cleaned)
    cleaned = re.sub(r":<([^>]+)>@", r":\1@", cleaned)
    return cleaned


def as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    APP_NAME = os.getenv("APP_NAME", "CineSuggest AI")
    APP_URL = os.getenv("APP_URL", "http://127.0.0.1:5000")
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    DEBUG = as_bool(os.getenv("FLASK_DEBUG"), False)

    MONGODB_URI = _clean_mongo_uri(os.getenv("MONGODB_URI"))
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "cinesuggest_ai").strip().strip("'\"")
    MONGODB_TIMEOUT_MS = 15000

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto").strip()
    SUMMARY_OPENROUTER_MODEL = os.getenv("SUMMARY_OPENROUTER_MODEL", "google/gemini-2.5-flash-lite").strip()

    SUMMARY_PROVIDER = os.getenv("SUMMARY_PROVIDER", "gemini").strip().lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()

    REQUEST_TIMEOUT_SECONDS = 12
    AI_TIMEOUT_SECONDS = 45
    HOMEPAGE_MOVIE_LIMIT = 30

    @classmethod
    def validate(cls) -> None:
        if cls.SUMMARY_PROVIDER not in {"gemini", "openai", "openrouter"}:
            cls.SUMMARY_PROVIDER = "gemini"

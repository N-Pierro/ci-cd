"""Application configuration. Everything comes from environment variables (12-factor)."""
import os


class Config:
    APP_ENV = os.getenv("APP_ENV", "dev")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:////tmp/tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 16 * 1024  # reject request bodies over 16 KB
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

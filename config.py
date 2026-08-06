import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "development-secret-key"
)

SQLALCHEMY_DATABASE_URI = "sqlite:///voting.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    PORT = int(os.getenv("PORT", 5000))

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "gis_db")

    JWT_SECRET = os.getenv("JWT_SECRET", "my_super_secret_key")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    CLIENT_URL = os.getenv("CLIENT_URL", "http://localhost:5173")
    MAPQUEST_KEY = os.getenv("MAPQUEST_KEY", "")

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    PROFILE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "profile")
    LOCATION_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "locations")

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
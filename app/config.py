import os

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "super_secret_diploma_key_2026")

    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = ""
    DB_NAME = "medical_ai"
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FraudGuardAI"

    #database setting
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_NAME: str = os.getenv("DB_NAME", "fraud_db")
    DB_USER: str = os.getenv("DB_NAME", "postgres")
    DB_PASS: str = os.getenv("DB_PASSWORD", "postgres")

    #security setting
    SECRET_KET: str = os.getenv("SECRET_KEY", "SUPER_SECRET_DEVELOPMENT_KEY_CHANGEME")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

settings = Settings()
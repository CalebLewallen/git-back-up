from pydantic_settings import BaseSettings, SettingsConfigDict
from cryptography.fernet import Fernet

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gitbackup"
    ENCRYPTION_KEY: str = Fernet.generate_key().decode()
    
    # Git settings
    TEMP_DIR: str = "/tmp/git-back-up"
    
    # Security
    WEBHOOK_SECRET: str = "change-me-in-production"
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

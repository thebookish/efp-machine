from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    ENV: str = Field(default='production')
    LOG_LEVEL: str = Field(default='INFO')
    OPENAI_API_KEY: str = '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'
    DATABASE_URL: str = Field(default='sqlite+aiosqlite:///./efp.db')
    ALLOW_ORIGINS: str = Field(default='http://localhost:5173')
    TIMEZONE_UK: str = Field(default='Europe/London')
    class Config:
        env_file = '.env'
settings = Settings()

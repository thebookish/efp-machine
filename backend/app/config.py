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

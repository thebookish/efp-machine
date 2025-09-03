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

from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    ENV: str = Field(default='production')
    LOG_LEVEL: str = Field(default='INFO')
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    DATABASE_URL: str = Field(default='sqlite+aiosqlite:///./efp.db')
    ALLOW_ORIGINS: str = Field(default='http://localhost:5173')
    TIMEZONE_UK: str = Field(default='Europe/London')
    class Config:
        env_file = '.env'
settings = Settings()

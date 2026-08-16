from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "sqlite:///./screening.db"
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    LLM_PROVIDER: Literal["groq", "anthropic", "openai"] = "groq"
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    MAX_QUESTIONS_PER_INTERVIEW: int = 6
    RETRIEVAL_TOP_K: int = 4
    CORS_ORIGINS: str = "http://localhost:3000"


settings = Settings()

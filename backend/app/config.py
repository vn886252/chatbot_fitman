from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    FB_PAGE_ACCESS_TOKEN: str = Field(default="")
    FB_VERIFY_TOKEN: str = Field(default="fitman_webhook_verify_2026")
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    USE_LOCAL_LLM: bool = Field(default=False)
    QWEN_API_BASE: str = Field(default="http://127.0.0.1:5001/v1")
    QWEN_FALLBACK_PORT: int = Field(default=5001)
    SERVER_BASE_URL: str = Field(default="")

settings = Settings()

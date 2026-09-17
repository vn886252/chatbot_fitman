import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

# Đường dẫn đến file .env ở thư mục gốc project
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(ROOT_DIR, ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE if os.path.exists(ENV_FILE) else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    FB_PAGE_ACCESS_TOKEN: str = Field(default="")
    FB_VERIFY_TOKEN: str = Field(default="fitman_webhook_verify_2026")
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    USE_LOCAL_LLM: bool = Field(default=False)
    QWEN_API_BASE: str = Field(default="http://127.0.0.1:5001/v1")
    QWEN_FALLBACK_PORT: int = Field(default=8888)
    SERVER_BASE_URL: str = Field(default="")
    TELEGRAM_BOT_TOKEN: str = Field(default="8767221119:AAGUOtUEVgv6u67ClKFwMYukiJOOloLST0k")
    TELEGRAM_CHAT_ID: str = Field(default="1144165826")

settings = Settings()
